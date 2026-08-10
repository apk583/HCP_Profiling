"""ClinicalTrials.gov API v2 collector."""

import logging
from typing import Any

from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class ClinicalTrialsCollector(BaseCollector):
    source_name = "clinical_trials"

    async def collect(self, npi: str, **kwargs: Any) -> dict[str, Any]:
        provider_name: str = kwargs.get("provider_name", "")
        if not provider_name:
            return {"trials": []}

        url = f"{self.settings.clinical_trials_base_url}studies"
        params = {
            "query.term": provider_name,
            "pageSize": "20",
            "format": "json",
        }
        data = await self._get_with_retry(url, params=params)
        if not isinstance(data, dict):
            return {"trials": []}

        studies = data.get("studies", [])
        trials = [self._parse_study(s) for s in studies]
        logger.info("ClinicalTrials: found %d trials for %s", len(trials), provider_name)
        return {"trials": trials}

    def _parse_study(self, study: dict[str, Any]) -> dict[str, Any]:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        contacts = protocol.get("contactsLocationsModule", {})
        officials = contacts.get("overallOfficials", [])

        role = ""
        if officials:
            role = officials[0].get("role", "")

        phases = design.get("phases", [])
        return {
            "nct_id": ident.get("nctId", ""),
            "title": ident.get("briefTitle", ident.get("officialTitle", "")),
            "status": status_mod.get("overallStatus", ""),
            "phase": ", ".join(phases) if phases else "N/A",
            "role": role,
            "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
        }
