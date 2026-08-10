"""Grounded AI summary generation for HCP profiles."""

import json
import logging

from app.config import Settings
from app.schemas.hcp import HCPProfile
from app.services.ai.client import GroqService
from app.services.normalizer import ProfileNormalizer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a healthcare intelligence analyst specializing in HCP (Healthcare Professional) profiling.
Generate concise, factual summaries grounded ONLY in the provided data.
Do not invent credentials, affiliations, or achievements not present in the data.
Use professional language suitable for pharmaceutical field teams.
Structure the summary with: Overview, Clinical Activity, Research Collaboration Insights, and Influence Assessment."""


class SummaryGenerator:
    def __init__(self, settings: Settings):
        self.ai = GroqService(settings)
        self.settings = settings

    def generate(self, profile: HCPProfile) -> str:
        if not self.ai.is_configured:
            return self._fallback_summary(profile)

        context = self._build_context(profile)
        user_prompt = f"""Based on the following verified HCP data, write a comprehensive intelligence summary.

DATA:
{context}

Write a 300-500 word summary covering clinical activity, research output, collaboration-network insights, and KOL potential.
Only cite facts present in the data above."""

        try:
            return self.ai.chat(
                model=self.settings.groq_model,
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.3,
            )
        except Exception as exc:
            logger.error("Summary generation failed: %s", exc)
            return self._fallback_summary(profile)

    def _build_context(self, profile: HCPProfile) -> str:
        identity = profile.identity
        name = ProfileNormalizer.provider_display_name(identity)
        data = {
            "name": name,
            "npi": profile.npi,
            "specialty": identity.primary_specialty,
            "location": f"{identity.address.city}, {identity.address.state}",
            "publications_count": len(profile.publications),
            "top_publications": [p.title for p in profile.publications[:5]],
            "clinical_trials_count": len(profile.clinical_trials),
            "trials": [
                {"title": t.title, "status": t.status, "role": t.role}
                for t in profile.clinical_trials[:5]
            ],
            "collaboration_metrics": profile.collaboration_network.metrics.model_dump() if profile.collaboration_network else {},
            "ml_influence_scores": [
                {"model": p.model_name, "score": p.influence_score, "tier": p.kol_tier}
                for p in profile.ml_predictions
            ],
        }
        return json.dumps(data, indent=2)

    def _fallback_summary(self, profile: HCPProfile) -> str:
        identity = profile.identity
        name = ProfileNormalizer.provider_display_name(identity)
        best_ml = profile.ml_predictions[0] if profile.ml_predictions else None
        tier = best_ml.kol_tier if best_ml else "Not assessed"
        score = best_ml.influence_score if best_ml else 0

        return f"""## Overview
{name} (NPI: {profile.npi}) is a {identity.primary_specialty or 'healthcare provider'} based in {identity.address.city}, {identity.address.state}.

## Clinical Activity
- Publications indexed: {len(profile.publications)}
- Clinical trials associated: {len(profile.clinical_trials)}
- Years active (since NPI enumeration): {profile.features.years_active}

## Research Collaboration Insights
- Unique collaborators: {profile.features.unique_collaborator_count}
- Strongest collaborator: {profile.collaboration_network.metrics.strongest_collaborator if profile.collaboration_network else 'N/A'}
- Shared publications with strongest collaborator: {profile.features.strongest_collaboration_count}
- Average collaborations per author: {profile.features.average_collaboration_strength}

## Influence Assessment
- Predicted influence score: {score}/100
- KOL tier: {tier}

*Note: AI summary unavailable — configure Groq API for enhanced narratives.*"""
