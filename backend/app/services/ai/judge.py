"""LLM-as-a-Judge evaluation for generated summaries."""

import json
import logging
import re

from app.config import Settings
from app.schemas.hcp import HCPProfile, JudgeEvaluation
from app.services.ai.gemini import GeminiService

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = """You are a senior healthcare intelligence quality reviewer.
Validate a completed HCP profile and its generated intelligence summary against ONLY the
provided source evidence. Do not reward plausible but unsupported clinical claims. Check
identity, specialty, publications, clinical trials, collaboration metrics, and influence
assessment. Identify the most important issue concisely in feedback.
Score each dimension from 0-10. Respond ONLY with valid JSON in this exact format:
{
  "overall_score": <float>,
  "groundedness": <float>,
  "completeness": <float>,
  "clarity": <float>,
  "feedback": "<string>",
  "passed": <boolean>
}
A summary passes if overall_score >= 7.0 and groundedness >= 7.0."""


class SummaryJudge:
    PASS_THRESHOLD = 7.0

    def __init__(self, settings: Settings):
        self.gemini = GeminiService(settings)
        self.settings = settings

    def evaluate(self, profile: HCPProfile, summary: str) -> JudgeEvaluation:
        if not self.gemini.is_configured:
            return self._heuristic_evaluation(profile, summary)

        evidence = {
            "identity": {
                "npi": profile.npi,
                "name": f"{profile.identity.first_name} {profile.identity.last_name}".strip(),
                "specialty": profile.identity.primary_specialty,
                "location": f"{profile.identity.address.city}, {profile.identity.address.state}",
            },
            "publications": [
                {"pmid": p.pmid, "title": p.title, "journal": p.journal, "date": p.pub_date}
                for p in profile.publications[:25]
            ],
            "clinical_trials": [
                {"id": t.nct_id, "title": t.title, "status": t.status, "role": t.role}
                for t in profile.clinical_trials[:15]
            ],
            "collaboration_metrics": profile.collaboration_network.metrics.model_dump()
            if profile.collaboration_network else {},
            "influence_predictions": [p.model_dump() for p in profile.ml_predictions],
        }
        user_prompt = f"""Evaluate this FINAL HCP PROFILE.

VERIFIED EVIDENCE:
{json.dumps(evidence, ensure_ascii=False)}

GENERATED INTELLIGENCE SUMMARY:
{summary}

Score groundedness (claims supported by evidence), completeness (key evidence represented),
and clarity. Pass only when the summary is both accurate and sufficiently complete."""

        try:
            raw = self.gemini.judge(system=JUDGE_SYSTEM, user=user_prompt)
            evaluation = self._parse_judge_response(raw)
            evaluation.judge_model = self.settings.gemini_judge_model
            return evaluation
        except Exception as exc:
            logger.error("Judge evaluation failed: %s", exc)
            detail = str(exc).strip()
            feedback = (
                f"Gemini validation request failed: {detail}"
                if detail
                else "Gemini validation request failed. Verify GEMINI_API_KEY, GEMINI_JUDGE_MODEL, "
                "network access, and your Google AI account permissions."
            )
            return JudgeEvaluation(
                overall_score=0.0,
                groundedness=0.0,
                completeness=0.0,
                clarity=0.0,
                feedback=feedback,
                passed=False,
                judge_model="Gemini unavailable",
            )

    def _parse_judge_response(self, raw: str) -> JudgeEvaluation:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in judge response")
        data = json.loads(match.group())
        return JudgeEvaluation(
            overall_score=float(data.get("overall_score", 0)),
            groundedness=float(data.get("groundedness", 0)),
            completeness=float(data.get("completeness", 0)),
            clarity=float(data.get("clarity", 0)),
            feedback=str(data.get("feedback", "")),
            passed=bool(data.get("passed", False)),
        )

    def _heuristic_evaluation(self, profile: HCPProfile, summary: str) -> JudgeEvaluation:
        checks = [
            profile.npi in summary,
            len(summary) > 100,
            profile.identity.primary_specialty.lower() in summary.lower()
            if profile.identity.primary_specialty
            else True,
        ]
        score = sum(checks) / len(checks) * 10
        return JudgeEvaluation(
            overall_score=round(score, 1),
            groundedness=round(score, 1),
            completeness=round(min(score + 1, 10), 1),
            clarity=8.0,
            feedback="Heuristic evaluation (Gemini judge not configured).",
            passed=score >= self.PASS_THRESHOLD,
            judge_model="Heuristic fallback",
        )
