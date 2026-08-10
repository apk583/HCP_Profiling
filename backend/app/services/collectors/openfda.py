"""OpenFDA adverse event collector."""

import logging
from typing import Any

from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class OpenFDACollector(BaseCollector):
    source_name = "openfda"

    async def collect(self, npi: str, **kwargs: Any) -> dict[str, Any]:
        provider_name: str = kwargs.get("provider_name", "")
        if not provider_name:
            return {"adverse_events": []}

        url = f"{self.settings.openfda_base_url}drug/event.json"
        params = {
            "search": f'patient.drug.openfda.brand_name:"*" AND reportercountry:"US"',
            "limit": 5,
        }

        try:
            data = await self._get_with_retry(url, params=params)
        except RuntimeError as exc:
            logger.warning("OpenFDA unavailable: %s", exc)
            return {"adverse_events": [], "error": str(exc)}

        if not isinstance(data, dict):
            return {"adverse_events": []}

        results = data.get("results", [])
        summaries = self._aggregate_events(results)
        logger.info("OpenFDA: aggregated %d drug summaries", len(summaries))
        return {"adverse_events": summaries}

    def _aggregate_events(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        drug_counts: dict[str, dict[str, int]] = {}
        for event in results:
            drugs = event.get("patient", {}).get("drug", [])
            serious = 1 if event.get("serious") == "1" else 0
            for drug in drugs:
                name = drug.get("openfda", {}).get("brand_name", [""])
                drug_name = name[0] if name else drug.get("medicinalproduct", "Unknown")
                if drug_name not in drug_counts:
                    drug_counts[drug_name] = {"event_count": 0, "serious_count": 0}
                drug_counts[drug_name]["event_count"] += 1
                drug_counts[drug_name]["serious_count"] += serious

        return [
            {
                "drug_name": name,
                "event_count": counts["event_count"],
                "serious_count": counts["serious_count"],
            }
            for name, counts in drug_counts.items()
        ]
