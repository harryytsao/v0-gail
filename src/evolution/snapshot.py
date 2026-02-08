import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import FitScore, ProfileSnapshot, UserProfile

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manage profile snapshots for evolution tracking."""

    async def create_snapshot(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> ProfileSnapshot | None:
        """Create a snapshot of the user's current profile state."""
        # Load current profile
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning("Cannot snapshot: no profile for user %s", user_id)
            return None

        # Load current scores
        scores_stmt = (
            select(FitScore)
            .where(FitScore.user_id == user_id)
            .order_by(FitScore.scored_at.desc())
        )
        scores_result = await db.execute(scores_stmt)
        all_scores = scores_result.scalars().all()

        # Get latest score per dimension
        latest_scores = {}
        for score in all_scores:
            if score.dimension not in latest_scores:
                latest_scores[score.dimension] = {
                    "score": score.score,
                    "reasoning": score.reasoning,
                }

        snapshot_data = {
            "temperament": profile.temperament,
            "communication_style": profile.communication_style,
            "sentiment_trend": profile.sentiment_trend,
            "life_stage": profile.life_stage,
            "topic_interests": profile.topic_interests,
            "interaction_stats": profile.interaction_stats,
            "primary_language": profile.primary_language,
            "current_arc": profile.current_arc,
            "profile_version": profile.profile_version,
            "scores": latest_scores,
        }

        snapshot = ProfileSnapshot(
            user_id=user_id,
            snapshot=snapshot_data,
            arc_label=profile.current_arc,
        )
        db.add(snapshot)
        return snapshot

    async def get_timeline(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 52,
    ) -> list[dict]:
        """Get profile evolution timeline (list of snapshots)."""
        stmt = (
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == user_id)
            .order_by(ProfileSnapshot.snapshot_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        snapshots = result.scalars().all()

        return [
            {
                "id": snap.id,
                "snapshot_at": snap.snapshot_at.isoformat() if snap.snapshot_at else None,
                "arc_label": snap.arc_label,
                "snapshot": snap.snapshot,
            }
            for snap in reversed(snapshots)
        ]

    async def should_snapshot(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        interval_days: int = 7,
    ) -> bool:
        """Check if enough time has passed since the last snapshot."""
        stmt = (
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == user_id)
            .order_by(ProfileSnapshot.snapshot_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest is None:
            return True

        now = datetime.now(timezone.utc)
        last_at = latest.snapshot_at.replace(tzinfo=timezone.utc)
        days_since = (now - last_at).total_seconds() / 86400
        return days_since >= interval_days
