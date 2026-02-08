"""CLI script to run batch processing of conversation data."""

import argparse
import asyncio
import logging

from src.profile_engine.batch_processor import BatchProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run(args):
    processor = BatchProcessor()

    if args.step == "all":
        result = await processor.run_full_pipeline(
            dataset_path=args.dataset, limit=args.limit
        )
    elif args.step == "ingest":
        result = await processor.ingest_jsonl(args.dataset)
    elif args.step == "extract":
        result = await processor.process_conversations(limit=args.limit)
    elif args.step == "aggregate":
        result = await processor.aggregate_profiles()
    else:
        logger.error("Unknown step: %s", args.step)
        return

    logger.info("Result: %s", result)


def main():
    parser = argparse.ArgumentParser(description="Gail batch processing")
    parser.add_argument(
        "--step",
        choices=["all", "ingest", "extract", "aggregate"],
        default="all",
        help="Which processing step to run",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to JSONL dataset (default: from config)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of conversations to process",
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
