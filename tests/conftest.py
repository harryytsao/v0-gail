import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Force a dummy provider config so imports don't fail during tests
os.environ.setdefault("GAIL_LLM_PROVIDER", "anthropic")
os.environ.setdefault("GAIL_ANTHROPIC_API_KEY", "test-key-not-used")

import pytest
import pytest_asyncio
from sqlalchemy import JSON, String, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base
from src.models import BehavioralSignal, Conversation, FitScore, UserProfile

# Use SQLite for tests — remap PostgreSQL types
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    # Remap PostgreSQL-specific types to SQLite-compatible types
    # so create_all works with SQLite
    _remap_pg_types()

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _remap_pg_types():
    """Remap JSONB→JSON and UUID→String(36) for SQLite compatibility."""
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    # Only patch once
    if getattr(SQLiteTypeCompiler, "_gail_patched", False):
        return
    SQLiteTypeCompiler._gail_patched = True

    original_process = SQLiteTypeCompiler.process

    def patched_process(self, type_, **kw):
        if isinstance(type_, JSONB):
            return self.process(JSON(), **kw)
        if isinstance(type_, UUID):
            return "VARCHAR(36)"
        return original_process(self, type_, **kw)

    SQLiteTypeCompiler.process = patched_process


@pytest_asyncio.fixture
async def db(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_user_id():
    return uuid.UUID("55798ace-d5ae-4797-a94f-3bc2f705d8c8")


@pytest.fixture
def sample_conversation_id():
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest_asyncio.fixture
async def sample_profile(db, sample_user_id):
    profile = UserProfile(
        user_id=sample_user_id,
        temperament={"score": 7, "label": "patient", "volatility": "low", "summary": "Calm user"},
        communication_style={
            "formality": 0.6,
            "verbosity": 0.4,
            "technicality": 0.8,
            "structured": 0.7,
            "summary": "formal, concise, technical",
        },
        sentiment_trend={"direction": "stable", "recent_avg": 0.3, "summary": "Neutral"},
        life_stage={"stage": "professional", "confidence": 0.85, "domain_expertise": ["software"]},
        topic_interests={"primary": ["technology", "legal"], "secondary": ["math"]},
        interaction_stats={"total_conversations_analyzed": 5, "total_signals": 30},
        primary_language="English",
        current_arc="stable",
    )
    db.add(profile)
    await db.flush()
    return profile


@pytest_asyncio.fixture
async def sample_signals(db, sample_user_id, sample_conversation_id):
    signals = [
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="temperament",
            signal_value={"score": 7, "label": "patient", "evidence": "polite language"},
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc),
        ),
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="communication_style",
            signal_value={"formality": 0.7, "verbosity": 0.3, "technicality": 0.9, "structured": 0.6},
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc),
        ),
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="sentiment",
            signal_value={"overall": 0.4, "arc": "stable", "frustration_detected": False},
            confidence=0.7,
            extracted_at=datetime.now(timezone.utc),
        ),
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="cooperation",
            signal_value={"follows_instructions": 0.8, "provides_context": 0.7, "politeness": 0.9},
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc),
        ),
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="life_stage",
            signal_value={"indicators": ["professional"], "confidence": 0.8, "domain_expertise": ["software"]},
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc),
        ),
        BehavioralSignal(
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            signal_type="topics",
            signal_value={"topics": ["technology", "software"]},
            confidence=0.7,
            extracted_at=datetime.now(timezone.utc),
        ),
    ]
    for s in signals:
        db.add(s)
    await db.flush()
    return signals


@pytest.fixture
def sample_messages():
    return [
        {"role": "user", "content": "Can you help me understand credit monitoring?", "message_index": 0},
        {"role": "assistant", "content": "Credit monitoring tracks changes to your credit reports...", "message_index": 1},
        {"role": "user", "content": "What about identity theft protection?", "message_index": 2},
        {"role": "assistant", "content": "Identity theft protection includes monitoring...", "message_index": 3},
    ]


@pytest.fixture
def mock_anthropic():
    """Create a mock LLM client for tests."""
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(
        return_value='{"temperament":{"score":7,"label":"patient","evidence":"polite"},"communication_style":{"formality":0.6,"verbosity":0.4,"technicality":0.8,"structured":0.7},"sentiment":{"overall":0.3,"arc":"stable","frustration_detected":false},"life_stage":{"indicators":["professional"],"confidence":0.8,"domain_expertise":["finance"]},"topics":["finance","identity protection"],"cooperation":{"follows_instructions":0.8,"provides_context":0.7,"politeness":0.9}}'
    )
    mock_client.chat = AsyncMock(return_value="Hello! How can I help you?")
    return mock_client
