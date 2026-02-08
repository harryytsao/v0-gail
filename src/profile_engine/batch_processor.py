import asyncio
import json
import logging
import uuid
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import async_session
from src.models import BehavioralSignal, Conversation, UserProfile
from src.profile_engine.aggregator import ProfileAggregator
from src.profile_engine.extractor import TraitExtractor

logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self):
        self.extractor = TraitExtractor()
        self.aggregator = ProfileAggregator()
        self._progress = {"total": 0, "processed": 0, "failed": 0, "status": "idle"}

    @property
    def progress(self) -> dict:
        return self._progress.copy()

    async def ingest_jsonl(self, path: str | None = None) -> dict:
        """Read JSONL dataset and populate conversations table."""
        file_path = Path(path or settings.dataset_path)
        if not file_path.exists():
            return {"error": f"Dataset not found at {file_path}"}

        self._progress = {"total": 0, "processed": 0, "failed": 0, "status": "ingesting"}

        # Group records by conversation
        conversations: dict[str, dict] = defaultdict(
            lambda: {"messages": [], "user_id": None, "model": None, "language": None}
        )

        logger.info("Reading dataset from %s", file_path)
        line_count = 0

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self._progress["failed"] += 1
                    continue

                conv_id = record.get("conversation_id", "")
                conv = conversations[conv_id]
                conv["user_id"] = record.get("user_id")
                conv["model"] = record.get("model")
                conv["language"] = record.get("language")
                conv["messages"].append(
                    {
                        "role": record.get("role", ""),
                        "content": record.get("content", ""),
                        "message_index": record.get("message_index", 0),
                        "conversation_turn": record.get("conversation_turn", 0),
                        "redacted": record.get("redacted", False),
                    }
                )
                line_count += 1

        logger.info("Read %d records into %d conversations", line_count, len(conversations))
        self._progress["total"] = len(conversations)

        # Store conversations in batches
        batch_size = settings.batch_chunk_size
        conv_items = list(conversations.items())

        for i in range(0, len(conv_items), batch_size):
            batch = conv_items[i : i + batch_size]
            async with async_session() as db:
                for conv_id_str, conv_data in batch:
                    try:
                        conv_uuid = uuid.UUID(conv_id_str)
                    except ValueError:
                        conv_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, conv_id_str)

                    user_id_str = conv_data["user_id"]
                    try:
                        user_uuid = uuid.UUID(user_id_str)
                    except (ValueError, TypeError):
                        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id_str))

                    # Ensure user profile exists
                    existing = await db.execute(
                        select(UserProfile).where(UserProfile.user_id == user_uuid)
                    )
                    if existing.scalar_one_or_none() is None:
                        db.add(UserProfile(user_id=user_uuid))

                    # Sort messages by message_index
                    sorted_msgs = sorted(
                        conv_data["messages"], key=lambda m: m.get("message_index", 0)
                    )

                    # Check if conversation already exists
                    existing_conv = await db.execute(
                        select(Conversation).where(
                            Conversation.conversation_id == conv_uuid
                        )
                    )
                    if existing_conv.scalar_one_or_none() is None:
                        conv_record = Conversation(
                            conversation_id=conv_uuid,
                            user_id=user_uuid,
                            model=conv_data["model"],
                            language=conv_data["language"],
                            total_turns=max(
                                (m.get("conversation_turn", 0) for m in sorted_msgs), default=0
                            ),
                            messages=sorted_msgs,
                            processed=False,
                        )
                        db.add(conv_record)

                    self._progress["processed"] += 1

                await db.commit()

            logger.info(
                "Ingested batch %d-%d of %d",
                i,
                min(i + batch_size, len(conv_items)),
                len(conv_items),
            )

        self._progress["status"] = "ingestion_complete"
        return self._progress.copy()

    async def process_conversations(
        self, limit: int | None = None, user_id: uuid.UUID | None = None
    ) -> dict:
        """Extract behavioral signals from unprocessed conversations."""
        self._progress["status"] = "extracting"

        async with async_session() as db:
            stmt = select(Conversation).where(Conversation.processed == False)  # noqa: E712
            if user_id:
                stmt = stmt.where(Conversation.user_id == user_id)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            convos = result.scalars().all()

        self._progress["total"] = len(convos)
        self._progress["processed"] = 0

        semaphore = asyncio.Semaphore(settings.max_concurrent_extractions)

        async def process_one(conv: Conversation):
            async with semaphore:
                try:
                    signals = await self.extractor.extract_signals(
                        conv.messages, conv.conversation_id
                    )
                    await self._store_signals(conv, signals)
                    self._progress["processed"] += 1
                except Exception:
                    logger.exception(
                        "Failed to process conversation %s", conv.conversation_id
                    )
                    self._progress["failed"] += 1

        tasks = [process_one(conv) for conv in convos]
        await asyncio.gather(*tasks)

        self._progress["status"] = "extraction_complete"
        return self._progress.copy()

    async def _store_signals(self, conv: Conversation, signals: dict):
        """Store extracted signals and mark conversation as processed."""
        async with async_session() as db:
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
                        conversation_id=conv.conversation_id,
                        signal_type=sig_type,
                        signal_value=signals[sig_type]
                        if isinstance(signals[sig_type], dict)
                        else {"topics": signals[sig_type]},
                        confidence=0.7,  # default confidence from LLM extraction
                    )
                    db.add(signal)

            # Mark conversation as processed
            stmt = select(Conversation).where(
                Conversation.conversation_id == conv.conversation_id
            )
            result = await db.execute(stmt)
            conv_record = result.scalar_one_or_none()
            if conv_record:
                conv_record.processed = True

            await db.commit()

    async def aggregate_profiles(self, user_id: uuid.UUID | None = None) -> dict:
        """Aggregate signals into profiles for all users (or a specific user)."""
        self._progress["status"] = "aggregating"

        async with async_session() as db:
            if user_id:
                user_ids = [user_id]
            else:
                stmt = select(UserProfile.user_id)
                result = await db.execute(stmt)
                user_ids = [row[0] for row in result.all()]

        self._progress["total"] = len(user_ids)
        self._progress["processed"] = 0

        for uid in user_ids:
            try:
                async with async_session() as db:
                    await self.aggregator.aggregate(uid, db)
                    await db.commit()
                self._progress["processed"] += 1
            except Exception:
                logger.exception("Failed to aggregate profile for user %s", uid)
                self._progress["failed"] += 1

        self._progress["status"] = "complete"
        return self._progress.copy()

    async def run_full_pipeline(
        self, dataset_path: str | None = None, limit: int | None = None
    ) -> dict:
        """Run the full ingestion → extraction → aggregation pipeline."""
        logger.info("Starting full pipeline")

        # Step 1: Ingest
        ingest_result = await self.ingest_jsonl(dataset_path)
        if "error" in ingest_result:
            return ingest_result

        # Step 2: Extract signals
        await self.process_conversations(limit=limit)

        # Step 3: Aggregate profiles
        await self.aggregate_profiles()

        return self._progress.copy()
