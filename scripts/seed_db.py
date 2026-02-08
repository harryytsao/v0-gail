"""Seed the database with sample data for development."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.database import async_session, init_db
from src.models import BehavioralSignal, Conversation, FitScore, UserProfile


SAMPLE_USERS = [
    {
        "user_id": uuid.UUID("55798ace-d5ae-4797-a94f-3bc2f705d8c8"),
        "temperament": {"score": 7, "label": "patient", "volatility": "low", "summary": "Patient user"},
        "communication_style": {
            "formality": 0.4,
            "verbosity": 0.3,
            "technicality": 0.2,
            "structured": 0.4,
            "summary": "casual, concise, non-technical",
        },
        "sentiment_trend": {"direction": "stable", "recent_avg": 0.2, "summary": "Neutral"},
        "life_stage": {"stage": "consumer", "confidence": 0.7, "domain_expertise": []},
        "topic_interests": {"primary": ["identity protection", "credit"], "secondary": ["finance"]},
        "primary_language": "English",
        "current_arc": "stable",
    },
    {
        "user_id": uuid.UUID("f2420c66-0000-0000-0000-000000000000"),
        "temperament": {"score": 8, "label": "agreeable", "volatility": "low", "summary": "Engaged researcher"},
        "communication_style": {
            "formality": 0.8,
            "verbosity": 0.8,
            "technicality": 0.9,
            "structured": 0.9,
            "summary": "formal, verbose, technical, structured",
        },
        "sentiment_trend": {"direction": "stable", "recent_avg": 0.5, "summary": "Positive"},
        "life_stage": {"stage": "professional", "confidence": 0.9, "domain_expertise": ["compliance", "sanctions"]},
        "topic_interests": {"primary": ["sanctions", "compliance", "legal"], "secondary": ["research"]},
        "primary_language": "English",
        "current_arc": "growth",
    },
    {
        "user_id": uuid.UUID("11111111-2222-3333-4444-555555555555"),
        "temperament": {"score": 3, "label": "impatient", "volatility": "high", "summary": "Frustrated user"},
        "communication_style": {
            "formality": 0.2,
            "verbosity": 0.2,
            "technicality": 0.5,
            "structured": 0.3,
            "summary": "casual, terse",
        },
        "sentiment_trend": {"direction": "declining", "recent_avg": -0.3, "frustration_rate": 0.4, "summary": "Declining"},
        "life_stage": {"stage": "professional", "confidence": 0.6, "domain_expertise": ["tech"]},
        "topic_interests": {"primary": ["technology", "debugging"], "secondary": ["automation"]},
        "primary_language": "English",
        "current_arc": "cooling",
    },
]


async def seed():
    await init_db()
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        for user_data in SAMPLE_USERS:
            uid = user_data["user_id"]

            # Check if user already exists
            existing = await db.execute(
                select(UserProfile).where(UserProfile.user_id == uid)
            )
            if existing.scalar_one_or_none():
                print(f"User {uid} already exists, skipping")
                continue

            # Create profile
            profile = UserProfile(
                user_id=uid,
                temperament=user_data["temperament"],
                communication_style=user_data["communication_style"],
                sentiment_trend=user_data["sentiment_trend"],
                life_stage=user_data["life_stage"],
                topic_interests=user_data["topic_interests"],
                primary_language=user_data["primary_language"],
                current_arc=user_data["current_arc"],
            )
            db.add(profile)

            # Create sample signals
            for i in range(5):
                signal_date = now - timedelta(days=i * 7)
                db.add(
                    BehavioralSignal(
                        user_id=uid,
                        conversation_id=uuid.uuid4(),
                        signal_type="temperament",
                        signal_value=user_data["temperament"],
                        confidence=0.8,
                        extracted_at=signal_date,
                    )
                )
                db.add(
                    BehavioralSignal(
                        user_id=uid,
                        conversation_id=uuid.uuid4(),
                        signal_type="communication_style",
                        signal_value=user_data["communication_style"],
                        confidence=0.8,
                        extracted_at=signal_date,
                    )
                )
                db.add(
                    BehavioralSignal(
                        user_id=uid,
                        conversation_id=uuid.uuid4(),
                        signal_type="sentiment",
                        signal_value={
                            "overall": user_data["sentiment_trend"]["recent_avg"],
                            "arc": user_data["sentiment_trend"]["direction"],
                            "frustration_detected": user_data["sentiment_trend"].get("frustration_rate", 0) > 0.3,
                        },
                        confidence=0.7,
                        extracted_at=signal_date,
                    )
                )

            # Create sample scores
            for dim, score_val in [
                ("responsiveness", 60.0),
                ("escalation_risk", 30.0 if user_data["temperament"]["score"] > 5 else 70.0),
                ("engagement_quality", 65.0),
                ("cooperation_level", user_data["temperament"]["score"] * 10.0),
                ("expertise_level", user_data["communication_style"]["technicality"] * 100),
            ]:
                db.add(
                    FitScore(
                        user_id=uid,
                        dimension=dim,
                        score=score_val,
                        reasoning=f"Seeded score for {dim}",
                        component_signals={"seeded": True},
                    )
                )

            print(f"Seeded user {uid}")

        await db.commit()
        print("Database seeded successfully!")


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
