"""Regression tests for embedding batch selection."""

from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from pipeline.text import clean_text_for_embedding
from pipeline.embeddings import batch_processor
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



@pytest.mark.asyncio
async def test_process_batch_marks_too_short_jobs_as_embedding_skipped(monkeypatch):
    updates = []
    commits = 0

    class _FakeUpdate:
        def __init__(self, model):
            self.model = model
            self.job_id = None
            self.update_values = None

        def where(self, predicate):
            self.job_id = predicate
            return self

        def values(self, **values):
            self.update_values = values
            return self

    class _FakeColumn:
        def __eq__(self, other):
            return other

    class _FakeJobModel:
        id = _FakeColumn()

    class _FakeDb:
        async def execute(self, stmt):
            updates.append(stmt)

        async def commit(self):
            nonlocal commits
            commits += 1

    monkeypatch.setattr(batch_processor, "update", lambda model: _FakeUpdate(model))
    monkeypatch.setattr(batch_processor, "Job", _FakeJobModel)

    job = SimpleNamespace(
        id="job-1",
        description_text="```\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n```",
        company="Acme",
        title="Tiny",
        apply_url="https://example.com/job",
    )

    success, errors, skipped, failed = await batch_processor._process_batch(
        _FakeDb(),
        [job],
        embedder=SimpleNamespace(),
        batch_num=1,
    )

    assert (success, errors, skipped, failed) == (0, 0, 1, [])
    assert commits == 1
    assert len(updates) == 1
    assert updates[0].job_id == "job-1"
    assert updates[0].update_values["embedding_skip_reason"] == "too_short"
    assert updates[0].update_values["embedding_skipped_at"] is not None
