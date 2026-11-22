from __future__ import annotations

import argparse


class PipelineArgumentParser(argparse.ArgumentParser):
    """Argument parser that rejects contradictory pipeline modes early."""

    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        self._validate(parsed)
        return parsed

    def _validate(self, args: argparse.Namespace) -> None:
        self._validate_modes(args)
        self._validate_step_options(args)
        self._validate_positive_values(args)

    def _validate_modes(self, args: argparse.Namespace) -> None:
        execution_flags = {
            "--step": args.step is not None,
            "--continuous": args.continuous,
            "--resume": args.resume,
            "--fresh": args.fresh,
            "--test": args.test,
            "--dry-run": args.dry_run,
            "--delete-inactive": args.delete_inactive,
        }
        if args.check:
            conflicts = [flag for flag, enabled in execution_flags.items() if enabled]
            if conflicts:
                self.error(f"--check is health-check-only and cannot be combined with {', '.join(conflicts)}")
        if args.resume and args.fresh:
            self.error("--resume and --fresh are mutually exclusive")
        if args.continuous and args.step:
            self.error("--continuous cannot be combined with --step")
        if args.continuous and args.fresh:
            self.error("--continuous cannot be combined with --fresh")
        if args.interval is not None and not args.continuous:
            self.error("--interval requires --continuous")

    def _validate_step_options(self, args: argparse.Namespace) -> None:
        if args.delete_inactive and args.step != "ingest":
            self.error("--delete-inactive requires --step ingest")
        if args.all and args.step != "cleanup":
            self.error("--all requires --step cleanup")
        if args.test and args.step != "cleanup":
            self.error("--test requires --step cleanup")

    def _validate_positive_values(self, args: argparse.Namespace) -> None:
        if args.interval is not None and args.interval <= 0:
            self.error("--interval must be greater than zero")
        if args.limit is not None and args.limit <= 0:
            self.error("--limit must be greater than zero")


def build_parser(config) -> argparse.ArgumentParser:
    parser = PipelineArgumentParser(
        description="Run job ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  internnexus-pipeline                      # Run full pipeline once
  internnexus-pipeline -c                   # Run continuously
  internnexus-pipeline -c --interval 3600   # Run continuously every hour
  internnexus-pipeline --step ingest        # Only fetch new jobs
  internnexus-pipeline --step ingest --delete-inactive  # Fetch + delete inactive
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
            "ingest",
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
