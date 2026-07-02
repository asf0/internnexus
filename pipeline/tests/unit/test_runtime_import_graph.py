"""Runtime import graph baseline test.

Captures the current import graph between runtime/ and repositories/ as a
golden fixture.  PR #2 and PR #3 update this fixture when they change
import paths; this test enforces no unexpected graph drift.

To regenerate the fixture after an intentional change:
    pytest tests/unit/test_runtime_import_graph.py --generate-import-graph
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "runtime_import_graph.json"
TARGET_DIRS = ("runtime", "repositories")


class _ImportGraphVisitor(ast.NodeVisitor):
    """Collect imports while tracking whether they occur in a function."""

    def __init__(self, source_file: str) -> None:
        self.source_file = source_file
        self.function_stack: list[str] = []
        self.edges: list[dict[str, Any]] = []

    @property
    def kind(self) -> str:
        if self.function_stack:
            return f"lazy-in-{self.function_stack[-1]}"
        return "top-level"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.edges.append(
                {
                    "source_file": self.source_file,
                    "from_module": alias.name,
                    "imported_names": [alias.name],
                    "kind": self.kind,
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = f"{'.' * node.level}{node.module or ''}"
        self.edges.append(
            {
                "source_file": self.source_file,
                "from_module": module,
                "imported_names": [alias.name for alias in node.names],
                "kind": self.kind,
            }
        )


def _classify_imports(source_file: str, tree: ast.AST) -> list[dict[str, Any]]:
    """Walk AST and return imports from all module ecosystems."""
    visitor = _ImportGraphVisitor(source_file)
    visitor.visit(tree)
    return visitor.edges


def _build_graph() -> dict[str, Any]:
    """Walk all .py files in target directories and build import graph."""
    all_edges: list[dict[str, Any]] = []

    for target in TARGET_DIRS:
        target_dir = PROJECT_ROOT / target
        if not target_dir.exists():
            continue
        for pyfile in sorted(target_dir.rglob("*.py")):
            if "__pycache__" in pyfile.parts:
                continue
            rel = str(pyfile.relative_to(PROJECT_ROOT))
            tree = ast.parse(pyfile.read_text())
            edges = _classify_imports(rel, tree)
            all_edges.extend(edges)

    return {
        "edges": sorted(
            all_edges,
            key=lambda edge: (
                edge["source_file"],
                edge["from_module"],
                edge["kind"],
                edge["imported_names"],
            ),
        )
    }


def _normalize_for_comparison(graph: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    """Normalize graph edges for deterministic comparison."""
    return tuple(
        (
            edge["source_file"],
            edge["from_module"],
            edge["kind"],
            tuple(edge["imported_names"]),
        )
        for edge in graph["edges"]
    )


@pytest.fixture(scope="module")
def current_graph() -> dict[str, Any]:
    return _build_graph()


@pytest.fixture(scope="module")
def fixture_graph(current_graph: dict[str, Any], pytestconfig: pytest.Config) -> dict[str, Any]:
    if pytestconfig.getoption("--generate-import-graph"):
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(json.dumps(current_graph, indent=2) + "\n")
        return current_graph
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(f"Import graph fixture not found: {FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text())


class TestRuntimeImportGraph:
    """Assert the current import graph matches the golden fixture."""

    def test_graph_matches_fixture(self, current_graph: dict[str, Any], fixture_graph: dict[str, Any]) -> None:
        current = _normalize_for_comparison(current_graph)
        expected = _normalize_for_comparison(fixture_graph)

        if current != expected:
            missing = set(expected) - set(current)
            extra = set(current) - set(expected)
            msg = ["Import graph drift detected."]
            if missing:
                msg.append(f"\nMissing edges ({len(missing)}):")
                for edge in sorted(missing):
                    msg.append(f"  {edge}")
            if extra:
                msg.append(f"\nExtra edges ({len(extra)}):")
                for edge in sorted(extra):
                    msg.append(f"  {edge}")
            pytest.fail("\n".join(msg))

    def test_lazy_imports_captured(self, current_graph: dict[str, Any]) -> None:
        """Only the documented optional ctypes import may remain lazy."""
        lazy = [e for e in current_graph["edges"] if e["kind"].startswith("lazy-in-")]
        assert lazy == [
            {
                "source_file": "runtime/services.py",
                "from_module": "ctypes",
                "imported_names": ["ctypes"],
                "kind": "lazy-in-trim_process_memory",
            }
        ]

    def test_graph_includes_stdlib_third_party_and_pipeline_imports(self, current_graph: dict[str, Any]) -> None:
        modules = {edge["from_module"] for edge in current_graph["edges"]}
        assert {"sys", "sqlalchemy", "pipeline.db"} <= modules
