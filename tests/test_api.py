import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.database import Base, get_db
from src.models import UserProfile


@pytest_asyncio.fixture
async def client(db):
    """Create test client with DB override."""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "gail"


class TestProfileEndpoints:
    @pytest.mark.asyncio
    async def test_get_profile(self, client, sample_profile):
        response = await client.get(f"/api/profiles/{sample_profile.user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_profile.user_id)
        assert data["temperament"]["label"] == "patient"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/profiles/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_profile_invalid_id(self, client):
        response = await client.get("/api/profiles/not-a-uuid")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_timeline(self, client, sample_profile):
        response = await client.get(f"/api/profiles/{sample_profile.user_id}/timeline")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_profile.user_id)
        assert isinstance(data["timeline"], list)


class TestScoreEndpoints:
    @pytest.mark.asyncio
    async def test_get_scores_empty(self, client, sample_profile):
        response = await client.get(f"/api/profiles/{sample_profile.user_id}/scores")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["scores"], list)

    @pytest.mark.asyncio
    async def test_get_score_history_invalid_dimension(self, client, sample_profile):
        response = await client.get(
            f"/api/profiles/{sample_profile.user_id}/scores/nonexistent"
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_score_history(self, client, sample_profile):
        response = await client.get(
            f"/api/profiles/{sample_profile.user_id}/scores/cooperation_level"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dimension"] == "cooperation_level"


class TestBatchEndpoints:
    @pytest.mark.asyncio
    async def test_get_status(self, client):
        response = await client.get("/api/batch/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_recompute_invalid_id(self, client):
        response = await client.post("/api/batch/recompute/not-a-uuid")
        assert response.status_code == 400


class TestAdaptationEndpoint:
    @pytest.mark.asyncio
    async def test_preview_adaptation(self, client, sample_profile):
        response = await client.get(f"/api/agent/adaptation/{sample_profile.user_id}")
        assert response.status_code == 200
        data = response.json()
        assert "system_prompt_preview" in data
        assert "Gail" in data["system_prompt_preview"]
        assert isinstance(data["adaptations"], list)

    @pytest.mark.asyncio
    async def test_preview_adaptation_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/agent/adaptation/{fake_id}")
        assert response.status_code == 404
