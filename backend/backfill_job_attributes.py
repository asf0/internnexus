#!/usr/bin/env python3
"""Backfill job_type and work_mode for existing jobs."""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import SessionLocal
from app.models import Job, JobType, WorkMode


def detect_job_type(title: str, description: str) -> JobType | None:
    title_lower = title.lower()
    desc_lower = description.lower() if description else ""

    if "intern" in title_lower:
        return JobType.internship
    if re.search(r"part[\s-]?time", title_lower):
        return JobType.part_time
    if re.search(r"part[\s-]?time", desc_lower):
        return JobType.part_time
    return None


def detect_work_mode(title: str, location: str, description: str) -> WorkMode | None:
    title_lower = title.lower()
    location_lower = location.lower() if location else ""
    desc_lower = description.lower() if description else ""

    combined = f"{title_lower} {location_lower} {desc_lower}"

    if "remote" in combined:
        return WorkMode.remote
    if "hybrid" in combined:
        return WorkMode.hybrid
    if any(p in combined for p in ["on-site", "onsite", "in-office", "in office"]):
        return WorkMode.on_site
    return None


def backfill_attributes(batch_size: int = 100) -> None:
    db = SessionLocal()

    jobs = db.query(Job).filter((Job.job_type == None) | (Job.work_mode == None)).all()
    total = len(jobs)

    print(f"Found {total} jobs to backfill")

    updated_job_type = 0
    updated_work_mode = 0

    for i, job in enumerate(jobs):
        if job.job_type is None:
            job_type = detect_job_type(job.title, job.description_text or "")
            if job_type:
                job.job_type = job_type
                updated_job_type += 1

        if job.work_mode is None:
            work_mode = detect_work_mode(job.title, job.location, job.description_text or "")
            if work_mode:
                job.work_mode = work_mode
                updated_work_mode += 1

        if (i + 1) % batch_size == 0:
            db.commit()
            print(f"  [{i + 1}/{total}] Committed batch...")

    db.commit()
    db.close()

    print(f"\nDone!")
    print(f"  job_type updated: {updated_job_type}")
    print(f"  work_mode updated: {updated_work_mode}")


if __name__ == "__main__":
    print("Starting job attributes backfill...")
    print("=" * 50)

    start = time.time()
    backfill_attributes()
    elapsed = time.time() - start

    print(f"\nCompleted in {elapsed:.1f} seconds")
