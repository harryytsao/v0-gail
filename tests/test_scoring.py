import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.models import BehavioralSignal
from src.scoring.calculator import ScoreCalculator
from src.scoring.dimensions import DIMENSIONS
from src.scoring.reasoning import generate_reasoning


class TestScoreCalculator:
    def test_recency_weight(self):
        calc = ScoreCalculator(decay_lambda=0.03)

        # Today: weight = 1.0
        assert abs(calc.recency_weight(0) - 1.0) < 0.001

        # ~23 days: half-life
        half_life_weight = calc.recency_weight(23.1)
        assert abs(half_life_weight - 0.5) < 0.05

        # 100 days: much lower
        assert calc.recency_weight(100) < 0.1

    @pytest.mark.asyncio
    async def test_compute_score_with_signals(self, db, sample_user_id, sample_signals, sample_profile):
        calc = ScoreCalculator()

        score = await calc.compute_score(sample_user_id, "cooperation_level", db)
        assert score is not None
        assert 0 <= score.score <= 100
        assert score.dimension == "cooperation_level"
        assert score.reasoning is not None

    @pytest.mark.asyncio
    async def test_compute_all_scores(self, db, sample_user_id, sample_signals, sample_profile):
        calc = ScoreCalculator()

        scores = await calc.compute_all_scores(sample_user_id, db)
        assert len(scores) == len(DIMENSIONS)
        for dim_name, score in scores.items():
            assert dim_name in DIMENSIONS
            assert 0 <= score.score <= 100

    @pytest.mark.asyncio
    async def test_default_score_no_signals(self, db):
        user_id = uuid.uuid4()
        from src.models import UserProfile
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()

        calc = ScoreCalculator()
        score = await calc.compute_score(user_id, "responsiveness", db)

        assert score.score == 50.0  # default
        assert "Default" in score.reasoning or "no behavioral" in score.reasoning.lower()

    @pytest.mark.asyncio
    async def test_expertise_score(self, db, sample_user_id, sample_signals, sample_profile):
        calc = ScoreCalculator()

        score = await calc.compute_score(sample_user_id, "expertise_level", db)
        # User has high technicality (0.9) so expertise should be above average
        assert score.score > 50

    @pytest.mark.asyncio
    async def test_escalation_risk_for_calm_user(self, db, sample_user_id, sample_signals, sample_profile):
        calc = ScoreCalculator()

        score = await calc.compute_score(sample_user_id, "escalation_risk", db)
        # User has temperament 7/10 and positive sentiment, risk should be moderate-low
        assert score.score < 60

    def test_unknown_dimension(self, db, sample_user_id):
        calc = ScoreCalculator()
        with pytest.raises(ValueError, match="Unknown dimension"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                calc.compute_score(sample_user_id, "nonexistent", db)
            )


class TestDimensions:
    def test_all_dimensions_defined(self):
        expected = [
            "responsiveness",
            "escalation_risk",
            "engagement_quality",
            "cooperation_level",
            "expertise_level",
        ]
        for dim in expected:
            assert dim in DIMENSIONS
            assert DIMENSIONS[dim].min_score == 0.0
            assert DIMENSIONS[dim].max_score == 100.0


class TestReasoning:
    def test_generate_reasoning_with_change(self):
        result = generate_reasoning(
            "escalation_risk",
            52.0,
            35.0,
            [
                {"signal_id": 1, "key": "temperament.score_inverted", "value": 30.0, "weight": 0.5, "days_ago": 2.0},
                {"signal_id": 2, "key": "sentiment.frustration_detected", "value": 100.0, "weight": 0.3, "days_ago": 5.0},
            ],
        )

        assert "Escalation risk" in result
        assert "increased" in result
        assert "35" in result
        assert "52" in result

    def test_generate_reasoning_no_change(self):
        result = generate_reasoning("cooperation_level", 75.0, 75.0, [])
        assert "No significant change" in result

    def test_generate_reasoning_no_previous(self):
        result = generate_reasoning("expertise_level", 80.0, None, [])
        assert "high" in result
        assert "80" in result
