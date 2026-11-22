"""Tests for internnexus-core package imports."""

from __future__ import annotations


def test_core_package_imports():
    """Verify the core package imports cleanly."""
    import internnexus_core

    assert internnexus_core is not None


def test_core_has_no_backend_imports():
    """Core must never import from backend app."""
    import internnexus_core
    import pkgutil

    core = internnexus_core
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=core.__path__, prefix=core.__name__ + ".", onerror=lambda x: None
    ):
        try:
            mod = importer.find_module(modname).load_module(modname)
        except Exception:
            continue
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name, None)
            if attr is None:
                continue
            if hasattr(attr, "__name__"):
                name = getattr(attr, "__name__", "")
                if name.startswith("app."):
                    raise AssertionError(f"{modname} references backend module: {name}")


def test_core_has_no_pipeline_imports():
    """Core must never import from pipeline."""
    import internnexus_core
    import pkgutil

    core = internnexus_core
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=core.__path__, prefix=core.__name__ + ".", onerror=lambda x: None
    ):
        try:
            mod = importer.find_module(modname).load_module(modname)
        except Exception:
            continue
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name, None)
            if attr is None:
                continue
            if hasattr(attr, "__name__"):
                name = getattr(attr, "__name__", "")
                if name.startswith("pipeline"):
                    raise AssertionError(f"{modname} references pipeline module: {name}")
