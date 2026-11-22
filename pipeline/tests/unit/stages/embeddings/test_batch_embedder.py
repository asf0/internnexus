"""Regression tests for embedding batch selection."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from internnexus_core.text import clean_text_for_embedding
from pipeline.stages.embeddings import batch_embedder
from pipeline.repositories.job_text_sql import embedding_candidate_text_sql


def test_clean_text_code_fence_only_body_is_too_short():
    raw_text = "```\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n```"

    assert len(clean_text_for_embedding(raw_text)) == 29


def test_embedding_candidate_sql_strips_code_fence_markers():
    compiled = str(
        embedding_candidate_text_sql().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "```[a-zA-Z0-9_+-]*" in compiled
    assert "replace(" in compiled.lower()


@pytest.mark.asyncio
async def test_process_batch_marks_too_short_jobs_as_embedding_skipped():
    """Too-short jobs get a skip marker via a single multi-row UPDATE.

    Asserts against the real compiled statement rather than a stubbed `update()`,
    so the test stays honest about the SQL actually sent.
    """
    updates = []
    commits = 0

    class _CaptureDb:
        async def execute(self, stmt):
            updates.append(stmt)

        async def commit(self):
            nonlocal commits
            commits += 1

    job_id = uuid4()
    job = SimpleNamespace(
        id=job_id,
        description_text="```\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n```",
        company="Acme",
        title="Tiny",
        apply_url="https://example.com/job",
    )

    success, errors, skipped, failed = await batch_embedder._process_batch(
        _CaptureDb(),
        [job],
        embedder=SimpleNamespace(),
        batch_num=1,
    )

    assert (success, errors, skipped, failed) == (0, 0, 1, [])
    assert commits == 1
    assert len(updates) == 1

    compiled = updates[0].compile(dialect=postgresql.dialect())
    sql = " ".join(str(compiled).split())
    assert "UPDATE jobs SET embedding_skip_reason=" in sql
    assert "FROM (VALUES" in sql
    assert "WHERE jobs.id = v.id" in sql

    params = compiled.params
    assert job_id in params.values()
    assert "too_short" in params.values()
    assert params["embedding_skipped_at"] is not None


@pytest.mark.asyncio
async def test_embedding_candidate_selection_is_limited_to_active_jobs():
    class _CaptureDb:
        async def execute(self, statement):
            self.statement = statement

            class _Result:
                class _Scalars:
                    def all(self):
                        return []

                def scalars(self):
                    return self._Scalars()

            return _Result()

    db = _CaptureDb()

    await batch_embedder._fetch_job_ids_batch(db, 10)
    sql = str(db.statement.compile(dialect=postgresql.dialect()))

    assert "jobs.is_active IS true" in sql
    assert "jobs.posted_at IS NULL" in sql
    assert "jobs.posted_at >=" in sql


@pytest.mark.asyncio
async def test_embedding_write_is_guarded_against_stale_or_inactive_jobs(monkeypatch):
    statements = []

    class _Db:
        async def execute(self, statement):
            statements.append(statement)
            return SimpleNamespace(rowcount=0)

        async def commit(self):
            return None

        def expunge_all(self):
            return None

    async def _embed_many(_texts, *, batch_size):
        return [[0.1, 0.2, 0.3]]

    monkeypatch.setattr(
        batch_embedder,
        "get_config",
        lambda: SimpleNamespace(embeddings=SimpleNamespace(api_batch_size=10)),
    )
    job = SimpleNamespace(
        id=uuid4(),
        description_text="A sufficiently detailed role description for safe embedding writes.",
    )

    success, errors, failed = await batch_embedder._embed_and_save(
        _Db(),
        [job],
        [job.description_text],
        embedder=SimpleNamespace(embed_many=_embed_many),
        batch_num=1,
        retry_attempt=0,
    )

    assert (success, errors, failed) == (0, 0, [])
    sql = str(statements[0].compile(dialect=postgresql.dialect()))
    assert "jobs.is_active IS true" in sql
    assert "jobs.description_embedding IS NULL" in sql
    assert "jobs.embedding_skip_reason IS NULL" in sql
    assert "jobs.embedding_input_hash" in sql
