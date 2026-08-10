"""Base collector with retry logic and shared HTTP client."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    source_name: str = "unknown"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "BaseCollector":
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.settings.http_timeout_seconds,
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Collector client not initialized")
        return self._client

    async def _get_with_retry(self, url: str, params: dict | None = None) -> dict | list | str:
        last_error: Exception | None = None
        for attempt in range(self.settings.http_max_retries):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    return response.json()
                return response.text
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                wait = 2**attempt
                logger.warning(
                    "%s request failed (attempt %d/%d): %s",
                    self.source_name,
                    attempt + 1,
                    self.settings.http_max_retries,
                    exc,
                )
                if attempt < self.settings.http_max_retries - 1:
                    await asyncio.sleep(wait)
        raise RuntimeError(f"{self.source_name} request failed after retries: {last_error}")

    @abstractmethod
    async def collect(self, npi: str, **kwargs: Any) -> dict[str, Any]:
        """Collect raw data for the given NPI."""
