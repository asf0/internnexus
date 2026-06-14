from __future__ import annotations

from pipeline.sources import registry


def test_ashby_slugs_do_not_include_generic_common_company_slugs(monkeypatch):
    monkeypatch.setattr(
        registry,
        "load_discovery_results",
        lambda: {"greenhouse": [], "lever": [], "ashby": ["notion"]},
    )
    monkeypatch.setattr(registry, "load_common_companies", lambda: ["meta", "microsoft", "netflix"])

    slugs = registry.get_ashby_slugs()

    assert "notion" in slugs
    assert "meta" not in slugs
    assert "microsoft" not in slugs
    assert "netflix" not in slugs


def test_greenhouse_and_lever_still_include_common_company_slugs(monkeypatch):
    monkeypatch.setattr(
        registry,
        "load_discovery_results",
        lambda: {"greenhouse": ["databricks"], "lever": ["stripe"], "ashby": []},
    )
    monkeypatch.setattr(registry, "load_common_companies", lambda: ["meta"])

    assert registry.get_greenhouse_slugs() == ["databricks", "meta"]
    assert registry.get_lever_slugs() == ["meta", "stripe"]
