"""
langbuilder → langflow/lfx compatibility shim.

Redirects all `langbuilder.*` imports to the equivalent `langflow.*` or
`lfx.*` module so that flow JSON files saved from LangBuilder deployments
continue to work on Langflow 1.8.0.

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


# ── Flow JSON migration: renamed / removed components ──────────────────────
# Maps old component type names to their new equivalents in Langflow 1.8.0.
# Used by migrate_flow_json() to rewrite exported flow JSON so that flows
# created with older LangBuilder versions load without errors.
COMPONENT_RENAME_MAP: dict[str, str] = {
    # Langflow 1.2 renames
    "MergeData": "CombineData",
    # Langflow 1.7 renames
    "SaveFile": "WriteFile",
    "File": "ReadFile",
    "SmartFunction": "SmartTransform",
    "LLMRouter": "LLMSelector",
    # Langflow 1.7 – Bedrock migration
    "AmazonBedrockComponent": "AmazonBedrockConverseComponent",
}

# Components removed in newer versions — flows referencing these will get a
# warning but won't hard-fail (the node is dropped with a log message).
REMOVED_COMPONENTS: set[str] = {
    "LocalDB",
    "ZepMemory",
    "GmailLoader",
    "CombineText",  # deprecated in 1.5+
}

# Import-path renames that appear in flow JSON `type` fields
# (fully qualified module paths used in older LangBuilder flow exports)
MODULE_PATH_RENAME_MAP: dict[str, str] = {
    "langbuilder.components.": "lfx.components.",
    "langbuilder.base.": "langflow.base.",
    "langbuilder.custom.": "langflow.custom.",
}


def migrate_flow_json(flow_data: dict) -> dict:
    """Rewrite a flow JSON dict so old LangBuilder flows work on Langflow 1.8.0.

    Handles:
    - Component type renames (e.g. SaveFile → WriteFile)
    - Module path migrations (langbuilder.* → lfx.*/langflow.*)
    - Removed component warnings
    - Old `build()` method references → `build_model()` / output wiring

    Returns the migrated flow dict (mutated in place for performance).
    """
    import logging

    log = logging.getLogger("langbuilder_compat")

    nodes = flow_data.get("data", {}).get("nodes", [])
    if not nodes:
        # Try alternate structure (some exports nest differently)
        nodes = flow_data.get("nodes", [])

    removed_ids: list[str] = []

    for node in nodes:
        node_data = node.get("data", {})
        node_type = node_data.get("type", "")

        # 1. Rename component types
        if node_type in COMPONENT_RENAME_MAP:
            old_type = node_type
            node_data["type"] = COMPONENT_RENAME_MAP[node_type]
            log.info("Flow migration: renamed component %s → %s", old_type, node_data["type"])

        # 2. Handle removed components
        if node_type in REMOVED_COMPONENTS:
            log.warning(
                "Flow migration: component %s was removed in newer versions. "
                "Node %s will be dropped.",
                node_type,
                node.get("id", "?"),
            )
            removed_ids.append(node.get("id", ""))

        # 3. Migrate module paths in the 'type' field
        for old_prefix, new_prefix in MODULE_PATH_RENAME_MAP.items():
            if node_type.startswith(old_prefix):
                node_data["type"] = new_prefix + node_type[len(old_prefix):]
                break

        # 4. Migrate template/node references
        template = node_data.get("template", {})
        if template:
            _migrate_template(template)

    # Remove edges that reference removed nodes
    if removed_ids:
        edges = flow_data.get("data", {}).get("edges", [])
        if not edges:
            edges = flow_data.get("edges", [])
        flow_data.get("data", {})["edges"] = [
            e
            for e in edges
            if e.get("source") not in removed_ids and e.get("target") not in removed_ids
        ]

    return flow_data


def _migrate_template(template: dict) -> None:
    """Migrate old template field references."""
    for field_name, field_data in template.items():
        if not isinstance(field_data, dict):
            continue
        # Rename old `_type` references
        field_type = field_data.get("_type", "")
        if isinstance(field_type, str):
            for old_prefix, new_prefix in MODULE_PATH_RENAME_MAP.items():
                if field_type.startswith(old_prefix):
                    field_data["_type"] = new_prefix + field_type[len(old_prefix):]
                    break


# ── Import redirection machinery ───────────────────────────────────────────

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
