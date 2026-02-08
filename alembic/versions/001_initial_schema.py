"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("temperament", postgresql.JSONB(), nullable=True),
        sa.Column("communication_style", postgresql.JSONB(), nullable=True),
        sa.Column("sentiment_trend", postgresql.JSONB(), nullable=True),
        sa.Column("life_stage", postgresql.JSONB(), nullable=True),
        sa.Column("topic_interests", postgresql.JSONB(), nullable=True),
        sa.Column("interaction_stats", postgresql.JSONB(), nullable=True),
        sa.Column("primary_language", sa.String(50), nullable=True),
        sa.Column("current_arc", sa.String(100), nullable=True),
        sa.Column("profile_version", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "behavioral_signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("signal_value", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("source_turn", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_signals_user_time", "behavioral_signals", ["user_id", "extracted_at"])

    op.create_table(
        "fit_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("component_signals", postgresql.JSONB(), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scores_user_dim", "fit_scores", ["user_id", "dimension", "scored_at"])

    op.create_table(
        "profile_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("arc_label", sa.String(100), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_snapshots_user", "profile_snapshots", ["user_id", "snapshot_at"])

    op.create_table(
        "conversations",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("total_turns", sa.Integer(), nullable=True),
        sa.Column("messages", postgresql.JSONB(), nullable=False),
        sa.Column("processed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("conversation_id"),
    )
    op.create_index("idx_conversations_user", "conversations", ["user_id"])


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("profile_snapshots")
    op.drop_table("fit_scores")
    op.drop_table("behavioral_signals")
    op.drop_table("user_profiles")
