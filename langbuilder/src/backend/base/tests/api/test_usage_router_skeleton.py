"""F3-T1: Tests for usage router skeleton.

Verifies:
- Router module can be imported
- Router has correct prefix and tags
- Router has expected route stubs registered

Uses importlib to bypass langflow.api.v1.__init__ chain (which requires
optional modules like openai).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock


def _load_router_module():
    """Load the usage router module directly, bypassing the api package init chain."""
    # Stub out modules that are not available in the test environment
    optional_stubs = [
        "langflow.api.utils",
        "langflow.api.utils.core",
        "fastapi_pagination",
    ]
    for mod in optional_stubs:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()

    # Also stub the lfx deps to avoid lfx.services.deps import errors
    if "lfx.services.deps" not in sys.modules:
        sys.modules["lfx.services.deps"] = MagicMock()

    # Direct file path import - avoids executing langflow.api.v1.__init__
    router_path = Path(__file__).parent.parent.parent / "langflow" / "api" / "v1" / "usage" / "router.py"
    spec = importlib.util.spec_from_file_location("langflow.api.v1.usage.router", router_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_router_module_importable():
    """The usage router module can be loaded without errors."""
    mod = _load_router_module()
    assert mod is not None


def test_router_object_exists():
    """The router object exists in the module."""
    mod = _load_router_module()
    assert hasattr(mod, "router")
    assert mod.router is not None


def test_router_has_correct_prefix():
    """Router prefix is /usage."""
    mod = _load_router_module()
    assert mod.router.prefix == "/usage"


def test_router_has_correct_tags():
    """Router tags include 'Usage & Cost Tracking'."""
    mod = _load_router_module()
    assert "Usage & Cost Tracking" in mod.router.tags


def test_router_has_get_usage_summary_route():
    """GET /usage/ route is registered on the router."""
    mod = _load_router_module()
    paths = [r.path for r in mod.router.routes]
    assert "/usage/" in paths


def test_router_has_flow_runs_route():
    """GET /usage/{flow_id}/runs route is registered on the router."""
    mod = _load_router_module()
    paths = [r.path for r in mod.router.routes]
    assert "/usage/{flow_id}/runs" in paths


def test_router_has_save_key_route():
    """POST /usage/settings/langwatch-key route is registered on the router."""
    mod = _load_router_module()
    paths = [r.path for r in mod.router.routes]
    assert "/usage/settings/langwatch-key" in paths


def test_router_has_key_status_route():
    """GET /usage/settings/langwatch-key/status route is registered on the router."""
    mod = _load_router_module()
    paths = [r.path for r in mod.router.routes]
    assert "/usage/settings/langwatch-key/status" in paths


def test_router_routes_count():
    """Router has at least 4 routes registered."""
    mod = _load_router_module()
    assert len(mod.router.routes) >= 4
