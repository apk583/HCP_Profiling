"""NPI Registry API collector."""

import logging
from typing import Any

from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class NPIRegistryCollector(BaseCollector):
    source_name = "npi_registry"

    async def collect(self, npi: str, **kwargs: Any) -> dict[str, Any]:
        url = self.settings.npi_registry_base_url
        params = {"version": "2.1", "number": npi}
        data = await self._get_with_retry(url, params=params)
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected NPI Registry response format")
        result_count = data.get("result_count", 0)
        if result_count == 0:
            raise ValueError(f"No provider found for NPI {npi}")
        logger.info("NPI Registry returned %d result(s) for NPI %s", result_count, npi)
        return data
