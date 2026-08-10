"""Backend test suite."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "gemini_configured" in data


@pytest.mark.asyncio
async def test_hcp_invalid_npi(client):
    response = await client.post("/api/v1/hcp/profile", json={"npi": "abc"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_hcp_short_npi(client):
    response = await client.post("/api/v1/hcp/profile", json={"npi": "12345"})
    assert response.status_code == 422
