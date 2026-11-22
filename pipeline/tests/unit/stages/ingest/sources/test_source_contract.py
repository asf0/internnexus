"""Contract tests for the three source adapter clients.

Each adapter is exercised through its real normalization path, but HTTP is
mocked locally with real ``httpx.Request``/``httpx.Response`` objects so no
live ATS endpoint is contacted.
"""

from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import importlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema


_GREENHOUSE_PAYLOAD: dict[str, Any] = {
    "jobs": [
        {
            "id": 123,
            "title": "Software Engineer Intern",
            "company_name": "Stripe",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
            "content": "<p>A sufficiently long internship description.</p>",
            "first_published": "2026-01-01T00:00:00.000Z",
            "updated_at": "2026-01-01T00:00:00.000Z",
        }
    ]
}


_LEVER_PAYLOAD: list[dict[str, Any]] = [
    {
        "id": "job-1",
        "text": "Software Engineer Intern",
        "categories": {"location": "San Francisco, CA", "commitment": "Full-time"},
        "country": "US",
        "applyUrl": "https://jobs.lever.co/stripe/job-1",
        "description": "<p>A sufficiently long internship description.</p>",
        "createdAt": 1_700_000_000_000,
        "workplaceType": "remote",
        "hostedUrl": "https://jobs.lever.co/stripe/job-1",
    }
]


_ASHBY_PAYLOAD: dict[str, Any] = {
    "jobs": [
        {
            "id": "uuid-1",
            "title": "Software Engineer Intern",
            "companyName": "Notion",
            "department": "Engineering",
            "team": "Engineering",
            "employmentType": "FullTime",
            "location": "San Francisco, California",
            "publishedAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:00:00.000Z",
            "isListed": True,
            "isRemote": False,
            "address": {
                "postalAddress": {
                    "addressRegion": "California",
                    "addressCountry": "United States",
                    "addressLocality": "San Francisco",
                }
            },
            "jobUrl": "https://jobs.ashbyhq.com/notion/uuid-1",
            "applyUrl": "https://jobs.ashbyhq.com/notion/uuid-1/application",
            "descriptionHtml": "<p>A sufficiently long internship description.</p>",
            "descriptionPlain": "A sufficiently long internship description.",
        }
    ]
}


@pytest.mark.parametrize(
    "module_name, class_name, slug, payload, expected",
    [
        pytest.param(
            "pipeline.stages.ingest.sources.greenhouse",
            "GreenhouseClient",
            "stripe",
            _GREENHOUSE_PAYLOAD,
            {
                "source": "greenhouse",
                "company": "Stripe",
                "title": "Software Engineer Intern",
                "location": "San Francisco, CA",
                "apply_url": "https://boards.greenhouse.io/stripe/jobs/123",
                "description_text": "<p>A sufficiently long internship description.</p>",
            },
            id="greenhouse",
        ),
        pytest.param(
            "pipeline.stages.ingest.sources.lever",
            "LeverClient",
            "stripe",
            _LEVER_PAYLOAD,
            {
                "source": "lever",
                "company": "stripe",
                "title": "Software Engineer Intern",
                "location": "San Francisco, CA",
                "apply_url": "https://jobs.lever.co/stripe/job-1",
                "description_text": "<p>A sufficiently long internship description.</p>",
            },
            id="lever",
        ),
        pytest.param(
            "pipeline.stages.ingest.sources.ashby",
            "AshbyClient",
            "notion",
            _ASHBY_PAYLOAD,
            {
                "source": "ashby",
                "company": "Notion",
                "title": "Software Engineer Intern",
                "location": "San Francisco, California, United States",
                "apply_url": "https://jobs.ashbyhq.com/notion/uuid-1/application",
                "description_text": "A sufficiently long internship description.",
            },
            id="ashby",
        ),
    ],
)
def test_source_client_contract(
    module_name: str,
    class_name: str,
    slug: str,
    payload: dict[str, Any] | list[dict[str, Any]],
    expected: dict[str, Any],
) -> None:
    module = importlib.import_module(module_name)
    client_class = getattr(module, class_name)

    # The httpx client is instantiated by the shared core BaseATSClient.
    with patch("internnexus_core.ats.httpx.Client") as mock_client_class:
        mock_http_client = MagicMock()
        mock_client_class.return_value = mock_http_client
        mock_http_client.get.return_value = httpx.Response(
            status_code=200,
            json=payload,
            request=httpx.Request("GET", "https://example.com/jobs"),
        )

        client = client_class(timeout_seconds=20.0)
        mock_client_class.assert_called_once_with(timeout=20.0)

        jobs = client.fetch_jobs(slug)
        assert isinstance(jobs, list)
        assert len(jobs) == 1
        job = jobs[0]
        assert isinstance(job, JobSchema)
        assert job.source == expected["source"]
        assert job.company == expected["company"]
        assert job.title == expected["title"]
        assert job.location == expected["location"]
        assert job.apply_url == expected["apply_url"]
        assert job.description_text == expected["description_text"]

        client.close()
        mock_http_client.close.assert_called_once()

        with client_class(timeout_seconds=20.0) as context_client:
            assert isinstance(context_client, client_class)
        assert mock_http_client.close.call_count == 2
