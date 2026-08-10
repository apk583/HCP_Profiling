"""LangGraph workflow orchestrating HCP profile generation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from app.config import Settings
from app.schemas.hcp import (
    HCPProfile,
    PipelineProgress,
    PipelineStage,
    SourceResult,
)
from app.services.ai.judge import SummaryJudge
from app.services.ai.summary import SummaryGenerator
from app.services.collectors.clinical_trials import ClinicalTrialsCollector
from app.services.collectors.npi_registry import NPIRegistryCollector
from app.services.collectors.openfda import OpenFDACollector
from app.services.collectors.pubmed import PubMedCollector
from app.services.collaboration_network import CollaborationNetworkBuilder
from app.services.ml.predictor import InfluencePredictor
from app.services.normalizer import ProfileNormalizer
from app.services.pdf.generator import PDFReportGenerator

logger = logging.getLogger(__name__)


class HCPWorkflowState(TypedDict, total=False):
    npi: str
    stage: str
    progress_pct: int
    message: str
    sources_completed: list[str]
    raw_data: dict[str, Any]
    source_results: list[dict[str, Any]]
    profile: dict[str, Any]
    error: str | None


class HCPProfileWorkflow:
    STAGE_PROGRESS = {
        PipelineStage.INIT: 0,
        PipelineStage.FETCHING_NPI: 10,
        PipelineStage.COLLECTING_DATA: 30,
        PipelineStage.NORMALIZING: 45,
        PipelineStage.FEATURE_ENGINEERING: 50,
        PipelineStage.ML_PREDICTION: 60,
        PipelineStage.GENERATING_SUMMARY: 75,
        PipelineStage.JUDGING_SUMMARY: 85,
        PipelineStage.GENERATING_PDF: 95,
        PipelineStage.COMPLETE: 100,
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.normalizer = ProfileNormalizer()
        self.predictor = InfluencePredictor(settings)
        self.summary_gen = SummaryGenerator(settings)
        self.judge = SummaryJudge(settings)
        self.pdf_gen = PDFReportGenerator(settings)
        self.network_builder = CollaborationNetworkBuilder()
        self._progress_callbacks: list[Any] = []
        self._graph = self._build_graph()

    def on_progress(self, callback) -> None:
        self._progress_callbacks.append(callback)

    def _emit_progress(self, state: HCPWorkflowState) -> None:
        progress = PipelineProgress(
            npi=state.get("npi", ""),
            stage=PipelineStage(state.get("stage", PipelineStage.INIT)),
            progress_pct=state.get("progress_pct", 0),
            message=state.get("message", ""),
            sources_completed=state.get("sources_completed", []),
        )
        for cb in self._progress_callbacks:
            cb(progress)

    def _build_graph(self):
        graph = StateGraph(HCPWorkflowState)

        graph.add_node("fetch_npi", self._fetch_npi)
        graph.add_node("collect_parallel", self._collect_parallel)
        graph.add_node("normalize", self._normalize)
        graph.add_node("ml_predict", self._ml_predict)
        graph.add_node("generate_summary", self._generate_summary)
        graph.add_node("judge_summary", self._judge_summary)
        graph.add_node("generate_pdf", self._generate_pdf)

        graph.set_entry_point("fetch_npi")
        graph.add_edge("fetch_npi", "collect_parallel")
        graph.add_edge("collect_parallel", "normalize")
        graph.add_edge("normalize", "ml_predict")
        graph.add_edge("ml_predict", "generate_summary")
        graph.add_edge("generate_summary", "judge_summary")
        graph.add_edge("judge_summary", "generate_pdf")
        graph.add_edge("generate_pdf", END)

        return graph.compile()

    async def run(self, npi: str) -> HCPProfile:
        initial: HCPWorkflowState = {
            "npi": npi,
            "stage": PipelineStage.INIT.value,
            "progress_pct": 0,
            "message": "Starting pipeline",
            "sources_completed": [],
            "raw_data": {},
            "source_results": [],
            "error": None,
        }
        result = await self._graph.ainvoke(initial)
        if result.get("error"):
            raise RuntimeError(result["error"])
        return HCPProfile.model_validate(result["profile"])

    async def _fetch_npi(self, state: HCPWorkflowState) -> HCPWorkflowState:
        state["stage"] = PipelineStage.FETCHING_NPI.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.FETCHING_NPI]
        state["message"] = "Fetching NPI Registry data"
        self._emit_progress(state)

        npi = state["npi"]
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            collector = NPIRegistryCollector(self.settings, client)
            try:
                data = await collector.collect(npi)
                state["raw_data"]["npi_registry"] = data
                state["source_results"].append(
                    SourceResult(source="npi_registry", success=True, record_count=1).model_dump()
                )
                state["sources_completed"].append("npi_registry")
            except Exception as exc:
                logger.error("NPI fetch failed: %s", exc)
                state["error"] = f"NPI Registry lookup failed: {exc}"
                state["stage"] = PipelineStage.FAILED.value
        return state

    async def _collect_parallel(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.COLLECTING_DATA.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.COLLECTING_DATA]
        state["message"] = "Collecting data from external sources"
        self._emit_progress(state)

        npi_data = state["raw_data"].get("npi_registry", {})
        results = npi_data.get("results", [{}])
        basic = results[0].get("basic", {}) if results else {}
        first_name = basic.get("first_name", "")
        last_name = basic.get("last_name", "")
        org_name = basic.get("organization_name", "")
        provider_name = org_name or f"{first_name} {last_name}".strip()
        author_name = f"{last_name} {first_name[0]}" if last_name and first_name else last_name

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            collectors = {
                "pubmed": PubMedCollector(self.settings, client),
                "clinical_trials": ClinicalTrialsCollector(self.settings, client),
                "openfda": OpenFDACollector(self.settings, client),
            }

            async def _run_source(name: str, collector) -> tuple[str, dict, SourceResult]:
                try:
                    kwargs = {
                        "author_name": author_name,
                        "provider_name": provider_name,
                        "last_name": last_name,
                        "first_name": first_name,
                    }
                    data = await collector.collect(state["npi"], **kwargs)
                    count = len(data.get("publications", data.get("trials", data.get("adverse_events", []))))
                    return name, data, SourceResult(source=name, success=True, record_count=count)
                except Exception as exc:
                    logger.warning("%s collection failed: %s", name, exc)
                    return name, {}, SourceResult(source=name, success=False, error=str(exc))

            tasks = [_run_source(n, c) for n, c in collectors.items()]
            results_list = await asyncio.gather(*tasks)

            for name, data, result in results_list:
                state["raw_data"][name] = data
                state["source_results"].append(result.model_dump())
                if result.success:
                    state["sources_completed"].append(name)

        return state

    async def _normalize(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.NORMALIZING.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.NORMALIZING]
        state["message"] = "Normalizing profile data"
        self._emit_progress(state)

        source_results = [SourceResult(**sr) for sr in state["source_results"]]
        profile = self.normalizer.normalize(state["npi"], state["raw_data"], source_results)
        profile.collaboration_network = self.network_builder.build(profile)
        state["profile"] = profile.model_dump()
        return state

    async def _ml_predict(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.ML_PREDICTION.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.ML_PREDICTION]
        state["message"] = "Running influence prediction models"
        self._emit_progress(state)

        profile = HCPProfile.model_validate(state["profile"])
        predictions = self.predictor.predict(profile)
        profile.ml_predictions = predictions
        state["profile"] = profile.model_dump()
        return state

    async def _generate_summary(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.GENERATING_SUMMARY.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.GENERATING_SUMMARY]
        state["message"] = "Generating AI summary"
        self._emit_progress(state)

        profile = HCPProfile.model_validate(state["profile"])
        summary = self.summary_gen.generate(profile)
        profile.ai_summary = summary
        state["profile"] = profile.model_dump()
        return state

    async def _judge_summary(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.JUDGING_SUMMARY.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.JUDGING_SUMMARY]
        state["message"] = "Evaluating summary quality"
        self._emit_progress(state)

        profile = HCPProfile.model_validate(state["profile"])
        evaluation = self.judge.evaluate(profile, profile.ai_summary)
        profile.judge_evaluation = evaluation
        state["profile"] = profile.model_dump()
        return state

    async def _generate_pdf(self, state: HCPWorkflowState) -> HCPWorkflowState:
        if state.get("error"):
            return state

        state["stage"] = PipelineStage.GENERATING_PDF.value
        state["progress_pct"] = self.STAGE_PROGRESS[PipelineStage.GENERATING_PDF]
        state["message"] = "Generating PDF report"
        self._emit_progress(state)

        profile = HCPProfile.model_validate(state["profile"])
        pdf_path = self.pdf_gen.generate(profile)
        profile.pdf_path = pdf_path
        state["profile"] = profile.model_dump()

        state["stage"] = PipelineStage.COMPLETE.value
        state["progress_pct"] = 100
        state["message"] = "Profile generation complete"
        self._emit_progress(state)
        return state
