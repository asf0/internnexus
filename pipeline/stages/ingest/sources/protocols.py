"""Formal contract for ATS job-source adapters.

The three concrete clients (``GreenhouseClient``, ``LeverClient``,
``AshbyClient``) already satisfy this Protocol structurally. The Protocol
exists to make the implicit contract explicit and checkable by static
analyzers without forcing the adapters to inherit from an ABC.

All clients are synchronous (``httpx.Client`` under the hood); the ingest
orchestrator wraps blocking calls in ``asyncio.to_thread``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain import JobSchema


@runtime_checkable
class JobSourceClient(Protocol):
    """Contract for an ATS job source adapter.

    Protocols describe *instances*, so the constructor signature is not part
    of this interface; each concrete client keeps its own ``__init__``. A
    factory, if ever needed, should be annotated separately as
    ``Callable[[], JobSourceClient]``.
    """

    def close(self) -> None: ...

    def __enter__(self) -> JobSourceClient: ...

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object, /) -> None: ...

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]: ...
