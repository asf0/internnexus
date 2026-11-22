"""Tests for shared synchronous ATS HTTP behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from internnexus_core.ats import BaseATSClient, is_retryable_ats_error


def _response_error(status_code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(status_code, request=httpx.Request("GET", "https://example.test"))
    return httpx.HTTPStatusError("request failed", request=response.request, response=response)


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_retryable_ats_statuses(status_code: int) -> None:
    assert is_retryable_ats_error(_response_error(status_code)) is True


@pytest.mark.parametrize("status_code", [400, 401, 404])
def test_non_retryable_ats_statuses(status_code: int) -> None:
    assert is_retryable_ats_error(_response_error(status_code)) is False


def test_get_json_retries_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object.__new__(BaseATSClient)
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"jobs": []}
    client._client = MagicMock()
    client._client.get.side_effect = [httpx.ConnectError("offline"), response]

    monkeypatch.setattr("internnexus_core.ats.wait_exponential", lambda **_kwargs: lambda _: 0)

    assert client._get_json("https://example.test/jobs") == {"jobs": []}
    assert client._client.get.call_count == 2
