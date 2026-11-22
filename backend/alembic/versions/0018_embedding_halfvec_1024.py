"""Store job and resume embeddings as halfvec(1024).

Qwen3-Embedding-4B is Matryoshka-trained; its own guidance recommends truncating
to 1024 dimensions for search. The embedding service already truncates to
``EMBEDDING_DIMENSIONS``, so existing vectors can be shrunk without re-embedding:
keep the first 1024 dimensions and cast them to half precision. That is 2,056
bytes per vector instead of 10,248 -- a 5x reduction -- and the HNSW index
shrinks with it.

Expand/contract:

1. drop the old HNSW indexes,
2. add ``halfvec(1024)`` shadow columns,
3. backfill them in bounded, committed batches,
4. swap the columns in a short transaction,
5. rebuild the HNSW indexes with ``ef_construction=64``.

Pause the pipeline for the duration. It would otherwise write 2560-dimension
vectors into the old column while the swap is in flight. The public listing does
not read the embedding column, so backend reads stay up; only the (currently
unused) matching endpoint is affected during the swap.

Revision ID: 0018_embedding_halfvec_1024
Revises: 0017_jobs_read_indexes
Create Date: 2026-10-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import HALFVEC, Vector

revision: str = "0018_embedding_halfvec_1024"
down_revision: str | None = "0017_jobs_read_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DIMENSIONS = 1024
_BACKFILL_BATCH = 5_000


def _backfill(conn, table: str, source: str, target: str) -> None:
    """Copy the first 1024 dimensions into the shadow column in batches.

    Each batch runs outside the migration transaction (call this from an
    ``autocommit_block``) so the 700k-row backfill does not hold one huge
    transaction and its WAL open.
    """
    last_id = None
    while True:
        params: dict[str, object] = {"batch": _BACKFILL_BATCH}
        cursor = ""
        if last_id is not None:
            cursor = "AND id > :last_id"
            params["last_id"] = last_id

        rows = conn.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET {target} = subvector({source}, 1, {_DIMENSIONS})::halfvec({_DIMENSIONS}) "
                f"WHERE id IN ("
                f"  SELECT id FROM {table} "
                f"  WHERE {source} IS NOT NULL AND {target} IS NULL {cursor} "
                f"  ORDER BY id LIMIT :batch"
                f") RETURNING id"
            ),
            params,
        ).fetchall()
        if not rows:
            return
        last_id = max(row[0] for row in rows)


def upgrade() -> None:
    ctx = op.get_context()

    # Drop the old indexes first so the subsequent column swap has no
    # index dependency and the new build is the only graph maintained.
    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_resumes_embedding_hnsw")

    op.add_column(
        "jobs",
        sa.Column("description_embedding_1024", HALFVEC(_DIMENSIONS), nullable=True),
    )
    op.add_column(
        "user_resumes",
        sa.Column("resume_embedding_1024", HALFVEC(_DIMENSIONS), nullable=True),
    )

    with ctx.autocommit_block():
        conn = op.get_bind()
        _backfill(conn, "jobs", "description_embedding", "description_embedding_1024")
        _backfill(conn, "user_resumes", "resume_embedding", "resume_embedding_1024")

    op.drop_column("jobs", "description_embedding")
    op.alter_column(
        "jobs",
        "description_embedding_1024",
        new_column_name="description_embedding",
    )
    op.drop_column("user_resumes", "resume_embedding")
    op.alter_column(
        "user_resumes",
        "resume_embedding_1024",
        new_column_name="resume_embedding",
    )

    with ctx.autocommit_block():
        # Docker's default 64 MB /dev/shm is too small for pgvector's
        # parallel HNSW build; it aborts with DiskFull while requesting a
        # ~131 MB dynamic shared memory segment. Build single-threaded.
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute("SET maintenance_work_mem = '512MB'")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_embedding_hnsw "
            "ON jobs USING hnsw (description_embedding halfvec_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resumes_embedding_hnsw "
            "ON user_resumes USING hnsw (resume_embedding halfvec_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )
        # DROP COLUMN dropped this partial index with the old column; the embed
        # stage's candidate query still relies on it.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_needs_embedding "
            "ON jobs (id) WHERE is_active AND description_embedding IS NULL "
            "AND embedding_skip_reason IS NULL"
        )


def downgrade() -> None:
    """Restore 2560-dimension vectors by padding the dropped tail with zeros.

    The original tail dimensions cannot be recovered. This keeps the schema
    downgradable for test resets and rollbacks; matching quality requires a
    re-embed after a downgrade.
    """
    ctx = op.get_context()

    with ctx.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_resumes_embedding_hnsw")

    op.add_column(
        "jobs",
        sa.Column("description_embedding_2560", Vector(2560), nullable=True),
    )
    op.add_column(
        "user_resumes",
        sa.Column("resume_embedding_2560", Vector(2560), nullable=True),
    )

    with ctx.autocommit_block():
        conn = op.get_bind()
        conn.execute(
            sa.text(
                "UPDATE jobs SET description_embedding_2560 = ("
                "description_embedding::real[] || array_fill(0.0::real, ARRAY[1536])"
                ")::vector(2560) WHERE description_embedding IS NOT NULL"
            )
        )
        conn.execute(
            sa.text(
                "UPDATE user_resumes SET resume_embedding_2560 = ("
                "resume_embedding::real[] || array_fill(0.0::real, ARRAY[1536])"
                ")::vector(2560) WHERE resume_embedding IS NOT NULL"
            )
        )

    op.drop_column("jobs", "description_embedding")
    op.alter_column(
        "jobs",
        "description_embedding_2560",
        new_column_name="description_embedding",
    )
    op.drop_column("user_resumes", "resume_embedding")
    op.alter_column(
        "user_resumes",
        "resume_embedding_2560",
        new_column_name="resume_embedding",
    )

    with ctx.autocommit_block():
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute("SET maintenance_work_mem = '512MB'")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_embedding_hnsw "
            "ON jobs USING hnsw "
            "((description_embedding::halfvec(2560)) halfvec_cosine_ops) "
            "WITH (m = 16, ef_construction = 200)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resumes_embedding_hnsw "
            "ON user_resumes USING hnsw "
            "((resume_embedding::halfvec(2560)) halfvec_cosine_ops) "
            "WITH (m = 16, ef_construction = 200)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_needs_embedding "
            "ON jobs (id) WHERE is_active AND description_embedding IS NULL "
            "AND embedding_skip_reason IS NULL"
        )
