import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# --- Profile Schemas ---


class TemperamentSchema(BaseModel):
    score: float = 5.0
    label: str = "neutral"
    volatility: str = "low"
    summary: str = ""


class CommunicationStyleSchema(BaseModel):
    formality: float = 0.5
    verbosity: float = 0.5
    technicality: float = 0.5
    structured: float = 0.5
    summary: str = ""


class SentimentTrendSchema(BaseModel):
    direction: str = "stable"
    recent_avg: float = 0.0
    frustration_rate: float = 0.0
    summary: str = ""


class LifeStageSchema(BaseModel):
    stage: str = "unknown"
    confidence: float = 0.0
    domain_expertise: list[str] = []


class TopicInterestsSchema(BaseModel):
    primary: list[str] = []
    secondary: list[str] = []


class ProfileResponse(BaseModel):
    user_id: str
    temperament: TemperamentSchema | None = None
    communication_style: CommunicationStyleSchema | None = None
    sentiment_trend: SentimentTrendSchema | None = None
    life_stage: LifeStageSchema | None = None
    topic_interests: TopicInterestsSchema | None = None
    interaction_stats: dict | None = None
    primary_language: str | None = None
    current_arc: str | None = None
    profile_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    scores: dict | None = None


class ProfileTimelineResponse(BaseModel):
    user_id: str
    timeline: list[dict]


# --- Score Schemas ---


class ScoreResponse(BaseModel):
    dimension: str
    score: float
    previous_score: float | None = None
    reasoning: str | None = None
    scored_at: datetime | None = None


class AllScoresResponse(BaseModel):
    user_id: str
    scores: list[ScoreResponse]


class ScoreHistoryResponse(BaseModel):
    user_id: str
    dimension: str
    history: list[ScoreResponse]


# --- Agent Schemas ---


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    adaptations_applied: list[str]
    profile_summary: dict


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    user_id: str
    messages: list[dict]
    total_turns: int | None = None


class AdaptationPreviewResponse(BaseModel):
    user_id: str
    system_prompt_preview: str
    adaptations: list[str]
    profile_summary: dict


# --- Batch Schemas ---


class BatchIngestRequest(BaseModel):
    dataset_path: str | None = None
    limit: int | None = None


class BatchStatusResponse(BaseModel):
    total: int = 0
    processed: int = 0
    failed: int = 0
    status: str = "idle"


class RecomputeRequest(BaseModel):
    user_id: str


# --- Users List ---


class UserListItem(BaseModel):
    user_id: str
    primary_language: str | None = None
    current_arc: str | None = None
    temperament_label: str | None = None
    temperament_score: float | None = None
    total_conversations: int | None = None
    updated_at: datetime | None = None


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class DashboardStatsResponse(BaseModel):
    total_users: int
    total_conversations: int
    profiled_users: int
    scored_users: int
    total_signals: int
