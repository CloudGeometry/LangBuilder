"""
langbuilder → langflow/lfx compatibility shim.

Redirects all `langbuilder.*` imports to the equivalent `langflow.*` or
`lfx.*` module so that flow JSON files saved from LangBuilder deployments
continue to work on Langflow 1.7.3.

Uses the modern Python 3.4+ MetaPathFinder API (find_spec / exec_module)
because Python 3.12 dropped the deprecated find_module / load_module API.

Mapping rules (more-specific prefixes win):
  langbuilder.base.models.*          →  lfx.base.models.*
  langbuilder.components.*           →  lfx.components.*
  langbuilder.base.*                 →  langflow.base.*
  langbuilder.services.tracing.spans →  (no-op shim with ComponentSpanTracker)
  langbuilder.*                      →  langflow.*  (catch-all)
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import types

# Ordered from most-specific to least-specific
_PREFIX_MAP = [
    ("langbuilder.base.models", "lfx.base.models"),
    ("langbuilder.components", "lfx.components"),
    ("langbuilder.base", "langflow.base"),
    ("langbuilder.custom", "langflow.custom"),
    ("langbuilder.field_typing", "langflow.field_typing"),
    ("langbuilder.helpers", "langflow.helpers"),
    ("langbuilder.inputs", "langflow.inputs"),
    ("langbuilder.io", "langflow.io"),
    ("langbuilder.logging", "langflow.logging"),
    ("langbuilder.schema", "langflow.schema"),
    ("langbuilder.services", "langflow.services"),
    ("langbuilder.template", "langflow.template"),
    ("langbuilder.utils", "langflow.utils"),
    ("langbuilder", "langflow"),  # catch-all
]

_SPAN_SHIM = "langbuilder.services.tracing.spans"


def _get_real_name(fullname: str) -> str | None:
    for lb_prefix, real_prefix in _PREFIX_MAP:
        if fullname == lb_prefix or fullname.startswith(lb_prefix + "."):
            return real_prefix + fullname[len(lb_prefix):]
    return None


class _SpanTrackerLoader(importlib.abc.Loader):
    """Loader for the ComponentSpanTracker no-op shim."""

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        from contextlib import contextmanager

        class _SpanContext:
            def set_input(self, key, value):
                pass

            def set_output(self, key, value):
                pass

            def set_metadata(self, key, value):
                pass

        class ComponentSpanTracker:
            """No-op shim — ComponentSpanTracker was removed in Langflow 1.7.3."""

            def __init__(self, component):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def log(self, *args, **kwargs):
                pass

            def set_attribute(self, *args, **kwargs):
                pass

            @contextmanager
            def span_sync(self, name, span_type="custom", inputs=None, metadata=None):
                yield _SpanContext()

            async def span(self, name, span_type="custom", inputs=None, metadata=None):
                from contextlib import asynccontextmanager

                @asynccontextmanager
                async def _noop():
                    yield _SpanContext()

                return _noop()

            @contextmanager
            def api_call(self, name, url=None, method=None, **kwargs):
                yield _SpanContext()

        module.ComponentSpanTracker = ComponentSpanTracker


class _RedirectLoader(importlib.abc.Loader):
    """Loader that aliases a langbuilder.* module to a real langflow/lfx module."""

    def __init__(self, real_name: str) -> None:
        self.real_name = real_name

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        real_mod = importlib.import_module(self.real_name)
        # Replace the shim module in sys.modules with the real module.
        # Python's import machinery reads sys.modules after exec_module returns,
        # so callers will receive the real module.
        sys.modules[module.__spec__.name] = real_mod


class _LangbuilderFinder(importlib.abc.MetaPathFinder):
    """Meta-path finder that redirects langbuilder.* sub-imports to langflow/lfx."""

    def find_spec(self, fullname: str, path, target=None):
        # Only handle langbuilder submodules (not langbuilder itself)
        if not fullname.startswith("langbuilder."):
            return None

        # Already resolved — don't intercept again
        if fullname in sys.modules:
            return None

        # Special case: ComponentSpanTracker shim
        if fullname == _SPAN_SHIM:
            return importlib.machinery.ModuleSpec(
                fullname, _SpanTrackerLoader(), is_package=False
            )

        real_name = _get_real_name(fullname)
        if real_name is None:
            return None

        # If the real module is already loaded (possibly with __spec__=None due to
        # sys.modules replacement patterns in langflow/__init__.py), use it directly
        # rather than calling find_spec which raises ValueError in that case.
        if real_name in sys.modules:
            real_mod = sys.modules[real_name]
            is_pkg = hasattr(real_mod, "__path__")
            return importlib.machinery.ModuleSpec(
                fullname,
                _RedirectLoader(real_name),
                is_package=is_pkg,
            )

        try:
            real_spec = importlib.util.find_spec(real_name)
        except (ModuleNotFoundError, ValueError):
            return None

        if real_spec is None:
            return None

        is_pkg = real_spec.submodule_search_locations is not None
        return importlib.machinery.ModuleSpec(
            fullname,
            _RedirectLoader(real_name),
            origin=real_spec.origin,
            is_package=is_pkg,
        )


# Install once — importing `langbuilder` activates the shim for all submodules.
if not any(isinstance(f, _LangbuilderFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _LangbuilderFinder())
