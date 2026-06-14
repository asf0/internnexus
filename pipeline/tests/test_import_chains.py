from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestPipelineImports:
    """Pipeline-local import and entry-point smoke tests."""

    def test_pipeline_init_has_no_path_mutation(self):
        pipeline_init = PROJECT_ROOT / "pipeline" / "__init__.py"
        content = pipeline_init.read_text()

        assert "sys.path.insert" not in content

        code = """
import sys
before = list(sys.path)
import pipeline
after = list(sys.path)
print("UNCHANGED" if before == after else "MUTATED")
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0
        assert "UNCHANGED" in result.stdout

    def test_pipeline_imports_cleanly(self):
        code = """
import sys
sys.path.insert(0, '.')
import pipeline
print("SUCCESS: pipeline module imports cleanly")
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=PROJECT_ROOT
        )

        assert result.returncode == 0, f"Pipeline import failed: {result.stderr}"

    def test_pipeline_console_entry_point(self):
        env = {
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "test-model",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "CLASSIFICATION_MODEL": "test-classifier",
            "AUTH_SECRET": "abcdefghijklmnopqrstuvwxyz123456",
            "REDIS_URL": "redis://localhost:6379/0",
            "GREENHOUSE_API_URL": "https://boards-api.greenhouse.io/v1/boards",
            "LEVER_API_URL": "https://api.lever.co/v0/postings",
            "SIMPLIFY_JOBS_INTERN_URL": "https://example.com/intern",
            "SIMPLIFY_JOBS_NEW_GRAD_URL": "https://example.com/newgrad",
        }
        result = subprocess.run(
            [sys.executable, "-m", "pipeline.cli.run_pipeline", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env={**os.environ, **env},
        )

        assert "usage:" in result.stdout, f"run_pipeline entry point failed: {result.stderr}"


def test_pipeline_has_no_backend_or_shared_imports():
    forbidden = ("from app", "import app", "from backend", "import backend", "internnexus_shared")
    pipeline_dir = PROJECT_ROOT / "pipeline"
    offenders = []
    for path in pipeline_dir.rglob("*.py"):
        if path.name == "test_import_chains.py":
            continue
        if ".venv" in path.parts:
            continue
        content = path.read_text()
        for token in forbidden:
            if token in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {token}")
    assert offenders == []


def test_core_has_no_backend_or_pipeline_imports():
    """Core package must never import from backend or pipeline."""
    core_dir = PROJECT_ROOT / "packages" / "internnexus-core" / "internnexus_core"
    if not core_dir.exists():
        return
    forbidden = ("from app", "import app", "from backend", "import backend")
    offenders = []
    for path in core_dir.rglob("*.py"):
        content = path.read_text()
        for token in forbidden:
            if token in content:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {token}")
    assert offenders == []
