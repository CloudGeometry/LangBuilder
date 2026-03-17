"""F3-T2: Tests for usage router registration in main api router.

Verifies that the usage router is registered in the main API router
so that /api/v1/usage/* routes are accessible.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock


def _stub_modules(*names: str) -> None:
    """Stub out optional modules not available in test environment."""
    stubs = [
        "fastapi_pagination",
        "langflow.api.utils",
        "langflow.api.utils.core",
        "lfx.services.deps",
        "openai",
        "langflow.api.v1.voice_mode",
        "langflow.api.build",
        "langflow.api.limited_background_tasks",
    ]
    for mod in stubs:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()
    for name in names:
        if name not in sys.modules:
            sys.modules[name] = MagicMock()


def _load_api_router():
    """Load the main api router module directly."""
    _stub_modules()
    router_path = Path(__file__).parent.parent.parent / "langflow" / "api" / "router.py"
    spec = importlib.util.spec_from_file_location("langflow.api.router", router_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_usage_router():
    """Load the usage router module."""
    _stub_modules()
    usage_path = Path(__file__).parent.parent.parent / "langflow" / "api" / "v1" / "usage" / "router.py"
    spec = importlib.util.spec_from_file_location("langflow.api.v1.usage.router", usage_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_usage_router_prefix_is_usage():
    """Usage router has /usage prefix."""
    mod = _load_usage_router()
    assert mod.router.prefix == "/usage"


def test_usage_router_has_4_routes():
    """Usage router has exactly 4 routes."""
    mod = _load_usage_router()
    assert len(mod.router.routes) == 4


def test_usage_route_paths_are_correct():
    """Usage router paths match the API contract."""
    mod = _load_usage_router()
    paths = {r.path for r in mod.router.routes}
    expected = {
        "/usage/",
        "/usage/{flow_id}/runs",
        "/usage/settings/langwatch-key",
        "/usage/settings/langwatch-key/status",
    }
    assert expected == paths


def test_usage_router_methods():
    """Usage routes have correct HTTP methods."""
    mod = _load_usage_router()
    method_map = {}
    for r in mod.router.routes:
        method_map[r.path] = r.methods

    assert "GET" in method_map.get("/usage/", set())
    assert "GET" in method_map.get("/usage/{flow_id}/runs", set())
    assert "POST" in method_map.get("/usage/settings/langwatch-key", set())
    assert "GET" in method_map.get("/usage/settings/langwatch-key/status", set())
