"""Pipeline-local base for synchronous ATS adapters.

Builds on the core HTTP client and reduces each provider adapter to its
distinct pieces: base URL setting, request URL/params, payload extraction,
and per-job normalization.
"""

from __future__ import annotations

from typing import Any, ClassVar

from internnexus_core.ats import BaseATSClient

from pipeline.infra.settings import get_settings
from pipeline.domain import JobSchema


class PipelineATSClient(BaseATSClient):
    """Template-method base for pipeline ATS adapters."""

    #: Name of the settings attribute holding this provider's API base URL.
    settings_attr: ClassVar[str]

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        super().__init__(timeout_seconds)
        self.base_url = getattr(get_settings(), self.settings_attr)

    def fetch_jobs(self, company_slug: str) -> list[JobSchema]:
        """Fetch and normalize all jobs for one company slug."""
        payload = self._get_json(self._jobs_url(company_slug), params=self._request_params())
        return self._normalize_jobs(company_slug, self._extract_jobs(payload))

    def _jobs_url(self, company_slug: str) -> str:
        raise NotImplementedError

    def _request_params(self) -> dict[str, str]:
        return {}

    def _extract_jobs(self, payload: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _normalize_jobs(self, company_slug: str, jobs: list[dict[str, Any]]) -> list[JobSchema]:
        raise NotImplementedError
