from __future__ import annotations

from app.api.admin import router


def _route_methods_by_path() -> dict[str, set[str]]:
    route_map: dict[str, set[str]] = {}
    for route in router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        route_map.setdefault(path, set()).update(methods)
    return route_map


def test_admin_combined_router_preserves_representative_paths():
    routes = _route_methods_by_path()

    assert "GET" in routes["/admin/jobs"]
    assert "POST" in routes["/admin/jobs"]
    assert "GET" in routes["/admin/jobs/stats"]
    assert "POST" in routes["/admin/jobs/bulk"]
    assert "GET" in routes["/admin/users"]
    assert "POST" in routes["/admin/users"]
    assert "GET" in routes["/admin/users/export"]
    assert "GET" in routes["/admin/me"]
    assert "GET" in routes["/admin/pipeline-runs"]
    assert "POST" in routes["/admin/pipeline-runs/trigger"]
    assert "GET" in routes["/admin/clicks"]
    assert "GET" in routes["/admin/clicks/stats"]


def test_admin_router_has_expected_domain_route_count():
    routes = _route_methods_by_path()
    assert len(routes) >= 25
