from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.domain import JobSchema
from pipeline.domain.job_identity import fingerprint_for
from pipeline.domain.board_snapshot import build_board_snapshot
from pipeline.repositories import board_snapshots


def _job(url: str, title: str = "Software Engineer Intern") -> JobSchema:
    return JobSchema(
        source="greenhouse",
        title=title,
        company="Example",
        location="Remote",
        apply_url=url,
        description_text="A detailed internship description.",
    )


class _Result:
    def __init__(self, *, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self):
        return list(self._rows)


class _Session:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            return _Result(rows=[("changed",)])
        if len(self.statements) == 2:
            return _Result(rowcount=1)
        return _Result()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_unchanged_board_performs_no_writes_or_commit(monkeypatch) -> None:
    snapshot = build_board_snapshot([_job("https://example.com/jobs/1")])
    current = SimpleNamespace(
        board_hash=snapshot.board_hash,
        manifest=snapshot.manifest,
    )

    load_options = []

    async def _load(*_args, **kwargs):
        load_options.append(kwargs)
        return current

    monkeypatch.setattr(board_snapshots, "load_snapshot", _load)
    session = _Session()

    stats = await board_snapshots.reconcile_board(
        session,
        "greenhouse",
        "example",
        snapshot,
    )

    assert stats.snapshot_changed is False
    assert session.statements == []
    assert session.commits == 0
    assert session.rollbacks == 0
    assert load_options == [{}]


@pytest.mark.asyncio
async def test_first_miss_is_carried_forward_as_pending_not_deactivated(monkeypatch) -> None:
    removed = _job("https://example.com/jobs/removed")
    changed = _job("https://example.com/jobs/changed", title="New title")
    snapshot = build_board_snapshot([changed])
    removed_fingerprint = fingerprint_for(removed)
    current = SimpleNamespace(
        board_hash="old-hash",
        manifest={
            removed_fingerprint: "removed-hash",
            fingerprint_for(changed): "old-content-hash",
        },
    )

    async def _load(*_args, **_kwargs):
        return current

    monkeypatch.setattr(board_snapshots, "load_snapshot", _load)
    session = _Session()

    stats = await board_snapshots.reconcile_board(
        session,
        "greenhouse",
        "example",
        snapshot,
        batch_size=100,
    )

    # A single missed fetch doesn't deactivate - it's carried forward.
    assert stats.changed == 1
    assert stats.deactivated == 0
    assert stats.snapshot_changed is True
    assert len(session.statements) == 2
    snapshot_params = session.statements[-1].compile().params
    assert snapshot_params["manifest"][removed_fingerprint] == "pending:removed-hash"
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_second_consecutive_miss_deactivates_and_drops_from_manifest(monkeypatch) -> None:
    removed = _job("https://example.com/jobs/removed")
    changed = _job("https://example.com/jobs/changed", title="New title")
    snapshot = build_board_snapshot([changed])
    removed_fingerprint = fingerprint_for(removed)
    current = SimpleNamespace(
        board_hash="old-hash",
        manifest={
            removed_fingerprint: "pending:removed-hash",
            fingerprint_for(changed): "old-content-hash",
        },
    )

    async def _load(*_args, **_kwargs):
        return current

    monkeypatch.setattr(board_snapshots, "load_snapshot", _load)
    session = _Session()

    stats = await board_snapshots.reconcile_board(
        session,
        "greenhouse",
        "example",
        snapshot,
        batch_size=100,
    )

    assert stats.changed == 1
    assert stats.deactivated == 1
    assert stats.snapshot_changed is True
    assert len(session.statements) == 3
    assert "job_board_snapshots.manifest" in str(session.statements[1])
    snapshot_params = session.statements[-1].compile().params
    assert removed_fingerprint not in snapshot_params["manifest"]
    assert session.commits == 1
    assert session.rollbacks == 0
