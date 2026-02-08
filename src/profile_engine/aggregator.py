import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import BehavioralSignal, UserProfile

logger = logging.getLogger(__name__)


class ProfileAggregator:
    """Aggregate behavioral signals into a unified user profile."""

    async def aggregate(self, user_id: uuid.UUID, db: AsyncSession) -> UserProfile:
        """Build or update a user profile from all their behavioral signals."""
        stmt = (
            select(BehavioralSignal)
            .where(BehavioralSignal.user_id == user_id)
            .order_by(BehavioralSignal.extracted_at.asc())
        )
        result = await db.execute(stmt)
        signals = result.scalars().all()

        if not signals:
            logger.warning("No signals found for user %s", user_id)
            return await self._get_or_create_profile(user_id, db)

        # Group signals by type
        by_type: dict[str, list[BehavioralSignal]] = {}
        for sig in signals:
            by_type.setdefault(sig.signal_type, []).append(sig)

        profile = await self._get_or_create_profile(user_id, db)

        profile.temperament = self._aggregate_temperament(by_type.get("temperament", []))
        profile.communication_style = self._aggregate_communication_style(
            by_type.get("communication_style", [])
        )
        profile.sentiment_trend = self._aggregate_sentiment(by_type.get("sentiment", []))
        profile.life_stage = self._aggregate_life_stage(by_type.get("life_stage", []))
        profile.topic_interests = self._aggregate_topics(by_type.get("topics", []))
        profile.interaction_stats = self._compute_interaction_stats(signals)
        profile.updated_at = datetime.now(timezone.utc)
        profile.profile_version = (profile.profile_version or 0) + 1

        await db.flush()
        return profile

    async def _get_or_create_profile(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> UserProfile:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            await db.flush()

        return profile

    def _weighted_mean(self, values: list[float], weights: list[float]) -> float:
        if not values:
            return 0.0
        total_w = sum(weights)
        if total_w == 0:
            return sum(values) / len(values)
        return sum(v * w for v, w in zip(values, weights)) / total_w

    def _aggregate_temperament(self, signals: list[BehavioralSignal]) -> dict:
        if not signals:
            return {"score": 5, "label": "neutral", "volatility": "low", "summary": "No data"}

        scores = [s.signal_value.get("score", 5) for s in signals]
        confidences = [s.confidence for s in signals]
        labels = [s.signal_value.get("label", "neutral") for s in signals]

        avg_score = self._weighted_mean(scores, confidences)
        label_counts = Counter(labels)
        dominant_label = label_counts.most_common(1)[0][0]

        # Compute volatility from score std dev
        if len(scores) > 1:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std_dev = variance**0.5
            volatility = "high" if std_dev > 2.5 else ("medium" if std_dev > 1.5 else "low")
        else:
            volatility = "low"

        return {
            "score": round(avg_score, 1),
            "label": dominant_label,
            "volatility": volatility,
            "summary": f"User is generally {dominant_label} (avg {avg_score:.1f}/10, {volatility} volatility)",
        }

    def _aggregate_communication_style(self, signals: list[BehavioralSignal]) -> dict:
        if not signals:
            return {
                "formality": 0.5,
                "verbosity": 0.5,
                "technicality": 0.5,
                "structured": 0.5,
                "summary": "No data",
            }

        dims = ["formality", "verbosity", "technicality", "structured"]
        result = {}
        for dim in dims:
            values = [s.signal_value.get(dim, 0.5) for s in signals]
            weights = [s.confidence for s in signals]
            result[dim] = round(self._weighted_mean(values, weights), 2)

        parts = []
        if result["formality"] > 0.7:
            parts.append("formal")
        elif result["formality"] < 0.3:
            parts.append("casual")
        if result["verbosity"] > 0.7:
            parts.append("verbose")
        elif result["verbosity"] < 0.3:
            parts.append("concise")
        if result["technicality"] > 0.7:
            parts.append("technical")
        elif result["technicality"] < 0.3:
            parts.append("non-technical")
        result["summary"] = ", ".join(parts) if parts else "balanced style"

        return result

    def _aggregate_sentiment(self, signals: list[BehavioralSignal]) -> dict:
        if not signals:
            return {"direction": "stable", "recent_avg": 0.0, "summary": "No data"}

        overall_values = [s.signal_value.get("overall", 0.0) for s in signals]
        recent = overall_values[-5:]  # last 5 conversations
        older = overall_values[:-5] if len(overall_values) > 5 else []

        recent_avg = sum(recent) / len(recent) if recent else 0.0

        if older:
            older_avg = sum(older) / len(older)
            diff = recent_avg - older_avg
            if diff > 0.2:
                direction = "improving"
            elif diff < -0.2:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "stable"

        frustration_count = sum(
            1 for s in signals if s.signal_value.get("frustration_detected", False)
        )
        frustration_rate = frustration_count / len(signals) if signals else 0.0

        return {
            "direction": direction,
            "recent_avg": round(recent_avg, 2),
            "frustration_rate": round(frustration_rate, 2),
            "summary": f"Sentiment is {direction} (recent avg: {recent_avg:.2f})",
        }

    def _aggregate_life_stage(self, signals: list[BehavioralSignal]) -> dict:
        if not signals:
            return {
                "stage": "unknown",
                "confidence": 0.0,
                "domain_expertise": [],
                "signals": [],
            }

        all_indicators = []
        all_domains = []
        for s in signals:
            all_indicators.extend(s.signal_value.get("indicators", []))
            all_domains.extend(s.signal_value.get("domain_expertise", []))

        indicator_counts = Counter(all_indicators)
        domain_counts = Counter(all_domains)

        stage = indicator_counts.most_common(1)[0][0] if indicator_counts else "unknown"
        confidence = min(1.0, indicator_counts.get(stage, 0) / max(len(signals), 1))
        top_domains = [d for d, _ in domain_counts.most_common(5)]

        return {
            "stage": stage,
            "confidence": round(confidence, 2),
            "domain_expertise": top_domains,
            "signals": [f"{ind}: {cnt}x" for ind, cnt in indicator_counts.most_common(5)],
        }

    def _aggregate_topics(self, signals: list[BehavioralSignal]) -> dict:
        if not signals:
            return {"primary": [], "secondary": []}

        all_topics = []
        for s in signals:
            topics = s.signal_value.get("topics", [])
            if isinstance(topics, list):
                all_topics.extend(topics)

        topic_counts = Counter(all_topics)
        sorted_topics = [t for t, _ in topic_counts.most_common()]

        return {
            "primary": sorted_topics[:3],
            "secondary": sorted_topics[3:8],
        }

    def _compute_interaction_stats(self, signals: list[BehavioralSignal]) -> dict:
        conversation_ids = set()
        for s in signals:
            if s.conversation_id:
                conversation_ids.add(s.conversation_id)

        return {
            "total_conversations_analyzed": len(conversation_ids),
            "total_signals": len(signals),
        }
