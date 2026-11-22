from __future__ import annotations

from app.prune_analytics import prune_mcp_invocations


class _FakeScalars:
    def __init__(self, rows: list[int]) -> None:
        self._rows = rows

    def all(self) -> list[int]:
        return self._rows


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeSession:
    """Minimal stand-in for a sync Session exercising the prune control flow."""

    def __init__(self, *, count: int = 0, batches: list[list[int]] | None = None) -> None:
        self._count = count
        self._batches = list(batches or [])
        self._last_rows: list[int] = []
        self.commits = 0
        self.rollbacks = 0
        self.deletes = 0

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def scalar(self, _stmt: object) -> int:
        return self._count

    def rollback(self) -> None:
        self.rollbacks += 1

    def scalars(self, _stmt: object) -> _FakeScalars:
        self._last_rows = self._batches.pop(0) if self._batches else []
        return _FakeScalars(self._last_rows)

    def execute(self, _stmt: object) -> _FakeResult:
        self.deletes += 1
        return _FakeResult(len(self._last_rows))

    def commit(self) -> None:
        self.commits += 1


def test_dry_run_counts_without_deleting() -> None:
    session = _FakeSession(count=5)
    result = prune_mcp_invocations(
        retention_days=90,
        apply=False,
        session_factory=lambda: session,
    )
    assert result == 5
    assert session.rollbacks == 1
    assert session.commits == 0
    assert session.deletes == 0


def test_apply_deletes_across_full_then_empty_batch() -> None:
    session = _FakeSession(batches=[[1, 2, 3], []])
    result = prune_mcp_invocations(
        retention_days=30,
        apply=True,
        batch_size=3,
        session_factory=lambda: session,
    )
    assert result == 3
    assert session.deletes == 1
    assert session.commits == 1


def test_apply_stops_on_partial_batch() -> None:
    session = _FakeSession(batches=[[1, 2]])
    result = prune_mcp_invocations(
        retention_days=30,
        apply=True,
        batch_size=3,
        session_factory=lambda: session,
    )
    assert result == 2
    assert session.deletes == 1
    assert session.commits == 1
