import importlib.util
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--generate-import-graph",
        action="store_true",
        default=False,
        help="Regenerate the runtime import graph fixture",
    )
    parser.addoption(
        "--generate-location-fixture",
        action="store_true",
        default=False,
        help="Regenerate the location normalisation golden fixture",
    )


def pytest_configure(config):
    if config.getoption("--generate-location-fixture"):
        mod_path = Path(__file__).resolve().parent / "unit" / "test_location_normalize_golden.py"
        spec = importlib.util.spec_from_file_location("_golden_gen", mod_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec from {mod_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod._generate_fixture()
        pytest.exit(
            "Fixture generated. Run tests without --generate-location-fixture.",
            returncode=0,
        )
