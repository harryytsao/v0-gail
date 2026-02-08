import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import AllScoresResponse, ScoreHistoryResponse, ScoreResponse
from src.database import get_db
from src.models import FitScore
from src.scoring.dimensions import DIMENSIONS

router = APIRouter(prefix="/api/profiles", tags=["scores"])


@router.get("/{user_id}/scores", response_model=AllScoresResponse)
async def get_all_scores(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all current fit scores with reasoning."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    scores_stmt = (
        select(FitScore)
        .where(FitScore.user_id == uid)
        .order_by(FitScore.scored_at.desc())
    )
    result = await db.execute(scores_stmt)
    all_scores = result.scalars().all()

    latest = {}
    for score in all_scores:
        if score.dimension not in latest:
            latest[score.dimension] = ScoreResponse(
                dimension=score.dimension,
                score=score.score,
                previous_score=score.previous_score,
                reasoning=score.reasoning,
                scored_at=score.scored_at,
            )

    return AllScoresResponse(
        user_id=user_id,
        scores=list(latest.values()),
    )


@router.get("/{user_id}/scores/{dimension}", response_model=ScoreHistoryResponse)
async def get_score_history(
    user_id: str,
    dimension: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get score history for a specific dimension."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    if dimension not in DIMENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dimension: {dimension}. Valid: {list(DIMENSIONS.keys())}",
        )

    stmt = (
        select(FitScore)
        .where(FitScore.user_id == uid, FitScore.dimension == dimension)
        .order_by(FitScore.scored_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    scores = result.scalars().all()

    return ScoreHistoryResponse(
        user_id=user_id,
        dimension=dimension,
        history=[
            ScoreResponse(
                dimension=s.dimension,
                score=s.score,
                previous_score=s.previous_score,
                reasoning=s.reasoning,
                scored_at=s.scored_at,
            )
            for s in scores
        ],
    )
