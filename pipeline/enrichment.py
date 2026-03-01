from __future__ import annotations

import logging

from pipeline.backend_bridge import EmbeddingService
from pipeline.classification import get_classifier
from pipeline.schemas import JobSchema


logger = logging.getLogger(__name__)
_embedder: EmbeddingService | None = None


def reset_embedder() -> None:
    """Reset the embedder singleton to free memory."""
    global _embedder
    if _embedder is not None:
        _embedder = None
        logger.debug("Embedder reset")


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
    category_context: dict | None = None,  # Deprecated: LLM classification replaces this
    skip_embedding: bool = False,
    skip_classification: bool = False,
) -> list[JobSchema]:
    """Enrich jobs with embeddings and AI-based category classification.

    Args:
        jobs: List of jobs to enrich
        category_context: Deprecated - no longer used, kept for backward compatibility
        skip_embedding: If True, skip embedding generation
        skip_classification: If True, skip category classification

    Returns:
        Enriched jobs list (same objects, modified in place)
    """
    if not jobs:
        return []

    # Classify jobs that don't have a category
    if not skip_classification:
        jobs_to_classify = [j for j in jobs if not j.job_category]
        if jobs_to_classify:
            try:
                classifier = get_classifier()
                inputs = [(j.title, j.description_text or "") for j in jobs_to_classify]
                categories = await classifier.classify_batch(inputs)
                for job, category in zip(jobs_to_classify, categories):
                    if category:
                        job.job_category = category
                classified_count = sum(1 for c in categories if c)
                logger.info(f"Classified {classified_count}/{len(jobs_to_classify)} jobs")
            except Exception as e:
                logger.warning(f"Failed to classify jobs: {e}")

    # Generate embeddings for jobs with descriptions
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
