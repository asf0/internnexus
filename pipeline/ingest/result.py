"""Typed synchronization results shared by ingestion and runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


SYNC_SOURCES = ("greenhouse", "lever", "ashby")


@dataclass
class SourceFetchStats:
    """Mutable counters populated while one ATS source is streamed."""

    source: str
    configured_slugs: int
    jobs_fetched: int = 0
    fetch_errors: int = 0
    fatal_errors: int = 0

    def record_error(self, error_type: str) -> None:
        self.fetch_errors += 1
        if error_type != "http_404":
            self.fatal_errors += 1

    @property
    def complete(self) -> bool:
        return self.fatal_errors == 0


@dataclass(frozen=True)
class IngestResult:
    """Persistable synchronization context produced by a complete ingest pass."""

    sync_id: UUID
    total_fetched: int
    source_counts: dict[str, int]
    fetch_error_counts: dict[str, int]
    source_complete: dict[str, bool]
    jobs_changed: int = 0

    @classmethod
    def empty(cls, sync_id: UUID) -> IngestResult:
        return cls(
            sync_id=sync_id,
            total_fetched=0,
            source_counts={source: 0 for source in SYNC_SOURCES},
            fetch_error_counts={source: 0 for source in SYNC_SOURCES},
            source_complete={source: True for source in SYNC_SOURCES},
        )

    def to_metadata(self) -> dict[str, Any]:
        return {
            "sync_id": str(self.sync_id),
            "jobs_fetched": self.total_fetched,
            "source_counts": dict(self.source_counts),
            "fetch_error_counts": dict(self.fetch_error_counts),
            "source_complete": dict(self.source_complete),
            "jobs_changed": self.jobs_changed,
        }

    @classmethod
    def from_metadata(cls, value: dict[str, Any] | None) -> IngestResult | None:
        if not isinstance(value, dict) or not value.get("sync_id"):
            return None
        try:
            sync_id = UUID(str(value["sync_id"]))
            source_counts = {source: int((value.get("source_counts") or {}).get(source, 0)) for source in SYNC_SOURCES}
            return cls(
                sync_id=sync_id,
                total_fetched=int(value.get("jobs_fetched", sum(source_counts.values()))),
                source_counts=source_counts,
                fetch_error_counts={
                    source: int((value.get("fetch_error_counts") or {}).get(source, 0)) for source in SYNC_SOURCES
                },
                source_complete={
                    source: bool((value.get("source_complete") or {}).get(source, False)) for source in SYNC_SOURCES
                },
                jobs_changed=int(value.get("jobs_changed", 0)),
            )
        except (TypeError, ValueError):
            return None
