"""HCP profile generation endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.hcp import CollaborationNetwork, HCPProfile, HCPProfileRequest, HCPProfileResponse, PipelineProgress, PipelineStage
from app.services.collaboration_network import CollaborationNetworkBuilder
from app.workflows.hcp_graph import HCPProfileWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hcp", tags=["hcp"])

_progress_store: dict[str, PipelineProgress] = {}
_profile_store: dict[str, HCPProfile] = {}
_network_builder = CollaborationNetworkBuilder()


@router.post("/profile", response_model=HCPProfileResponse)
async def generate_profile(request: HCPProfileRequest) -> HCPProfileResponse:
    settings = get_settings()
    workflow = HCPProfileWorkflow(settings)

    def _track_progress(progress: PipelineProgress) -> None:
        _progress_store[request.npi] = progress

    workflow.on_progress(_track_progress)

    try:
        _progress_store[request.npi] = PipelineProgress(
            npi=request.npi,
            stage=PipelineStage.INIT,
            progress_pct=0,
            message="Pipeline started",
        )
        profile = await workflow.run(request.npi)
        _profile_store[request.npi] = profile
        _progress_store[request.npi] = PipelineProgress(
            npi=request.npi,
            stage=PipelineStage.COMPLETE,
            progress_pct=100,
            message="Complete",
            sources_completed=[sr.source for sr in profile.source_results if sr.success],
        )
        return HCPProfileResponse(success=True, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Profile generation failed for NPI %s", request.npi)
        _progress_store[request.npi] = PipelineProgress(
            npi=request.npi,
            stage=PipelineStage.FAILED,
            progress_pct=0,
            message=str(exc),
        )
        return HCPProfileResponse(success=False, error=str(exc))


@router.get("/profile/{npi}/collaboration-network", response_model=CollaborationNetwork)
async def get_collaboration_network(npi: str) -> CollaborationNetwork:
    """Return the cached collaboration network for the most recently generated profile."""
    profile = _profile_store.get(npi)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found. Generate a profile first.")
    if profile.collaboration_network is None:
        profile.collaboration_network = _network_builder.build(profile)
    return profile.collaboration_network


@router.get("/profile/{npi}/progress", response_model=PipelineProgress)
async def get_progress(npi: str) -> PipelineProgress:
    if npi not in _progress_store:
        raise HTTPException(status_code=404, detail="No active or recent pipeline for this NPI")
    return _progress_store[npi]


@router.get("/profile/{npi}/pdf")
async def download_pdf(npi: str):
    settings = get_settings()
    pdf_dir = settings.pdf_output_dir
    matches = sorted(pdf_dir.glob(f"hcp_report_{npi}_*.pdf"), reverse=True)
    if not matches:
        raise HTTPException(status_code=404, detail="PDF report not found. Generate a profile first.")
    return FileResponse(
        path=str(matches[0]),
        media_type="application/pdf",
        filename=matches[0].name,
    )
