from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import importlib
import sys
from pathlib import Path

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pipeline
import pipeline.cli


class TestPipelineLazyExports:
    def test_all_contains_expected_names(self) -> None:
        assert set(pipeline.__all__) == {
            "fetch_and_ingest",
            "cleanup_locations",
            "generate_embeddings",
            "upsert_jobs",
        }

    def test_each_export_is_accessible_via_getattr(self) -> None:
        for name in pipeline.__all__:
            obj = getattr(pipeline, name)
            assert obj is not None
            assert callable(obj)

    def test_no_false_positive_exports(self) -> None:
        with __import__("pytest").raises(AttributeError):
            getattr(pipeline, "nonexistent_export")

    def test_lazy_resolution_is_consistent(self) -> None:
        first = getattr(pipeline, "fetch_and_ingest")
        second = getattr(pipeline, "fetch_and_ingest")
        assert first is second


class TestCliLazyExports:
    def test_all_contains_expected_names(self) -> None:
        assert set(pipeline.cli.__all__) == {
            "args",
            "consolidate_categories",
            "run_pipeline",
        }

    def test_each_submodule_is_accessible(self) -> None:
        for name in pipeline.cli.__all__:
            mod = importlib.import_module(f"pipeline.cli.{name}")
            assert mod is not None
            assert hasattr(mod, "__name__")
            assert mod.__name__.startswith("pipeline.cli.")
