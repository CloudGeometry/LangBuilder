"""CG-Jira Transitions Component

Get available status transitions for an issue and move issues to new
statuses.  Transition names are resolved to IDs internally so the agent
never needs to know numeric transition IDs.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.io import DataInput, MessageTextInput, StrInput
from langbuilder.schema.data import Data

from langbuilder.components.chez_antoine.cg_jira_utils import (
    build_error_response,
    error_code_from_status,
    extract_auth,
    jira_request,
    parse_jira_error,
    text_to_adf,
)

if TYPE_CHECKING:
    pass


class CGJiraTransitionsComponent(LCToolComponent):
    """Get available status transitions and move Jira issues between statuses.

    Exposes two tools:

    1. **cg_jira_get_transitions** -- list the transitions available for an
       issue given its current workflow state.
    2. **cg_jira_transition_issue** -- move an issue to a new status by
       transition *name* (case-insensitive).  The component resolves the
       name to a transition ID internally.

    **Authentication:** Connect a CG-JiraAuth component to the *Jira Auth*
    input.  Credentials are shared across all CG-Jira components in the
    flow.
    """

    display_name = "CG-Jira Transitions"
    description = (
        "Get available status transitions for a Jira issue and move "
        "issues between statuses."
    )
    documentation = (
        "https://developer.atlassian.com/cloud/jira/platform/rest/v3/"
        "api-group-issues/#api-rest-api-3-issue-issueidorkey-transitions-get"
    )
    icon = "Jira"
    name = "CGJiraTransitions"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Connect a CG-JiraAuth component to provide credentials.",
            required=True,
        ),
        MessageTextInput(
            name="issue_key",
            display_name="Issue Key",
            info="Jira issue key (e.g. PROJ-123).",
            required=True,
            tool_mode=True,
        ),
        StrInput(
            name="transition_name",
            display_name="Transition Name",
            info="Name of the transition to perform (e.g. 'In Progress', 'Done'). Case-insensitive.",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="comment",
            display_name="Comment",
            info="Optional comment to add when transitioning the issue.",
            required=False,
            tool_mode=True,
        ),
    ]

    # Uses default LCToolComponent outputs (api_run_model, api_build_tool)

    # ------------------------------------------------------------------
    # run_model  (deterministic / flow-edge execution)
    # ------------------------------------------------------------------

    def run_model(self) -> Data:
        """Execute the component's main logic.

        If ``transition_name`` is provided, performs a transition;
        otherwise returns available transitions for the issue.
        """
        issue_key = str(self.issue_key).strip() if self.issue_key else ""
        if not issue_key:
            return build_error_response(
                "issue_key is required.",
                error_code="validation_error",
                issue_key=None,
            )

        transition_name = (
            str(self.transition_name).strip() if self.transition_name else ""
        )

        if transition_name:
            comment = str(self.comment).strip() if self.comment else ""
            return self._transition_issue(issue_key, transition_name, comment)
        return self._get_transitions(issue_key)

    # ------------------------------------------------------------------
    # Private implementation methods
    # ------------------------------------------------------------------

    def _get_transitions(self, issue_key: str) -> Data:
        """Fetch available transitions for *issue_key*.

        Returns a ``Data`` object with ``issue_key``, ``current_status``,
        and a ``transitions`` list.
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                issue_key=issue_key,
            )

        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}/transitions"

        try:
            self.status = f"Fetching transitions for {issue_key}..."
            response = jira_request(
                "GET", url, auth["headers"], log=self.log
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching transitions.",
                error_code="timeout",
                issue_key=issue_key,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                issue_key=issue_key,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                issue_key=issue_key,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                issue_key=issue_key,
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code, issue_key=issue_key)

        data = response.json()
        raw_transitions = data.get("transitions", [])

        transitions = []
        for t in raw_transitions:
            to_obj = t.get("to", {})
            category = (to_obj.get("statusCategory") or {}).get("key", "")
            transitions.append(
                {
                    "id": str(t.get("id", "")),
                    "name": t.get("name", ""),
                    "to_status": to_obj.get("name", ""),
                    "to_category": category,
                }
            )

        # Attempt to determine current status from the issue itself
        current_status = ""
        try:
            issue_url = (
                f"{auth['base_url']}/rest/api/3/issue/{issue_key}"
                "?fields=status"
            )
            issue_resp = jira_request(
                "GET", issue_url, auth["headers"], log=self.log
            )
            if issue_resp.status_code == 200:
                fields = issue_resp.json().get("fields", {})
                current_status = (fields.get("status") or {}).get("name", "")
        except Exception:
            pass  # Non-critical; we still return transitions

        self.status = (
            f"Found {len(transitions)} transition(s) for {issue_key}"
        )
        return Data(
            data={
                "issue_key": issue_key,
                "current_status": current_status,
                "transitions": transitions,
            }
        )

    def _transition_issue(
        self,
        issue_key: str,
        transition_name: str,
        comment: str = "",
    ) -> Data:
        """Move *issue_key* to a new status via *transition_name*.

        Resolves the human-readable name to a transition ID by first
        calling ``_get_transitions``, then POSTs the transition.
        """
        import requests as _requests

        # Step 1: get available transitions
        transitions_data = self._get_transitions(issue_key)

        if transitions_data.data.get("error"):
            return transitions_data

        available = transitions_data.data.get("transitions", [])
        if not available:
            return build_error_response(
                f"No transitions available for {issue_key}.",
                error_code="no_transitions",
                issue_key=issue_key,
                transitioned=False,
            )

        # Step 2: case-insensitive name match
        match = None
        name_lower = transition_name.lower()
        for t in available:
            if t["name"].lower() == name_lower:
                match = t
                break

        if match is None:
            available_names = [t["name"] for t in available]
            return build_error_response(
                f"Transition '{transition_name}' not found for {issue_key}. "
                f"Available transitions: {', '.join(available_names)}",
                error_code="invalid_transition",
                issue_key=issue_key,
                transitioned=False,
                available_transitions=available_names,
            )

        # Step 3: build request body
        body: dict = {
            "transition": {"id": str(match["id"])},
        }

        if comment:
            body["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": text_to_adf(comment),
                        }
                    }
                ],
            }

        # Step 4: POST the transition
        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                issue_key=issue_key,
                transitioned=False,
            )

        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}/transitions"

        try:
            self.status = (
                f"Transitioning {issue_key} to '{match['to_status']}'..."
            )
            response = jira_request(
                "POST",
                url,
                auth["headers"],
                json=body,
                log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while transitioning issue.",
                error_code="timeout",
                issue_key=issue_key,
                transitioned=False,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                issue_key=issue_key,
                transitioned=False,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                issue_key=issue_key,
                transitioned=False,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                issue_key=issue_key,
                transitioned=False,
            )

        # 204 No Content = success
        if response.status_code == 204:
            new_status = match["to_status"] or match["name"]
            self.status = f"Transitioned {issue_key} to '{new_status}'"
            return Data(
                data={
                    "issue_key": issue_key,
                    "transitioned": True,
                    "new_status": new_status,
                }
            )

        msg = parse_jira_error(response)
        code = error_code_from_status(response.status_code)
        return build_error_response(
            msg,
            error_code=code,
            issue_key=issue_key,
            transitioned=False,
        )

    # ------------------------------------------------------------------
    # Tool building (Agent integration)
    # ------------------------------------------------------------------

    def build_tool(self) -> list:
        """Build and return the transition tools for Agent use."""
        return self._build_tools()

    async def _get_tools(self):
        """Return both tools with proper names and tags."""
        tools = self._build_tools()
        for t in tools:
            if not t.tags:
                t.tags = [t.name]
        return tools

    def _build_tools(self) -> list[StructuredTool]:
        """Construct the two StructuredTool objects."""

        # --- Schema definitions -------------------------------------------

        class GetTransitionsInput(BaseModel):
            """Input schema for cg_jira_get_transitions."""

            issue_key: str = Field(
                description="Jira issue key (e.g. PROJ-123)."
            )

        class TransitionIssueInput(BaseModel):
            """Input schema for cg_jira_transition_issue."""

            issue_key: str = Field(
                description="Jira issue key (e.g. PROJ-123)."
            )
            transition_name: str = Field(
                description=(
                    "Name of the target transition (e.g. 'In Progress', "
                    "'Done'). Case-insensitive."
                )
            )
            comment: str = Field(
                default="",
                description="Optional comment to add when transitioning.",
            )

        # --- Closure functions that call private methods ------------------

        def _get_transitions_fn(issue_key: str) -> str:
            result = self._get_transitions(issue_key)
            if result.data.get("error"):
                return (
                    f"Error fetching transitions for {issue_key}: "
                    f"{result.data['error']}"
                )
            current = result.data.get("current_status", "unknown")
            transitions = result.data.get("transitions", [])
            names = [
                f"{t['name']} -> {t['to_status']}" for t in transitions
            ]
            return (
                f"Issue {issue_key} (status: {current}) has "
                f"{len(transitions)} available transition(s): "
                + "; ".join(names)
            )

        def _transition_issue_fn(
            issue_key: str,
            transition_name: str,
            comment: str = "",
        ) -> str:
            result = self._transition_issue(
                issue_key, transition_name, comment
            )
            if result.data.get("error"):
                return (
                    f"Error transitioning {issue_key}: "
                    f"{result.data['error']}"
                )
            new_status = result.data.get("new_status", "")
            return (
                f"Successfully transitioned {issue_key} to '{new_status}'."
            )

        # --- Build tools --------------------------------------------------

        get_tool = StructuredTool.from_function(
            name="cg_jira_get_transitions",
            description=(
                "Get the available status transitions for a Jira issue. "
                "Call this to discover which transitions are possible "
                "before attempting to move an issue to a new status."
            ),
            args_schema=GetTransitionsInput,
            func=_get_transitions_fn,
            return_direct=False,
            tags=["cg_jira_get_transitions"],
        )

        transition_tool = StructuredTool.from_function(
            name="cg_jira_transition_issue",
            description=(
                "Move a Jira issue to a new status by transition name "
                "(case-insensitive). The component resolves the name to "
                "a transition ID internally. If the transition name is "
                "invalid, an error is returned listing all available "
                "transitions."
            ),
            args_schema=TransitionIssueInput,
            func=_transition_issue_fn,
            return_direct=False,
            tags=["cg_jira_transition_issue"],
        )

        self.status = "Tools created"
        return [get_tool, transition_tool]
