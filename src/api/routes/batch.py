import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import BatchIngestRequest, BatchStatusResponse
from src.database import get_db
from src.profile_engine.aggregator import ProfileAggregator
from src.profile_engine.batch_processor import BatchProcessor
from src.scoring.calculator import ScoreCalculator

router = APIRouter(prefix="/api/batch", tags=["batch"])

# Global processor instance for status tracking
_processor = BatchProcessor()


@router.post("/ingest", response_model=BatchStatusResponse)
async def trigger_ingest(
    request: BatchIngestRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger ingestion and processing of the JSONL dataset."""
    if _processor.progress.get("status") not in ("idle", "complete", "ingestion_complete", "extraction_complete"):
        return BatchStatusResponse(**_processor.progress)

    background_tasks.add_task(
        _run_pipeline, request.dataset_path, request.limit
    )

    return BatchStatusResponse(
        total=0,
        processed=0,
        failed=0,
        status="starting",
    )


async def _run_pipeline(dataset_path: str | None, limit: int | None):
    """Run the full batch processing pipeline."""
    try:
        await _processor.run_full_pipeline(dataset_path=dataset_path, limit=limit)

        # Also compute scores for all users
        from src.database import async_session

        calculator = ScoreCalculator()
        async with async_session() as db:
            from sqlalchemy import select
            from src.models import UserProfile

            result = await db.execute(select(UserProfile.user_id))
            user_ids = [row[0] for row in result.all()]

            for uid in user_ids:
                try:
                    await calculator.compute_all_scores(uid, db)
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "Failed to compute scores for %s", uid
                    )

            await db.commit()

    except Exception:
        import logging
        logging.getLogger(__name__).exception("Pipeline failed")


@router.get("/status", response_model=BatchStatusResponse)
async def get_status():
    """Check batch processing progress."""
    return BatchStatusResponse(**_processor.progress)


@router.post("/recompute/{user_id}", response_model=BatchStatusResponse)
async def recompute_profile(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Recompute a user's profile from all signals."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    background_tasks.add_task(_recompute_user, uid)

    return BatchStatusResponse(status="recomputing", total=1, processed=0, failed=0)


async def _recompute_user(user_id: uuid.UUID):
    """Recompute profile, scores, and arc for a user."""
    from src.database import async_session
    from src.evolution.arc_detector import ArcDetector
    from src.evolution.snapshot import SnapshotManager

    try:
        aggregator = ProfileAggregator()
        calculator = ScoreCalculator()
        arc_detector = ArcDetector()
        snapshot_manager = SnapshotManager()

        async with async_session() as db:
            # Re-aggregate profile
            await aggregator.aggregate(user_id, db)

            # Recompute scores
            await calculator.compute_all_scores(user_id, db)

            # Detect arc
            await arc_detector.detect_arc(user_id, db)

            # Create snapshot
            if await snapshot_manager.should_snapshot(user_id, db):
                await snapshot_manager.create_snapshot(user_id, db)

            await db.commit()
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Recompute failed for %s", user_id
        )
