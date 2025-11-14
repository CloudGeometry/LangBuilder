"""Jira components for ActionBridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langbuilder.components._importing import import_mod

if TYPE_CHECKING:
    from .jira_auth import JiraAuth
    from .jira_create_issue import JiraCreateIssue
    from .jira_get_issue import JiraGetIssue
    from .jira_search_issues import JiraSearchIssues
    from .jira_update_issue import JiraUpdateIssue

_dynamic_imports = {
    "JiraAuth": "jira_auth",
    "JiraCreateIssue": "jira_create_issue",
    "JiraGetIssue": "jira_get_issue",
    "JiraSearchIssues": "jira_search_issues",
    "JiraUpdateIssue": "jira_update_issue",
}

__all__ = [
    "JiraAuth",
    "JiraCreateIssue",
    "JiraGetIssue",
    "JiraSearchIssues",
    "JiraUpdateIssue",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import Jira components on attribute access."""
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)
