import uuid
from datetime import datetime, timezone

import pytest

from src.models import BehavioralSignal, UserProfile
from src.profile_engine.aggregator import ProfileAggregator


class TestProfileAggregator:
    @pytest.mark.asyncio
    async def test_aggregate_creates_profile(self, db, sample_user_id, sample_signals):
        aggregator = ProfileAggregator()
        profile = await aggregator.aggregate(sample_user_id, db)

        assert profile is not None
        assert profile.user_id == sample_user_id
        assert profile.temperament is not None
        assert profile.temperament["label"] == "patient"

    @pytest.mark.asyncio
    async def test_aggregate_communication_style(self, db, sample_user_id, sample_signals):
        aggregator = ProfileAggregator()
        profile = await aggregator.aggregate(sample_user_id, db)

        style = profile.communication_style
        assert style is not None
        assert 0.0 <= style["formality"] <= 1.0
        assert "summary" in style

    @pytest.mark.asyncio
    async def test_aggregate_sentiment(self, db, sample_user_id, sample_signals):
        aggregator = ProfileAggregator()
        profile = await aggregator.aggregate(sample_user_id, db)

        sentiment = profile.sentiment_trend
        assert sentiment is not None
        assert sentiment["direction"] in ("stable", "improving", "declining", "volatile")

    @pytest.mark.asyncio
    async def test_aggregate_no_signals(self, db):
        user_id = uuid.uuid4()
        # Create empty profile
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()

        aggregator = ProfileAggregator()
        result = await aggregator.aggregate(user_id, db)

        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_aggregate_updates_version(self, db, sample_user_id, sample_signals):
        # First create profile
        profile = UserProfile(user_id=sample_user_id, profile_version=1)
        db.add(profile)
        await db.flush()

        aggregator = ProfileAggregator()
        updated = await aggregator.aggregate(sample_user_id, db)

        assert updated.profile_version >= 2

    @pytest.mark.asyncio
    async def test_topic_aggregation(self, db, sample_user_id, sample_signals):
        aggregator = ProfileAggregator()
        profile = await aggregator.aggregate(sample_user_id, db)

        topics = profile.topic_interests
        assert topics is not None
        assert "primary" in topics

    @pytest.mark.asyncio
    async def test_weighted_mean(self):
        aggregator = ProfileAggregator()

        result = aggregator._weighted_mean([5.0, 10.0], [1.0, 1.0])
        assert result == 7.5

        result = aggregator._weighted_mean([5.0, 10.0], [2.0, 1.0])
        assert abs(result - 6.67) < 0.01

        result = aggregator._weighted_mean([], [])
        assert result == 0.0
