from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.chez_antoine.cg_jira_auth import CGJiraAuthComponent
    from lfx.components.chez_antoine.cg_jira_core import CGJiraCoreComponent
    from lfx.components.chez_antoine.cg_jira_sprint import CGJiraSprintComponent
    from lfx.components.chez_antoine.cg_jira_transitions import CGJiraTransitionsComponent
    from lfx.components.chez_antoine.cg_jira_users import CGJiraUsersComponent
    from lfx.components.chez_antoine.cg_jira_metadata import CGJiraMetadataComponent
    from lfx.components.chez_antoine.aws_lambda_invoke import AWSLambdaInvokeComponent

_dynamic_imports = {
    "CGJiraAuthComponent": "cg_jira_auth",
    "CGJiraCoreComponent": "cg_jira_core",
    "CGJiraSprintComponent": "cg_jira_sprint",
    "CGJiraTransitionsComponent": "cg_jira_transitions",
    "CGJiraUsersComponent": "cg_jira_users",
    "CGJiraMetadataComponent": "cg_jira_metadata",
    "AWSLambdaInvokeComponent": "aws_lambda_invoke",
}

__all__ = [
    "CGJiraAuthComponent",
    "CGJiraCoreComponent",
    "CGJiraSprintComponent",
    "CGJiraTransitionsComponent",
    "CGJiraUsersComponent",
    "CGJiraMetadataComponent",
    "AWSLambdaInvokeComponent",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import Chez Antoine components on attribute access."""
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
