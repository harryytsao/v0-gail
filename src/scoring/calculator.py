import logging
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import BehavioralSignal, FitScore
from src.scoring.dimensions import DIMENSIONS, DimensionConfig
from src.scoring.reasoning import generate_reasoning

logger = logging.getLogger(__name__)


class ScoreCalculator:
    """Compute dynamic fit scores using recency-weighted behavioral signals."""

    def __init__(self, decay_lambda: float | None = None):
        self.decay_lambda = decay_lambda or settings.score_decay_lambda

    def recency_weight(self, days_since: float) -> float:
        """Exponential decay: exp(-λ * days)"""
        return math.exp(-self.decay_lambda * max(0.0, days_since))

    def _extract_signal_value(self, signal: BehavioralSignal, key: str) -> float | None:
        """Extract a numeric value from a signal given a dotted key."""
        parts = key.split(".")
        if len(parts) != 2:
            return None

        sig_type, field = parts

        if signal.signal_type != sig_type:
            return None

        value = signal.signal_value

        # Handle special computed fields
        if field == "score_inverted":
            raw = value.get("score", 5)
            return (10 - raw) / 10 * 100  # Invert and scale to 0-100

        if field == "overall_inverted":
            raw = value.get("overall", 0.0)
            return (1 - raw) / 2 * 100  # Map [-1,1] inverted to [0,100]

        if field == "frustration_detected":
            return 100.0 if value.get("frustration_detected", False) else 0.0

        if field == "diversity":
            topics = value.get("topics", [])
            if isinstance(topics, list):
                return min(100.0, len(set(topics)) * 20)
            return 50.0

        if field == "domain_count":
            domains = value.get("domain_expertise", [])
            if isinstance(domains, list):
                return min(100.0, len(domains) * 25)
            return 0.0

        if field == "score":
            raw = value.get("score", 5)
            return raw / 10 * 100  # Scale 1-10 to 0-100

        if field == "overall":
            raw = value.get("overall", 0.0)
            return (raw + 1) / 2 * 100  # Map [-1,1] to [0,100]

        # Direct numeric field
        raw = value.get(field)
        if isinstance(raw, (int, float)):
            return raw * 100 if raw <= 1.0 else raw

        return None

    async def compute_score(
        self,
        user_id: uuid.UUID,
        dimension_name: str,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> FitScore:
        """Compute a single dimension score for a user."""
        now = now or datetime.now(timezone.utc)
        dim_config = DIMENSIONS.get(dimension_name)
        if not dim_config:
            raise ValueError(f"Unknown dimension: {dimension_name}")

        # Fetch relevant signals
        stmt = (
            select(BehavioralSignal)
            .where(
                BehavioralSignal.user_id == user_id,
                BehavioralSignal.signal_type.in_(dim_config.signal_types),
            )
            .order_by(BehavioralSignal.extracted_at.desc())
        )
        result = await db.execute(stmt)
        signals = result.scalars().all()

        if not signals:
            return self._default_score(user_id, dimension_name, dim_config, db)

        # Compute weighted score
        weighted_sum = 0.0
        total_weight = 0.0
        component_details = []

        for signal in signals:
            days_since = (now - signal.extracted_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400
            r_weight = self.recency_weight(days_since)

            for key, key_weight in dim_config.signal_weights.items():
                value = self._extract_signal_value(signal, key)
                if value is not None:
                    combined_weight = r_weight * signal.confidence * key_weight
                    weighted_sum += value * combined_weight
                    total_weight += combined_weight
                    component_details.append(
                        {
                            "signal_id": signal.id,
                            "key": key,
                            "value": round(value, 2),
                            "weight": round(combined_weight, 4),
                            "days_ago": round(days_since, 1),
                        }
                    )

        score = weighted_sum / total_weight if total_weight > 0 else dim_config.default_score
        score = max(dim_config.min_score, min(dim_config.max_score, score))

        # Get previous score
        prev_stmt = (
            select(FitScore)
            .where(FitScore.user_id == user_id, FitScore.dimension == dimension_name)
            .order_by(FitScore.scored_at.desc())
            .limit(1)
        )
        prev_result = await db.execute(prev_stmt)
        prev_score_record = prev_result.scalar_one_or_none()
        previous_score = prev_score_record.score if prev_score_record else None

        reasoning_text = generate_reasoning(
            dimension_name, score, previous_score, component_details
        )

        fit_score = FitScore(
            user_id=user_id,
            dimension=dimension_name,
            score=round(score, 1),
            previous_score=previous_score,
            reasoning=reasoning_text,
            component_signals={"components": component_details[:20]},  # top 20 components
        )
        db.add(fit_score)

        return fit_score

    async def compute_all_scores(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> dict[str, FitScore]:
        """Compute all dimension scores for a user."""
        scores = {}
        for dimension_name in DIMENSIONS:
            scores[dimension_name] = await self.compute_score(user_id, dimension_name, db)
        return scores

    def _default_score(
        self,
        user_id: uuid.UUID,
        dimension_name: str,
        dim_config: DimensionConfig,
        db: AsyncSession,
    ) -> FitScore:
        score = FitScore(
            user_id=user_id,
            dimension=dimension_name,
            score=dim_config.default_score,
            previous_score=None,
            reasoning=f"Default score — no behavioral signals available for {dimension_name}",
            component_signals={"components": []},
        )
        db.add(score)
        return score
