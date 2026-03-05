"""CG-Jira Users Component

Search users, get current user info, and find assignable users
in Jira Cloud. Exposes 3 tools for Agent use.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from langflow.io import DataInput, MessageTextInput, StrInput
from langflow.schema.data import Data

from lfx.components.chez_antoine.cg_jira_utils import (
    build_error_response,
    error_code_from_status,
    extract_auth,
    extract_user,
    jira_request,
    parse_jira_error,
)

if TYPE_CHECKING:
    pass


class CGJiraUsersComponent(LCToolComponent):
    """Search, identify, and list Jira Cloud users.

    Provides three tools:

    - **cg_jira_search_user** -- Find a user by email or display name.
    - **cg_jira_get_myself** -- Get the authenticated user's info.
    - **cg_jira_find_assignable** -- List users assignable to a project.

    **Authentication:** Connect a CG-JiraAuth component to the
    ``auth_credentials`` input.
    """

    display_name = "CG-Jira Users"
    description = (
        "Search Jira users by email/name, get the current authenticated user, "
        "and find users assignable to a project."
    )
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-users/"
    icon = "Jira"
    name = "CGJiraUsers"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Connect a CG-JiraAuth component to provide credentials.",
            required=True,
        ),
        MessageTextInput(
            name="query",
            display_name="Search Query",
            info="Email address or display name to search for.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="project_key",
            display_name="Project Key",
            info="Jira project key for assignable-user lookup (e.g. PROJ).",
            required=False,
            tool_mode=True,
        ),
    ]

    # Uses default LCToolComponent outputs (api_run_model, api_build_tool)

    # ------------------------------------------------------------------
    # run_model -- default deterministic output (delegates to search_user)
    # ------------------------------------------------------------------

    def run_model(self) -> Data:
        """Execute a user search as the default flow action.

        Returns:
            Data with search results or error information.
        """
        query = self.query if self.query else ""
        if hasattr(query, "text"):
            query = query.text
        query = str(query).strip()

        if not query:
            return build_error_response(
                error="Query is required for user search.",
                error_code="validation_error",
                query="",
                users=[],
                count=0,
            )

        return self._search_user(query)

    # ------------------------------------------------------------------
    # Private tool methods
    # ------------------------------------------------------------------

    def _search_user(self, query: str) -> Data:
        """Find Jira users matching *query* (email or display name).

        Args:
            query: Email address or display name to search.

        Returns:
            Data with ``query``, ``users`` list, and ``count``.
        """
        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                error=str(exc),
                error_code="auth_failed",
                query=query,
                users=[],
                count=0,
            )

        url = f"{auth['base_url']}/rest/api/3/user/search"

        try:
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                params={"query": query},
                log=self.log,
            )
        except Exception as exc:
            return build_error_response(
                error=str(exc),
                error_code="connection_error",
                query=query,
                users=[],
                count=0,
            )

        if response.status_code != 200:
            error_msg = parse_jira_error(response)
            return build_error_response(
                error=error_msg,
                error_code=error_code_from_status(response.status_code),
                query=query,
                users=[],
                count=0,
            )

        raw_users = response.json()  # flat array
        users = [extract_user(u) for u in raw_users if u]
        users = [u for u in users if u is not None]

        self.status = f"Found {len(users)} user(s)"
        return Data(data={
            "query": query,
            "users": users,
            "count": len(users),
        })

    def _get_myself(self) -> Data:
        """Get the current authenticated user's information.

        Returns:
            Data with ``account_id``, ``display_name``, ``email``,
            ``active``, and ``timezone``.
        """
        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                error=str(exc),
                error_code="auth_failed",
                account_id=None,
                display_name=None,
                email=None,
                active=None,
                timezone=None,
            )

        url = f"{auth['base_url']}/rest/api/3/myself"

        try:
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                log=self.log,
            )
        except Exception as exc:
            return build_error_response(
                error=str(exc),
                error_code="connection_error",
                account_id=None,
                display_name=None,
                email=None,
                active=None,
                timezone=None,
            )

        if response.status_code != 200:
            error_msg = parse_jira_error(response)
            return build_error_response(
                error=error_msg,
                error_code=error_code_from_status(response.status_code),
                account_id=None,
                display_name=None,
                email=None,
                active=None,
                timezone=None,
            )

        raw = response.json()  # single user object
        user = extract_user(raw) or {}

        # Include timezone from the raw response (not extracted by extract_user)
        user["timezone"] = raw.get("timeZone", "")

        self.status = f"Authenticated as {user.get('display_name', 'unknown')}"
        return Data(data=user)

    def _find_assignable(self, project_key: str, query: str = "") -> Data:
        """Find users assignable to issues in a Jira project.

        Args:
            project_key: Jira project key (e.g. ``PROJ``).
            query: Optional filter by name or email.

        Returns:
            Data with ``project_key``, ``users`` list, and ``count``.
        """
        if not project_key or not project_key.strip():
            return build_error_response(
                error="project_key is required.",
                error_code="validation_error",
                project_key="",
                users=[],
                count=0,
            )

        project_key = project_key.strip()

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                error=str(exc),
                error_code="auth_failed",
                project_key=project_key,
                users=[],
                count=0,
            )

        url = f"{auth['base_url']}/rest/api/3/user/assignable/search"
        params: dict = {"project": project_key}
        if query and query.strip():
            params["query"] = query.strip()

        try:
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                params=params,
                log=self.log,
            )
        except Exception as exc:
            return build_error_response(
                error=str(exc),
                error_code="connection_error",
                project_key=project_key,
                users=[],
                count=0,
            )

        if response.status_code != 200:
            error_msg = parse_jira_error(response)
            return build_error_response(
                error=error_msg,
                error_code=error_code_from_status(response.status_code),
                project_key=project_key,
                users=[],
                count=0,
            )

        raw_users = response.json()  # flat array
        users = [extract_user(u) for u in raw_users if u]
        users = [u for u in users if u is not None]

        self.status = f"Found {len(users)} assignable user(s)"
        return Data(data={
            "project_key": project_key,
            "users": users,
            "count": len(users),
        })

    # ------------------------------------------------------------------
    # Tool wiring
    # ------------------------------------------------------------------

    def build_tool(self) -> list:
        """Build and return the user tools for Agent use."""
        return self._build_all_tools()

    async def _get_tools(self):
        """Return all three user tools for Agent use."""
        return self._build_all_tools()

    def _build_all_tools(self) -> list:
        """Build the three StructuredTool instances.

        Returns:
            List of StructuredTool objects.
        """

        # -- Arg schemas -----------------------------------------------

        class SearchUserInput(BaseModel):
            """Input schema for cg_jira_search_user."""

            query: str = Field(
                description="Email address or display name to search for in Jira."
            )

        class GetMyselfInput(BaseModel):
            """Input schema for cg_jira_get_myself (no arguments)."""

            pass

        class FindAssignableInput(BaseModel):
            """Input schema for cg_jira_find_assignable."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )
            query: str = Field(
                default="",
                description="Optional filter by user name or email.",
            )

        # -- Closures --------------------------------------------------

        def _do_search_user(query: str) -> str:
            result = self._search_user(query)
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return str(result.data)

        def _do_get_myself() -> str:
            result = self._get_myself()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return str(result.data)

        def _do_find_assignable(project_key: str, query: str = "") -> str:
            result = self._find_assignable(project_key, query)
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return str(result.data)

        # -- Tool construction -----------------------------------------

        search_tool = StructuredTool.from_function(
            name="cg_jira_search_user",
            description=(
                "Search for a Jira user by email address or display name. "
                "Returns matching users with their account IDs. Use this to "
                "resolve an email to a Jira accountId."
            ),
            args_schema=SearchUserInput,
            func=_do_search_user,
            return_direct=False,
            tags=["cg_jira_search_user"],
        )

        myself_tool = StructuredTool.from_function(
            name="cg_jira_get_myself",
            description=(
                "Get information about the currently authenticated Jira user. "
                "Returns account ID, display name, email, and timezone. "
                "Useful for validating credentials or identifying the service account."
            ),
            args_schema=GetMyselfInput,
            func=_do_get_myself,
            return_direct=False,
            tags=["cg_jira_get_myself"],
        )

        assignable_tool = StructuredTool.from_function(
            name="cg_jira_find_assignable",
            description=(
                "Find users who can be assigned to issues in a specific Jira "
                "project. Only returns users with the 'Assignable User' "
                "permission. Optionally filter by name or email."
            ),
            args_schema=FindAssignableInput,
            func=_do_find_assignable,
            return_direct=False,
            tags=["cg_jira_find_assignable"],
        )

        self.status = "3 tools created"
        return [search_tool, myself_tool, assignable_tool]
