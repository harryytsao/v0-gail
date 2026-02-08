import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evolution.conflict_resolver import signals_in_window
from src.evolution.temporal import std_dev, weighted_mean
from src.models import BehavioralSignal, UserProfile

logger = logging.getLogger(__name__)

# Named behavioral arcs
ARCS = {
    "rehabilitation": "hostile → neutral → cooperative",
    "churn": "engaged → declining → disengaged",
    "growth": "casual → technical → expert",
    "stable": "consistent behavior over time",
    "volatile": "unpredictable behavior pattern",
    "warming": "cold → warming → engaged",
    "cooling": "engaged → cooling → disengaged",
}


class ArcDetector:
    """Detect behavioral arcs by comparing trait clusters across time windows."""

    async def detect_arc(
        self, user_id: uuid.UUID, db: AsyncSession, now: datetime | None = None
    ) -> dict:
        """Detect behavioral arc for a user by analyzing signals across time windows."""
        now = now or datetime.now(timezone.utc)

        stmt = (
            select(BehavioralSignal)
            .where(BehavioralSignal.user_id == user_id)
            .order_by(BehavioralSignal.extracted_at.asc())
        )
        result = await db.execute(stmt)
        signals = result.scalars().all()

        if len(signals) < 3:
            return {"arc": "stable", "confidence": 0.0, "detail": "Insufficient data"}

        # Analyze temperament arc
        temperament_signals = [s for s in signals if s.signal_type == "temperament"]
        temperament_arc = self._analyze_trait_arc(
            temperament_signals,
            value_fn=lambda s: s.signal_value.get("score", 5),
            now=now,
        )

        # Analyze engagement arc (from communication style verbosity + cooperation)
        engagement_signals = [
            s for s in signals if s.signal_type in ("communication_style", "cooperation")
        ]
        engagement_arc = self._analyze_trait_arc(
            engagement_signals,
            value_fn=lambda s: (
                s.signal_value.get("verbosity", 0.5)
                if s.signal_type == "communication_style"
                else s.signal_value.get("provides_context", 0.5)
            ),
            now=now,
        )

        # Analyze expertise arc
        expertise_signals = [s for s in signals if s.signal_type == "communication_style"]
        expertise_arc = self._analyze_trait_arc(
            expertise_signals,
            value_fn=lambda s: s.signal_value.get("technicality", 0.5),
            now=now,
        )

        # Determine dominant arc
        arc_label, confidence = self._determine_dominant_arc(
            temperament_arc, engagement_arc, expertise_arc
        )

        # Update user profile
        profile_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        profile_result = await db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.current_arc = arc_label

        return {
            "arc": arc_label,
            "confidence": confidence,
            "detail": ARCS.get(arc_label, ""),
            "sub_arcs": {
                "temperament": temperament_arc,
                "engagement": engagement_arc,
                "expertise": expertise_arc,
            },
        }

    def _analyze_trait_arc(
        self,
        signals: list[BehavioralSignal],
        value_fn: callable,
        now: datetime,
    ) -> dict:
        """Analyze arc for a single trait dimension."""
        if len(signals) < 2:
            return {"direction": "stable", "magnitude": 0.0, "shift_detected": False}

        recent = signals_in_window(signals, days=30, now=now)
        historical = signals_in_window(signals, days=90, now=now)

        recent_values = [v for v in (value_fn(s) for s in recent) if v is not None]
        historical_values = [v for v in (value_fn(s) for s in historical) if v is not None]

        if not recent_values or not historical_values:
            return {"direction": "stable", "magnitude": 0.0, "shift_detected": False}

        recent_mean = sum(recent_values) / len(recent_values)
        historical_mean = sum(historical_values) / len(historical_values)
        historical_std = std_dev(historical_values)

        diff = recent_mean - historical_mean
        shift_detected = abs(diff) > 2 * max(historical_std, 0.5)

        if diff > 0.5:
            direction = "increasing"
        elif diff < -0.5:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "magnitude": round(abs(diff), 2),
            "shift_detected": shift_detected,
            "recent_mean": round(recent_mean, 2),
            "historical_mean": round(historical_mean, 2),
        }

    def _determine_dominant_arc(
        self, temperament: dict, engagement: dict, expertise: dict
    ) -> tuple[str, float]:
        """Determine the dominant behavioral arc from sub-arcs."""
        # Check for rehabilitation arc: temperament increasing
        if (
            temperament.get("direction") == "increasing"
            and temperament.get("shift_detected")
        ):
            return "rehabilitation", min(1.0, temperament["magnitude"] / 3.0)

        # Check for churn arc: engagement decreasing
        if (
            engagement.get("direction") == "decreasing"
            and engagement.get("shift_detected")
        ):
            return "churn", min(1.0, engagement["magnitude"] / 0.5)

        # Check for growth arc: expertise increasing
        if (
            expertise.get("direction") == "increasing"
            and expertise.get("shift_detected")
        ):
            return "growth", min(1.0, expertise["magnitude"] / 0.5)

        # Check for cooling: temperament or engagement decreasing
        if temperament.get("direction") == "decreasing" or engagement.get("direction") == "decreasing":
            mag = max(temperament.get("magnitude", 0), engagement.get("magnitude", 0))
            return "cooling", min(1.0, mag / 2.0)

        # Check for warming: temperament increasing (but not significant shift)
        if temperament.get("direction") == "increasing":
            return "warming", min(1.0, temperament.get("magnitude", 0) / 2.0)

        # Check for volatility
        shifts = sum(
            1
            for arc in (temperament, engagement, expertise)
            if arc.get("shift_detected")
        )
        if shifts >= 2:
            return "volatile", 0.7

        return "stable", 0.5
