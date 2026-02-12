#!/usr/bin/env python3
"""Embed all job descriptions using the configured embedding provider."""

from __future__ import annotations

import asyncio
import re
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.db import SessionLocal
from app.models import Job
from app.services.embedding_service import EmbeddingService


def clean_text(text: str) -> str:
    """Clean and truncate text for embedding."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove HTML entities
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    # Truncate to ~4000 chars (~2000 tokens, well under 8k limit)
    return text[:4000].strip()


async def embed_all_jobs(batch_size: int = 50) -> None:
    db = SessionLocal()
    embedder = EmbeddingService()

    # Get jobs without embeddings
    jobs = db.query(Job).filter(Job.description_embedding == None).all()
    total = len(jobs)

    print(f"Found {total} jobs without embeddings")

    success = 0
    errors = 0

    for i, job in enumerate(jobs):
        try:
            text = clean_text(job.description_text)
            if not text or len(text) < 50:
                print(f"  [{i + 1}/{total}] Skipping {job.id} - text too short")
                continue

            embedding = await embedder.embed(text)
            job.description_embedding = embedding
            success += 1

            # Commit every batch_size jobs
            if (i + 1) % batch_size == 0:
                db.commit()
                print(
                    f"  [{i + 1}/{total}] Committed batch... ({success} success, {errors} errors)"
                )

            if (i + 1) % 10 == 0:
                print(f"  [{i + 1}/{total}] {job.company} - {job.title[:40]}...")

        except Exception as e:
            errors += 1
            # Print full error for first few, then every 100 to avoid spam
            if errors <= 3 or errors % 100 == 1:
                print(f"  [{i + 1}/{total}] Error (#{errors}): {e}")
            continue

    # Final commit
    db.commit()
    db.close()

    print(f"\nDone! Embedded {success} jobs, {errors} errors.")


if __name__ == "__main__":
    print("Starting job embedding...")
    print("Using Ollama with nomic-embed-text (768 dimensions)")
    print("=" * 50)

    start = time.time()
    asyncio.run(embed_all_jobs())
    elapsed = time.time() - start

    print(f"\nCompleted in {elapsed:.1f} seconds ({elapsed / 60:.1f} minutes)")
