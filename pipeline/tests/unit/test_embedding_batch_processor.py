"""Regression tests for embedding batch selection."""

from sqlalchemy.dialects import postgresql

from pipeline.text import clean_text_for_embedding
from pipeline.embeddings.batch_processor import _embedding_candidate_text_sql


def test_clean_text_code_fence_only_body_is_too_short():
    raw_text = "```\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n```"

    assert len(clean_text_for_embedding(raw_text)) == 29


def test_embedding_candidate_sql_strips_code_fence_markers():
    compiled = str(
        _embedding_candidate_text_sql().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "```[a-zA-Z0-9_+-]*" in compiled
    assert "replace(" in compiled.lower()
