import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base

# Use timezone-aware timestamp type for all datetime columns
TZDateTime = DateTime(timezone=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    temperament: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    communication_style: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sentiment_trend: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    life_stage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    topic_interests: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    interaction_stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    primary_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_arc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BehavioralSignal(Base):
    __tablename__ = "behavioral_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    signal_type: Mapped[str] = mapped_column(String(50))
    signal_value: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    extracted_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    source_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FitScore(Base):
    __tablename__ = "fit_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    dimension: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    component_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    arc_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    messages: Mapped[dict] = mapped_column(JSONB)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
