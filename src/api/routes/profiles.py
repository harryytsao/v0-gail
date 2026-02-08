import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    DashboardStatsResponse,
    ProfileResponse,
    ProfileTimelineResponse,
    UserListItem,
    UserListResponse,
)
from src.database import get_db
from src.evolution.snapshot import SnapshotManager
from src.models import BehavioralSignal, Conversation, FitScore, UserProfile

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = None,
    has_profile: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List users with pagination and optional search."""
    stmt = select(UserProfile)

    if search:
        stmt = stmt.where(UserProfile.user_id.cast(String).ilike(f"%{search}%"))

    if has_profile is True:
        stmt = stmt.where(UserProfile.temperament.isnot(None))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate — order by updated_at desc, then user_id
    stmt = (
        stmt.order_by(UserProfile.updated_at.desc().nullslast(), UserProfile.user_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    items = []
    for p in profiles:
        temp = p.temperament or {}
        stats = p.interaction_stats or {}
        items.append(
            UserListItem(
                user_id=str(p.user_id),
                primary_language=p.primary_language,
                current_arc=p.current_arc,
                temperament_label=temp.get("label"),
                temperament_score=temp.get("score"),
                total_conversations=stats.get("total_conversations_analyzed"),
                updated_at=p.updated_at,
            )
        )

    return UserListResponse(users=items, total=total, page=page, page_size=page_size)


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard overview stats."""
    total_users = (await db.execute(select(func.count(UserProfile.user_id)))).scalar() or 0
    total_conversations = (await db.execute(select(func.count(Conversation.conversation_id)))).scalar() or 0
    profiled_users = (
        await db.execute(
            select(func.count(UserProfile.user_id)).where(UserProfile.temperament.isnot(None))
        )
    ).scalar() or 0
    scored_users = (
        await db.execute(select(func.count(func.distinct(FitScore.user_id))))
    ).scalar() or 0
    total_signals = (await db.execute(select(func.count(BehavioralSignal.id)))).scalar() or 0

    return DashboardStatsResponse(
        total_users=total_users,
        total_conversations=total_conversations,
        profiled_users=profiled_users,
        scored_users=scored_users,
        total_signals=total_signals,
    )


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get full profile with current scores."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    stmt = select(UserProfile).where(UserProfile.user_id == uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Load latest scores
    scores_stmt = (
        select(FitScore)
        .where(FitScore.user_id == uid)
        .order_by(FitScore.scored_at.desc())
    )
    scores_result = await db.execute(scores_stmt)
    all_scores = scores_result.scalars().all()

    latest_scores = {}
    for score in all_scores:
        if score.dimension not in latest_scores:
            latest_scores[score.dimension] = {
                "score": score.score,
                "reasoning": score.reasoning,
                "scored_at": score.scored_at.isoformat() if score.scored_at else None,
            }

    return ProfileResponse(
        user_id=str(profile.user_id),
        temperament=profile.temperament,
        communication_style=profile.communication_style,
        sentiment_trend=profile.sentiment_trend,
        life_stage=profile.life_stage,
        topic_interests=profile.topic_interests,
        interaction_stats=profile.interaction_stats,
        primary_language=profile.primary_language,
        current_arc=profile.current_arc,
        profile_version=profile.profile_version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        scores=latest_scores,
    )


@router.get("/{user_id}/timeline", response_model=ProfileTimelineResponse)
async def get_timeline(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get profile evolution timeline."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    manager = SnapshotManager()
    timeline = await manager.get_timeline(uid, db)

    return ProfileTimelineResponse(user_id=user_id, timeline=timeline)
