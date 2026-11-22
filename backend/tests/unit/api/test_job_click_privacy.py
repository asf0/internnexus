from __future__ import annotations

from types import SimpleNamespace

from app.api import jobs


def test_client_ip_hash_is_keyed_and_domain_separated(monkeypatch) -> None:
    monkeypatch.setattr(jobs, "get_settings", lambda: SimpleNamespace(resolved_ip_hash_secret="a" * 32))

    first = jobs._hash_client_ip("203.0.113.7")
    second = jobs._hash_client_ip("203.0.113.7")
    other_ip = jobs._hash_client_ip("203.0.113.8")

    assert first == second
    assert first != other_ip
    assert len(first) == 16

    monkeypatch.setattr(jobs, "get_settings", lambda: SimpleNamespace(resolved_ip_hash_secret="b" * 32))
    assert jobs._hash_client_ip("203.0.113.7") != first
