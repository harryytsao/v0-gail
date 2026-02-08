import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.adaptation_rules import get_adaptation_summary
from src.agent.prompt_builder import build_default_prompt, build_system_prompt
from src.config import settings
from src.llm import LLMClient, get_llm_client
from src.models import BehavioralSignal, Conversation, FitScore, UserProfile
from src.profile_engine.extractor import TraitExtractor

logger = logging.getLogger(__name__)


class LiveAgent:
    def __init__(self, api_key: str | None = None, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()
        self.extractor = TraitExtractor(llm_client=self.llm)

    async def chat(
        self,
        user_id: uuid.UUID,
        message: str,
        db: AsyncSession,
        conversation_id: uuid.UUID | None = None,
        redis_client=None,
    ) -> dict:
        """Send a message and get a profile-adapted response."""
        # Load profile and scores
        profile, scores = await self._load_profile_and_scores(
            user_id, db, redis_client
        )

        # Build adapted system prompt
        if profile:
            system_prompt = build_system_prompt(profile, scores)
        else:
            system_prompt = build_default_prompt()

        # Load or create conversation
        conversation_id = conversation_id or uuid.uuid4()
        history = await self._load_conversation_history(conversation_id, db)

        # Build messages list
        messages = history + [{"role": "user", "content": message}]

        # Call LLM
        assistant_message = await self.llm.chat(
            system=system_prompt,
            messages=messages,
            model=settings.resolved_agent_model,
            max_tokens=settings.max_agent_tokens,
        )

        # Store conversation
        await self._save_conversation(
            conversation_id, user_id, messages, assistant_message, db
        )

        # Get adaptation summary
        adaptations = (
            get_adaptation_summary(profile, scores)
            if profile
            else ["No profile available — using default behavior"]
        )

        # Build profile summary for response
        profile_summary = self._build_profile_summary(profile, scores)

        return {
            "response": assistant_message,
            "conversation_id": str(conversation_id),
            "adaptations_applied": adaptations,
            "profile_summary": profile_summary,
        }

    async def _load_profile_and_scores(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        redis_client=None,
    ) -> tuple[UserProfile | None, dict]:
        """Load user profile and scores, checking cache first."""
        profile = None
        scores = {}

        # Try Redis cache first
        if redis_client:
            try:
                cached = await redis_client.get(f"profile:{user_id}")
                if cached:
                    cached_data = json.loads(cached)
                    profile = await self._profile_from_cache(cached_data, user_id, db)
                    scores = cached_data.get("scores", {})
                    if profile:
                        return profile, scores
            except Exception:
                logger.debug("Cache miss for user %s", user_id)

        # Load from database
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            # Load latest scores
            scores_stmt = (
                select(FitScore)
                .where(FitScore.user_id == user_id)
                .order_by(FitScore.scored_at.desc())
            )
            scores_result = await db.execute(scores_stmt)
            all_scores = scores_result.scalars().all()

            for score in all_scores:
                if score.dimension not in scores:
                    scores[score.dimension] = score

            # Cache the profile
            if redis_client:
                try:
                    cache_data = {
                        "temperament": profile.temperament,
                        "communication_style": profile.communication_style,
                        "sentiment_trend": profile.sentiment_trend,
                        "current_arc": profile.current_arc,
                        "primary_language": profile.primary_language,
                        "topic_interests": profile.topic_interests,
                        "scores": {
                            dim: {"score": s.score, "reasoning": s.reasoning}
                            for dim, s in scores.items()
                        },
                    }
                    await redis_client.setex(
                        f"profile:{user_id}",
                        settings.profile_cache_ttl,
                        json.dumps(cache_data, default=str),
                    )
                except Exception:
                    logger.debug("Failed to cache profile for user %s", user_id)

        return profile, scores

    async def _profile_from_cache(
        self, cached: dict, user_id: uuid.UUID, db: AsyncSession
    ) -> UserProfile | None:
        """Reconstruct a UserProfile from cached data for prompt building."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_conversation_history(
        self, conversation_id: uuid.UUID, db: AsyncSession
    ) -> list[dict]:
        """Load existing conversation messages."""
        stmt = select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv and conv.messages:
            # Return message history in Claude API format
            return [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in conv.messages
                if m.get("role") in ("user", "assistant")
            ]
        return []

    async def _save_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        messages: list[dict],
        assistant_response: str,
        db: AsyncSession,
    ):
        """Save conversation with the new exchange."""
        full_messages = messages + [
            {"role": "assistant", "content": assistant_response}
        ]

        stmt = select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv:
            conv.messages = full_messages
            conv.total_turns = len([m for m in full_messages if m["role"] == "user"])
        else:
            conv = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=full_messages,
                total_turns=len([m for m in full_messages if m["role"] == "user"]),
                processed=False,
            )
            db.add(conv)

        await db.flush()

    def _build_profile_summary(
        self, profile: UserProfile | None, scores: dict
    ) -> dict:
        """Build a concise profile summary for the API response."""
        if not profile:
            return {"status": "no_profile"}

        temp = profile.temperament or {}
        style = profile.communication_style or {}
        summary_parts = []
        if style.get("summary"):
            summary_parts.append(style["summary"])

        escalation = scores.get("escalation_risk")
        escalation_val = (
            escalation.score
            if hasattr(escalation, "score")
            else (escalation.get("score", None) if isinstance(escalation, dict) else None)
        ) if escalation else None

        return {
            "temperament": temp.get("label", "unknown"),
            "style": style.get("summary", "unknown"),
            "escalation_risk": escalation_val,
            "current_arc": profile.current_arc,
        }

    async def extract_and_update(
        self, conversation_id: uuid.UUID, db: AsyncSession
    ):
        """Async post-conversation: extract signals and update profile."""
        stmt = select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if not conv or not conv.messages:
            return

        try:
            signals = await self.extractor.extract_signals(
                conv.messages, conversation_id
            )

            signal_types = [
                "temperament",
                "communication_style",
                "sentiment",
                "life_stage",
                "topics",
                "cooperation",
            ]

            for sig_type in signal_types:
                if sig_type in signals:
                    signal = BehavioralSignal(
                        user_id=conv.user_id,
                        conversation_id=conversation_id,
                        signal_type=sig_type,
                        signal_value=signals[sig_type]
                        if isinstance(signals[sig_type], dict)
                        else {"topics": signals[sig_type]},
                        confidence=0.7,
                    )
                    db.add(signal)

            conv.processed = True
            await db.flush()

        except Exception:
            logger.exception(
                "Failed to extract signals from conversation %s", conversation_id
            )
