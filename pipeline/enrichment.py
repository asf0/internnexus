from __future__ import annotations

import asyncio
import logging

from backend.app.services.embedding_service import EmbeddingService
from pipeline.schemas import JobSchema


logger = logging.getLogger(__name__)
_embedder: EmbeddingService | None = None


def _get_embedder() -> EmbeddingService | None:
    """Get or create the embedding service (lazy initialization)."""
    global _embedder
    if _embedder is None:
        try:
            _embedder = EmbeddingService()
        except RuntimeError:
            return None
    return _embedder


async def enrich_jobs(
    jobs: list[JobSchema],
    category_context: dict | None = None,
    skip_embedding: bool = False,
) -> list[JobSchema]:
    """Pass through jobs with optional embedding generation.

    Currently disabled: location normalization, category detection,
    job type detection, work mode detection - to test clean ATS data.
    """
    if not jobs:
        return []

    if not skip_embedding:
        embedder = _get_embedder()
        if embedder:
            jobs_to_embed = [j for j in jobs if j.description_text]
            texts = [j.description_text for j in jobs_to_embed]
            try:
                embeddings = await embedder.embed_many(texts, batch_size=10)
                for job, embedding in zip(jobs_to_embed, embeddings):
                    job.description_embedding = embedding
            except Exception as e:
                logger.warning(f"Failed to embed batch: {e}")

    return jobs
