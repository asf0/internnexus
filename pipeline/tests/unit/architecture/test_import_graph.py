"""Authoritative internal import-graph test for the pipeline package.

Verifies the `pipeline.*` module graph is acyclic by collecting imports that
execute at module-import time, skipping function bodies and TYPE_CHECKING
blocks.  Also runs per-module subprocess isolation smoke tests.
"""

from __future__ import annotations

from pipeline.tests.paths import PKG_ROOT
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = PKG_ROOT.parent

_ENV = {
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "EMBEDDING_MODEL": "test-model",
    "OPENAI_BASE_URL": "http://localhost:8080/v1",
    "CLASSIFICATION_MODEL": "test-classifier",
    "AUTH_SECRET": "abcdefghijklmnopqrstuvwxyz123456",
    "REDIS_URL": "redis://localhost:6379/0",
    "GREENHOUSE_API_URL": "https://boards-api.greenhouse.io/v1/boards",
    "LEVER_API_URL": "https://api.lever.co/v0/postings",
    "ASHBY_API_URL": "https://api.ashbyhq.com/posting-api/job-board",
    "SIMPLIFY_JOBS_INTERN_URL": "https://example.com/intern",
    "SIMPLIFY_JOBS_NEW_GRAD_URL": "https://example.com/newgrad",
    "DATA_DIR": "/tmp/ensign-pipeline-tests",
}

_EXCLUDE_PARTS = {".venv", "build", "dist", "site-packages", "tests", "__pycache__"}

_INTERNAL_PREFIX = "pipeline."


def _modules() -> list[str]:
    modules: list[str] = []
    for pyfile in sorted(PKG_ROOT.rglob("*.py")):
        if any(part in _EXCLUDE_PARTS or part.endswith(".egg-info") for part in pyfile.parts):
            continue
        rel = pyfile.relative_to(REPO_ROOT).with_suffix("")
        mod = ".".join(rel.parts)
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        modules.append(mod)
    return modules


def _module_pkg(module: str) -> str:
    dot = module.rfind(".")
    return module[:dot] if dot != -1 else ""


# ---------------------------------------------------------------------------
# AST-based import collection
# ---------------------------------------------------------------------------


def _is_type_checking(test_node: ast.expr) -> bool:
    return (isinstance(test_node, ast.Name) and test_node.id == "TYPE_CHECKING") or (
        isinstance(test_node, ast.Attribute)
        and isinstance(test_node.value, ast.Name)
        and test_node.value.id == "typing"
        and test_node.attr == "TYPE_CHECKING"
    )


def _module_scope_imports(tree: ast.AST) -> list[ast.Import | ast.ImportFrom]:
    found: list[ast.Import | ast.ImportFrom] = []

    def _walk(nodes: list[ast.stmt]) -> None:
        for n in nodes:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                found.append(n)
            elif isinstance(n, ast.If):
                if not _is_type_checking(n.test):
                    _walk(n.body)
                    _walk(n.orelse)
            elif isinstance(n, (ast.Try, ast.TryStar)):
                _walk(n.body)
                for h in n.handlers:
                    _walk(h.body)
                _walk(n.orelse)
                _walk(n.finalbody)
            elif isinstance(n, ast.ClassDef):
                _walk(n.body)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                _walk(n.body)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.While)):
                _walk(n.body)
                _walk(n.orelse)
            elif isinstance(n, ast.Match):
                for case in n.cases:
                    _walk(case.body)

    _walk(tree.body)
    return found


# ---------------------------------------------------------------------------
# Import resolution
# ---------------------------------------------------------------------------


def _resolve_targets(node: ast.Import | ast.ImportFrom, current_module: str) -> list[str]:
    """Return list of fully-qualified target module names for one import statement."""
    pkg = _module_pkg(current_module)

    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    # ast.ImportFrom
    if node.level == 0:
        base = node.module or ""
    else:
        up = node.level
        parts = pkg.split(".") if pkg else []
        while up > 1 and parts:
            parts.pop()
            up -= 1
        base = ".".join(parts) if parts else ""
        if node.module:
            base = f"{base}.{node.module}" if base else node.module

    if node.module is None:
        return [f"{base}.{alias.name}" if base else alias.name for alias in node.names]
    return [base]


# ---------------------------------------------------------------------------
# Graph & cycle detection
# ---------------------------------------------------------------------------


def _build_dep_graph() -> dict[str, set[str]]:
    module_set = set(_modules())
    graph: dict[str, set[str]] = {m: set() for m in module_set}

    for mod in sorted(module_set):
        py_path = PKG_ROOT / "/".join(mod.split(".")[1:])
        # Resolve __init__ for packages
        if (py_path / "__init__.py").exists():
            py_path = py_path / "__init__.py"
        else:
            py_path = py_path.with_suffix(".py")

        if not py_path.exists():
            continue

        tree = ast.parse(py_path.read_text())
        for node in _module_scope_imports(tree):
            for target in _resolve_targets(node, mod):
                if target.startswith(_INTERNAL_PREFIX) and target in module_set:
                    if target != mod:
                        graph[mod].add(target)

    return graph


def _topological_sort(graph: dict[str, set[str]]) -> list[str] | None:
    in_degree: dict[str, int] = {n: 0 for n in graph}
    for src, deps in graph.items():
        for dep in deps:
            in_degree[dep] = in_degree.get(dep, 0) + 1

    zero = [n for n, d in in_degree.items() if d == 0]
    sorted_nodes: list[str] = []

    while zero:
        n = zero.pop()
        sorted_nodes.append(n)
        for dep in graph.get(n, set()):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                zero.append(dep)

    return sorted_nodes if len(sorted_nodes) == len(graph) else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImportGraphAcyclic:
    def test_graph_is_acyclic(self) -> None:
        graph = _build_dep_graph()
        sorted_nodes = _topological_sort(graph)
        if sorted_nodes is None:
            remaining = set(graph) - set(_topological_sort(graph) or [])
            pytest.fail(f"Cycle detected among pipeline modules. Unreachable modules: {sorted(remaining)}")
        # Verify all modules are present
        assert len(sorted_nodes) == len(graph)
        all_modules = set(_modules())
        assert set(sorted_nodes) == all_modules, f"Missed modules: {sorted(all_modules - set(sorted_nodes))}"

    def test_no_self_loops(self) -> None:
        graph = _build_dep_graph()
        for mod, deps in graph.items():
            assert mod not in deps, f"Self-loop in {mod}"


class TestPerModuleSubprocessImport:
    @pytest.mark.parametrize("module", _modules())
    def test_module_imports_in_isolation(self, module: str) -> None:
        code = f"import {module}"
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, **_ENV, "PYTHONPATH": str(REPO_ROOT)},
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Import of {module} failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
        )
