from __future__ import annotations

import argparse


def build_parser(config) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run job ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                      # Run full pipeline once
  python run_pipeline.py -c                   # Run continuously (every hour by default)
  python run_pipeline.py -c --interval 3600   # Run continuously every hour
  python run_pipeline.py --step ingest        # Only fetch new jobs
  python run_pipeline.py --step ingest --delete-inactive  # Fetch + delete inactive
  python run_pipeline.py --step sync_inactive # Mark all jobs inactive
  python run_pipeline.py --step delete_inactive # Delete inactive jobs
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py --dry-run            # Preview without changes
  python run_pipeline.py --resume             # Resume failed run
  python run_pipeline.py --check              # Health checks only
  python run_pipeline.py --step cleanup --all # Re-process ALL locations
  python run_pipeline.py --step cleanup --test # Test mode: CSV output only
        """,
    )
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuously")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=None,
        help=f"Interval in seconds (default: {config.pipeline.continuous_interval})",
    )
    parser.add_argument(
        "--step",
        choices=[
            "discover",
            "sync_inactive",
            "ingest",
            "delete_inactive",
            "cleanup",
            "classify",
            "embed",
        ],
        help="Run only a specific step",
    )
    parser.add_argument(
        "--delete-inactive",
        action="store_true",
        help="With --step ingest, also delete inactive jobs after ingestion",
    )
    parser.add_argument("--skip-discover", action="store_true", help="Skip company discovery")
    parser.add_argument(
        "--all",
        action="store_true",
        help="With --step cleanup, re-process ALL jobs",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--check", action="store_true", help="Run health checks only")
    parser.add_argument("--skip-check", action="store_true", help="Skip health checks")
    parser.add_argument("--resume", action="store_true", help="Resume from last failed run")
    parser.add_argument("--fresh", action="store_true", help="Start fresh (clear incomplete runs)")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode for cleanup: write results to CSV without DB changes",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of jobs to process (for --test mode)")
    return parser
