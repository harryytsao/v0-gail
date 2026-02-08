"""Fast ingestion of conversations_merged.json into the database.

This script ONLY populates the conversations and user_profiles tables.
It does NOT call the Claude API for trait extraction.
Run extraction separately with: python scripts/run_batch.py --step extract --limit N
"""

import asyncio
import json
import logging
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from time import time

from sqlalchemy import select, text

from src.database import async_session, engine, init_db
from src.models import Conversation, UserProfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATASET_PATH = Path("/Users/harry/Desktop/code/v0-gail/conversations_merged.json")
BATCH_SIZE = 500  # conversations per DB commit


async def ingest():
    await init_db()

    logger.info("Reading dataset from %s ...", DATASET_PATH)
    t0 = time()

    # Phase 1: Read and group records by conversation
    conversations: dict[str, dict] = {}
    line_count = 0

    with open(DATASET_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            conv_id = record.get("conversation_id", "")
            if conv_id not in conversations:
                conversations[conv_id] = {
                    "user_id": record.get("user_id"),
                    "model": record.get("model"),
                    "language": record.get("language"),
                    "messages": [],
                }

            conversations[conv_id]["messages"].append({
                "role": record.get("role", ""),
                "content": record.get("content", ""),
                "message_index": record.get("message_index", 0),
                "conversation_turn": record.get("conversation_turn", 0),
                "redacted": record.get("redacted", False),
            })

            line_count += 1
            if line_count % 500_000 == 0:
                logger.info("  Read %d lines, %d conversations so far ...", line_count, len(conversations))

    t_read = time() - t0
    logger.info(
        "Read complete: %d lines → %d conversations in %.1fs",
        line_count, len(conversations), t_read,
    )

    # Collect unique user IDs
    user_ids = set()
    for conv_data in conversations.values():
        uid = conv_data["user_id"]
        if uid:
            user_ids.add(uid)

    logger.info("Found %d unique users", len(user_ids))

    # Phase 2: Insert user profiles
    t1 = time()
    user_batch = []
    for uid_str in user_ids:
        try:
            uid = uuid.UUID(uid_str)
        except (ValueError, TypeError):
            uid = uuid.uuid5(uuid.NAMESPACE_DNS, str(uid_str))
        user_batch.append(uid)

    # Batch insert users
    inserted_users = 0
    for i in range(0, len(user_batch), BATCH_SIZE):
        batch = user_batch[i:i + BATCH_SIZE]
        async with async_session() as db:
            # Check which users already exist
            existing = await db.execute(
                select(UserProfile.user_id).where(UserProfile.user_id.in_(batch))
            )
            existing_ids = {row[0] for row in existing.all()}

            for uid in batch:
                if uid not in existing_ids:
                    db.add(UserProfile(user_id=uid))
                    inserted_users += 1

            await db.commit()

        if (i + BATCH_SIZE) % 5000 == 0 or i + BATCH_SIZE >= len(user_batch):
            logger.info("  Users: %d / %d", min(i + BATCH_SIZE, len(user_batch)), len(user_batch))

    logger.info("Inserted %d user profiles in %.1fs", inserted_users, time() - t1)

    # Phase 3: Insert conversations
    t2 = time()
    conv_items = list(conversations.items())
    inserted_convs = 0
    skipped_convs = 0

    for i in range(0, len(conv_items), BATCH_SIZE):
        batch = conv_items[i:i + BATCH_SIZE]
        async with async_session() as db:
            for conv_id_str, conv_data in batch:
                try:
                    conv_uuid = uuid.UUID(conv_id_str)
                except ValueError:
                    conv_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, conv_id_str)

                uid_str = conv_data["user_id"]
                try:
                    user_uuid = uuid.UUID(uid_str)
                except (ValueError, TypeError):
                    user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(uid_str))

                # Sort messages by message_index
                sorted_msgs = sorted(
                    conv_data["messages"], key=lambda m: m.get("message_index", 0)
                )

                conv_record = Conversation(
                    conversation_id=conv_uuid,
                    user_id=user_uuid,
                    model=conv_data["model"],
                    language=conv_data["language"],
                    total_turns=max(
                        (m.get("conversation_turn", 0) for m in sorted_msgs),
                        default=0,
                    ),
                    messages=sorted_msgs,
                    processed=False,
                )
                db.add(conv_record)
                inserted_convs += 1

            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                # Likely duplicate key — insert one by one
                for conv_id_str, conv_data in batch:
                    async with async_session() as db2:
                        try:
                            conv_uuid = uuid.UUID(conv_id_str)
                        except ValueError:
                            conv_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, conv_id_str)

                        existing = await db2.execute(
                            select(Conversation).where(Conversation.conversation_id == conv_uuid)
                        )
                        if existing.scalar_one_or_none():
                            skipped_convs += 1
                            continue

                        uid_str = conv_data["user_id"]
                        try:
                            user_uuid = uuid.UUID(uid_str)
                        except (ValueError, TypeError):
                            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(uid_str))

                        sorted_msgs = sorted(
                            conv_data["messages"], key=lambda m: m.get("message_index", 0)
                        )
                        db2.add(Conversation(
                            conversation_id=conv_uuid,
                            user_id=user_uuid,
                            model=conv_data["model"],
                            language=conv_data["language"],
                            total_turns=max((m.get("conversation_turn", 0) for m in sorted_msgs), default=0),
                            messages=sorted_msgs,
                            processed=False,
                        ))
                        try:
                            await db2.commit()
                            inserted_convs += 1
                        except Exception:
                            await db2.rollback()
                            skipped_convs += 1

        if (i + BATCH_SIZE) % 2000 == 0 or i + BATCH_SIZE >= len(conv_items):
            logger.info(
                "  Conversations: %d / %d (skipped %d dupes)",
                min(i + BATCH_SIZE, len(conv_items)),
                len(conv_items),
                skipped_convs,
            )

    total_time = time() - t0
    logger.info(
        "Done! Inserted %d conversations (%d skipped) in %.1fs total",
        inserted_convs, skipped_convs, total_time,
    )

    # Print summary stats
    async with async_session() as db:
        user_count = await db.execute(text("SELECT COUNT(*) FROM user_profiles"))
        conv_count = await db.execute(text("SELECT COUNT(*) FROM conversations"))
        logger.info("DB totals: %d users, %d conversations",
                     user_count.scalar(), conv_count.scalar())

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
