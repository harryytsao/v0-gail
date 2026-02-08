import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.adaptation_rules import generate_adaptation_rules, get_adaptation_summary
from src.agent.live_agent import LiveAgent
from src.agent.prompt_builder import build_system_prompt
from src.api.schemas import (
    AdaptationPreviewResponse,
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
)
from src.database import get_db, get_redis
from src.models import Conversation, FitScore, UserProfile

router = APIRouter(prefix="/api/agent", tags=["agent"])

_agent: LiveAgent | None = None


def _get_agent() -> LiveAgent:
    global _agent
    if _agent is None:
        _agent = LiveAgent()
    return _agent


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a profile-adapted response."""
    try:
        user_uuid = uuid.UUID(request.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    conv_id = uuid.UUID(request.conversation_id) if request.conversation_id else None

    try:
        redis_client = get_redis()
    except Exception:
        redis_client = None

    try:
        result = await _get_agent().chat(
            user_id=user_uuid,
            message=request.message,
            db=db,
            conversation_id=conv_id,
            redis_client=redis_client,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
    finally:
        if redis_client:
            await redis_client.aclose()

    # Trigger async profile update in background
    conv_uuid = uuid.UUID(result["conversation_id"])
    background_tasks.add_task(_async_profile_update, conv_uuid)

    return ChatResponse(**result)


async def _async_profile_update(conversation_id: uuid.UUID):
    """Background task to extract signals from the conversation."""
    from src.database import async_session

    try:
        async with async_session() as db:
            agent = LiveAgent()
            await agent.extract_and_update(conversation_id, db)
            await db.commit()
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Background profile update failed for %s", conversation_id
        )


@router.get("/chat/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db)
):
    """Get conversation history."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    stmt = select(Conversation).where(Conversation.conversation_id == conv_uuid)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistoryResponse(
        conversation_id=str(conv.conversation_id),
        user_id=str(conv.user_id),
        messages=conv.messages or [],
        total_turns=conv.total_turns,
    )


@router.get("/adaptation/{user_id}", response_model=AdaptationPreviewResponse)
async def preview_adaptation(user_id: str, db: AsyncSession = Depends(get_db)):
    """Preview how agent would adapt for this user."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    stmt = select(UserProfile).where(UserProfile.user_id == uid)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Load scores
    scores_stmt = (
        select(FitScore)
        .where(FitScore.user_id == uid)
        .order_by(FitScore.scored_at.desc())
    )
    scores_result = await db.execute(scores_stmt)
    all_scores = scores_result.scalars().all()

    scores = {}
    for score in all_scores:
        if score.dimension not in scores:
            scores[score.dimension] = score

    system_prompt = build_system_prompt(profile, scores)
    adaptations = get_adaptation_summary(profile, scores)

    temp = profile.temperament or {}
    style = profile.communication_style or {}
    escalation = scores.get("escalation_risk")

    return AdaptationPreviewResponse(
        user_id=user_id,
        system_prompt_preview=system_prompt,
        adaptations=adaptations,
        profile_summary={
            "temperament": temp.get("label", "unknown"),
            "style": style.get("summary", "unknown"),
            "escalation_risk": escalation.score if escalation else None,
            "current_arc": profile.current_arc,
        },
    )
