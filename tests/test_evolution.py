import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.evolution.arc_detector import ArcDetector
from src.evolution.conflict_resolver import ResolvedTrait, resolve_conflict, signals_in_window
from src.evolution.snapshot import SnapshotManager
from src.evolution.temporal import std_dev, temporal_weight, weighted_mean
from src.models import BehavioralSignal, UserProfile


class TestTemporalWeight:
    def test_recent_weight(self):
        now = datetime.now(timezone.utc)
        assert temporal_weight(now, now) == 1.0

    def test_30_day_weight(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=15)
        assert temporal_weight(old, now) == 1.0

    def test_60_day_weight(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        assert temporal_weight(old, now) == 0.6

    def test_120_day_weight(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=120)
        assert temporal_weight(old, now) == 0.3

    def test_200_day_weight(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=200)
        assert temporal_weight(old, now) == 0.1

    def test_naive_datetime_handled(self):
        now = datetime.now(timezone.utc)
        old = datetime.now() - timedelta(days=10)  # naive
        weight = temporal_weight(old, now)
        assert weight == 1.0  # within 30 days


class TestWeightedMean:
    def test_equal_weights(self):
        assert weighted_mean([5.0, 10.0], [1.0, 1.0]) == 7.5

    def test_unequal_weights(self):
        result = weighted_mean([5.0, 10.0], [2.0, 1.0])
        assert abs(result - 6.667) < 0.01

    def test_empty(self):
        assert weighted_mean([], []) == 0.0

    def test_zero_weights(self):
        result = weighted_mean([5.0, 10.0], [0.0, 0.0])
        assert result == 7.5  # fallback to simple mean


class TestStdDev:
    def test_no_variance(self):
        assert std_dev([5.0, 5.0, 5.0]) == 0.0

    def test_known_std(self):
        result = std_dev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert abs(result - 2.0) < 0.1

    def test_single_value(self):
        assert std_dev([5.0]) == 0.0


class TestConflictResolver:
    def _make_signal(self, score: float, days_ago: float, confidence: float = 0.8):
        now = datetime.now(timezone.utc)
        return BehavioralSignal(
            user_id=uuid.uuid4(),
            signal_type="temperament",
            signal_value={"score": score},
            confidence=confidence,
            extracted_at=now - timedelta(days=days_ago),
        )

    def test_consistent_recent(self):
        signals = [
            self._make_signal(7.0, 5),
            self._make_signal(7.5, 10),
            self._make_signal(7.2, 15),
            self._make_signal(3.0, 60),
            self._make_signal(2.5, 70),
        ]

        result = resolve_conflict(
            signals, lambda s: s.signal_value.get("score"), now=datetime.now(timezone.utc)
        )

        assert isinstance(result, ResolvedTrait)
        assert result.confidence > 0.5
        assert result.volatility == "low"

    def test_volatile_signals(self):
        signals = [
            self._make_signal(9.0, 1),
            self._make_signal(2.0, 5),
            self._make_signal(8.0, 10),
            self._make_signal(1.0, 15),
        ]

        result = resolve_conflict(
            signals, lambda s: s.signal_value.get("score"), now=datetime.now(timezone.utc)
        )

        assert result.volatility in ("medium", "high")

    def test_empty_signals(self):
        result = resolve_conflict([], lambda s: s.signal_value.get("score"))
        assert result.value == 0.0
        assert result.confidence == 0.0


class TestSignalsInWindow:
    def test_filters_recent(self):
        now = datetime.now(timezone.utc)
        signals = [
            self._make_signal(now - timedelta(days=5)),
            self._make_signal(now - timedelta(days=15)),
            self._make_signal(now - timedelta(days=45)),
        ]

        recent = signals_in_window(signals, days=30, now=now)
        assert len(recent) == 2

    def _make_signal(self, extracted_at):
        return BehavioralSignal(
            user_id=uuid.uuid4(),
            signal_type="test",
            signal_value={},
            confidence=0.8,
            extracted_at=extracted_at,
        )


class TestArcDetector:
    @pytest.mark.asyncio
    async def test_detect_stable_arc(self, db, sample_user_id, sample_signals, sample_profile):
        detector = ArcDetector()
        result = await detector.detect_arc(sample_user_id, db)

        assert "arc" in result
        assert result["confidence"] >= 0.0

    @pytest.mark.asyncio
    async def test_insufficient_data(self, db):
        user_id = uuid.uuid4()
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()

        detector = ArcDetector()
        result = await detector.detect_arc(user_id, db)

        assert result["arc"] == "stable"
        assert result["confidence"] == 0.0


class TestSnapshotManager:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, db, sample_user_id, sample_profile):
        manager = SnapshotManager()
        snapshot = await manager.create_snapshot(sample_user_id, db)

        assert snapshot is not None
        assert snapshot.user_id == sample_user_id
        assert "temperament" in snapshot.snapshot

    @pytest.mark.asyncio
    async def test_should_snapshot_first_time(self, db, sample_user_id, sample_profile):
        manager = SnapshotManager()
        should = await manager.should_snapshot(sample_user_id, db)
        assert should is True

    @pytest.mark.asyncio
    async def test_get_timeline_empty(self, db, sample_user_id, sample_profile):
        manager = SnapshotManager()
        timeline = await manager.get_timeline(sample_user_id, db)
        assert timeline == []

    @pytest.mark.asyncio
    async def test_get_timeline_with_snapshots(self, db, sample_user_id, sample_profile):
        manager = SnapshotManager()
        await manager.create_snapshot(sample_user_id, db)
        await db.flush()

        timeline = await manager.get_timeline(sample_user_id, db)
        assert len(timeline) == 1
        assert timeline[0]["snapshot"]["temperament"] is not None
