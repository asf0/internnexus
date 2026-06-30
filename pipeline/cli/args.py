from __future__ import annotations

import argparse


def build_parser(config) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run job ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  internnexus-pipeline                      # Run full pipeline once
  internnexus-pipeline -c                   # Run continuously
  internnexus-pipeline -c --interval 3600   # Run continuously every hour
  internnexus-pipeline --step ingest        # Only fetch new jobs
  internnexus-pipeline --step ingest --delete-inactive  # Fetch + delete inactive
  internnexus-pipeline --step sync_inactive # Deprecated compatibility no-op
  internnexus-pipeline --step embed         # Only generate embeddings
  internnexus-pipeline --dry-run            # Preview without changes
  internnexus-pipeline --resume             # Resume failed run
  internnexus-pipeline --check              # Health checks only
  internnexus-pipeline --step cleanup --all # Re-process ALL locations
  internnexus-pipeline --step cleanup --test # Test mode: CSV output only
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
