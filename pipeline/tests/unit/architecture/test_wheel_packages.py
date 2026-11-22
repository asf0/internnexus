"""Wheel-content verification test.

Cross-checks source packages, manifest packages, and built-wheel packages.
Also asserts no bytecode artefacts are shipped in the wheel.
"""

from __future__ import annotations

from pipeline.tests.paths import PKG_ROOT
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

import pytest


_PYPROJECT = PKG_ROOT / "pyproject.toml"

_EXCLUDE_PARTS = {".venv", "build", "dist", "__pycache__", "tests", "site-packages"}


def _source_packages() -> set[str]:
    pkgs: set[str] = set()
    for init in PKG_ROOT.rglob("__init__.py"):
        if any(part in _EXCLUDE_PARTS or part.endswith(".egg-info") for part in init.parts):
            continue
        rel = init.parent.relative_to(PKG_ROOT.parent)
        pkg = ".".join(rel.parts)
        pkgs.add(pkg)
    return pkgs


def _manifest_packages() -> set[str]:
    data = tomllib.loads(_PYPROJECT.read_text())
    return set(data["tool"]["setuptools"]["packages"])


def _build_wheel_into(out_dir: Path) -> Path:
    ignore = shutil.ignore_patterns(
        ".venv",
        "build",
        "dist",
        "*.egg-info",
        "__pycache__",
        ".git",
        "tests",
        "node_modules",
        "output",
        "apis",
    )
    with tempfile.TemporaryDirectory() as td:
        tds = Path(td) / "src"
        shutil.copytree(PKG_ROOT, tds, ignore=ignore)
        subprocess.run(
            ["uv", "build", "--wheel", "--no-progress", "-o", str(out_dir)],
            cwd=tds,
            check=True,
            capture_output=True,
        )
    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, got {len(wheels)}: {wheels}"
    return wheels[0]


def _wheel_names(wheel_path: Path) -> set[str]:
    with zipfile.ZipFile(wheel_path) as z:
        return set(z.namelist())


def _wheel_module_names(names: set[str]) -> set[str]:
    modules: set[str] = set()
    for name in names:
        if name.endswith(".py") and not name.startswith("__") and not name.endswith("__init__.py"):
            mod = name.rstrip("/")[:-3].replace("/", ".")
            modules.add(mod)
    return modules


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestManifestCompleteness:
    def test_manifest_covers_every_source_package(self) -> None:
        src = _source_packages()
        man = _manifest_packages()
        missing = sorted(src - man)
        assert missing == [], f"Source packages missing from setuptools manifest: {missing}"

    def test_no_stale_manifest_entries(self) -> None:
        src = _source_packages()
        man = _manifest_packages()
        stale = sorted(man - src)
        assert stale == [], f"Manifest packages not present as source directories: {stale}"


class TestWheelContents:
    @pytest.fixture(scope="class")
    def wheel_path(self) -> Path:
        out_dir = Path(tempfile.mkdtemp(prefix="wheel-test-"))
        try:
            yield _build_wheel_into(out_dir)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def wheel_names(self, wheel_path: Path) -> set[str]:
        return _wheel_names(wheel_path)

    def test_every_manifest_package_in_wheel(self, wheel_path: Path, wheel_names: set[str]) -> None:
        missing: list[str] = []
        for pkg in sorted(_manifest_packages()):
            prefix = pkg.replace(".", "/") + "/__init__.py"
            if prefix not in wheel_names:
                missing.append(pkg)
        assert missing == [], f"Manifest packages missing from wheel: {missing}"

    def test_no_bytecode_in_wheel(self, wheel_path: Path, wheel_names: set[str]) -> None:
        offenders = [n for n in wheel_names if "__pycache__" in n or n.endswith((".pyc", ".pyo"))]
        assert offenders == [], f"Bytecode artefacts in wheel: {offenders}"

    def test_package_data_in_wheel(self, wheel_path: Path, wheel_names: set[str]) -> None:
        expected = [
            "pipeline/pipeline.yaml",
        ]
        missing = [e for e in expected if e not in wheel_names]
        assert missing == [], f"Package data missing from wheel: {missing}"

    def test_source_modules_in_wheel(self, wheel_path: Path, wheel_names: set[str]) -> None:
        missing: list[str] = []
        for pyfile in PKG_ROOT.rglob("*.py"):
            if any(part in _EXCLUDE_PARTS or part.endswith(".egg-info") for part in pyfile.parts):
                continue
            rel = pyfile.relative_to(PKG_ROOT)
            wheel_path_str = f"pipeline/{rel.as_posix()}"
            if wheel_path_str not in wheel_names:
                missing.append(str(rel))
        assert missing == [], f"Source modules missing from wheel: {missing}"
