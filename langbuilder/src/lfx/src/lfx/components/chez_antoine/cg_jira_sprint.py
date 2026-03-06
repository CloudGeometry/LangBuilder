"""CG-Jira Sprint Component

Board discovery, sprint management, backlog access, and issue movement
using the Jira Agile REST API (``/rest/agile/1.0/``).

Exposes six tools that an Agent can use to inspect boards, sprints,
sprint issues, the backlog, and to move issues between sprints.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.io import DataInput, IntInput, MessageTextInput, StrInput
from lfx.schema.data import Data

from lfx.components.chez_antoine.cg_jira_utils import (
    build_error_response,
    error_code_from_status,
    extract_auth,
    jira_request,
    parse_jira_error,
    simplify_issue,
)

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Agile API base path
# ---------------------------------------------------------------------------

AGILE_API = "/rest/agile/1.0"


class CGJiraSprintComponent(LCToolComponent):
    """Board discovery, sprint lifecycle, backlog, and issue movement.

    Exposes six tools backed by the Jira **Agile REST API**
    (``/rest/agile/1.0/``):

    1. **cg_jira_find_board** -- find board(s) for a project.
    2. **cg_jira_get_active_sprint** -- get active sprint(s) for a board.
    3. **cg_jira_get_sprint_issues** -- get all issues in a sprint.
    4. **cg_jira_list_sprints** -- list sprints for a board (with state
       filter).
    5. **cg_jira_get_backlog** -- get backlog issues for a board.
    6. **cg_jira_move_to_sprint** -- move issues into a sprint.

    **Authentication:** Connect a CG-JiraAuth component to the *Jira Auth*
    input.  Credentials are shared across all CG-Jira components in the
    flow.
    """

    display_name = "CG-Jira Sprint"
    description = (
        "Board discovery, sprint management, backlog access, and issue "
        "movement via the Jira Agile REST API."
    )
    documentation = (
        "https://developer.atlassian.com/cloud/jira/software/rest/intro/"
    )
    icon = "Jira"
    name = "CGJiraSprint"

    inputs = [
        # Auth ----------------------------------------------------------
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Connect a CG-JiraAuth component to provide credentials.",
            required=True,
        ),
        # Agent-passable inputs -----------------------------------------
        StrInput(
            name="project_key",
            display_name="Project Key",
            info="Jira project key used to find boards (e.g. PROJ).",
            required=False,
            tool_mode=True,
        ),
        IntInput(
            name="board_id",
            display_name="Board ID",
            info="Agile board ID. Use cg_jira_find_board to discover it.",
            required=False,
            tool_mode=True,
        ),
        IntInput(
            name="sprint_id",
            display_name="Sprint ID",
            info="Sprint ID. Use cg_jira_get_active_sprint to discover it.",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="issue_keys",
            display_name="Issue Keys",
            info="Comma-separated issue keys for move_to_sprint (e.g. PROJ-1,PROJ-2).",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="sprint_state",
            display_name="Sprint State Filter",
            info="Filter for list_sprints: 'active', 'closed', 'future', or comma-separated combination.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="fields",
            display_name="Fields",
            info="Comma-separated Jira fields to request (optional, for get_sprint_issues).",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum results per page (default 50).",
            value=50,
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        # Configuration (not tool_mode) ---------------------------------
        StrInput(
            name="story_points_field",
            display_name="Story Points Field",
            info="Custom field ID for story points. Varies per Jira instance.",
            value="customfield_10016",
            required=False,
            advanced=True,
        ),
    ]

    # Uses default LCToolComponent outputs (api_run_model, api_build_tool)

    # ------------------------------------------------------------------
    # run_model  (deterministic / flow-edge execution)
    # ------------------------------------------------------------------

    def run_model(self) -> Data:
        """Execute the component's main logic.

        When invoked via a flow edge (non-agent), the component tries to
        determine which action to take based on which inputs are populated.
        """
        # If issue_keys and sprint_id => move_to_sprint
        issue_keys = str(self.issue_keys).strip() if self.issue_keys else ""
        sprint_id = self.sprint_id if self.sprint_id else None
        board_id = self.board_id if self.board_id else None
        project_key = str(self.project_key).strip() if self.project_key else ""

        if issue_keys and sprint_id:
            return self._move_to_sprint(sprint_id, issue_keys)
        if sprint_id:
            fields = str(self.fields).strip() if self.fields else ""
            max_results = self.max_results or 50
            sp_field = str(self.story_points_field).strip() if self.story_points_field else "customfield_10016"
            return self._get_sprint_issues(sprint_id, fields, max_results, sp_field)
        if board_id:
            state = str(self.sprint_state).strip() if self.sprint_state else ""
            if state:
                return self._list_sprints(board_id, state)
            return self._get_active_sprint(board_id)
        if project_key:
            return self._find_board(project_key)

        return build_error_response(
            "Provide at least project_key, board_id, or sprint_id to determine the action.",
            error_code="validation_error",
        )

    # ------------------------------------------------------------------
    # 1. Find Board
    # ------------------------------------------------------------------

    def _find_board(self, project_key: str) -> Data:
        """Find board(s) for a project.

        Endpoint: ``GET /rest/agile/1.0/board?projectKeyOrId={key}``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = f"{auth['base_url']}{AGILE_API}/board"
        params = {"projectKeyOrId": project_key}

        try:
            self.status = f"Finding boards for {project_key}..."
            response = jira_request(
                "GET", url, auth["headers"], params=params, log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while finding boards.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(str(exc), error_code="rate_limited")
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code)

        data = response.json()
        values = data.get("values", [])

        boards = []
        for b in values:
            location = b.get("location") or {}
            boards.append({
                "id": b.get("id"),
                "name": b.get("name", ""),
                "type": b.get("type", ""),
                "project_key": location.get("projectKey", project_key),
            })

        self.status = f"Found {len(boards)} board(s) for {project_key}"
        return Data(data={"boards": boards})

    # ------------------------------------------------------------------
    # 2. Get Active Sprint
    # ------------------------------------------------------------------

    def _get_active_sprint(self, board_id: int) -> Data:
        """Get active sprint(s) for a board.

        Endpoint: ``GET /rest/agile/1.0/board/{boardId}/sprint?state=active``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc), error_code="auth_failed", board_id=board_id,
            )

        url = f"{auth['base_url']}{AGILE_API}/board/{board_id}/sprint"
        params = {"state": "active"}

        try:
            self.status = f"Fetching active sprint for board {board_id}..."
            response = jira_request(
                "GET", url, auth["headers"], params=params, log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out.", error_code="timeout", board_id=board_id,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                board_id=board_id,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited", board_id=board_id,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                board_id=board_id,
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code, board_id=board_id)

        data = response.json()
        values = data.get("values", [])

        sprints = []
        for s in values:
            sprints.append({
                "id": s.get("id"),
                "name": s.get("name", ""),
                "state": s.get("state", ""),
                "start_date": s.get("startDate", ""),
                "end_date": s.get("endDate", ""),
                "goal": s.get("goal", ""),
            })

        self.status = f"Found {len(sprints)} active sprint(s) for board {board_id}"
        return Data(data={"board_id": board_id, "sprints": sprints})

    # ------------------------------------------------------------------
    # 3. Get Sprint Issues
    # ------------------------------------------------------------------

    def _get_sprint_issues(
        self,
        sprint_id: int,
        fields: str = "",
        max_results: int = 50,
        story_points_field: str = "customfield_10016",
    ) -> Data:
        """Get all issues in a sprint with pagination.

        Endpoint: ``GET /rest/agile/1.0/sprint/{sprintId}/issue``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc), error_code="auth_failed", sprint_id=sprint_id,
            )

        url = f"{auth['base_url']}{AGILE_API}/sprint/{sprint_id}/issue"
        max_results = max(1, min(100, max_results))

        params: dict = {"maxResults": max_results, "startAt": 0}
        if fields:
            params["fields"] = fields

        all_issues: list[dict] = []
        total = 0

        try:
            self.status = f"Fetching issues for sprint {sprint_id}..."
            while True:
                response = jira_request(
                    "GET", url, auth["headers"], params=params, log=self.log,
                )

                if response.status_code != 200:
                    msg = parse_jira_error(response)
                    code = error_code_from_status(response.status_code)
                    return build_error_response(
                        msg, error_code=code, sprint_id=sprint_id,
                    )

                data = response.json()
                total = data.get("total", 0)
                issues = data.get("issues", [])

                for issue in issues:
                    simplified = simplify_issue(issue)
                    raw_fields = issue.get("fields", {})
                    simplified["story_points"] = raw_fields.get(
                        story_points_field
                    )
                    all_issues.append(simplified)

                # Check if we have all issues
                if params["startAt"] + len(issues) >= total:
                    break
                params["startAt"] += len(issues)

        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out.", error_code="timeout", sprint_id=sprint_id,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                sprint_id=sprint_id,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited", sprint_id=sprint_id,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                sprint_id=sprint_id,
            )

        self.status = f"Fetched {len(all_issues)} issue(s) for sprint {sprint_id}"
        return Data(
            data={
                "sprint_id": sprint_id,
                "total": total,
                "issues": all_issues,
            }
        )

    # ------------------------------------------------------------------
    # 4. List Sprints
    # ------------------------------------------------------------------

    def _list_sprints(self, board_id: int, state: str = "") -> Data:
        """List sprints for a board with optional state filter.

        Endpoint: ``GET /rest/agile/1.0/board/{boardId}/sprint``

        Uses ``isLast`` for pagination termination (``total`` may be
        missing due to a known Jira bug).
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc), error_code="auth_failed", board_id=board_id,
            )

        url = f"{auth['base_url']}{AGILE_API}/board/{board_id}/sprint"
        params: dict = {"maxResults": 50, "startAt": 0}
        if state:
            params["state"] = state

        all_sprints: list[dict] = []

        try:
            self.status = f"Listing sprints for board {board_id}..."
            while True:
                response = jira_request(
                    "GET", url, auth["headers"], params=params, log=self.log,
                )

                if response.status_code != 200:
                    msg = parse_jira_error(response)
                    code = error_code_from_status(response.status_code)
                    return build_error_response(
                        msg, error_code=code, board_id=board_id,
                    )

                data = response.json()
                values = data.get("values", [])

                for s in values:
                    all_sprints.append({
                        "id": s.get("id"),
                        "name": s.get("name", ""),
                        "state": s.get("state", ""),
                        "start_date": s.get("startDate", ""),
                        "end_date": s.get("endDate", ""),
                        "complete_date": s.get("completeDate", ""),
                    })

                # Use isLast for pagination (total may be missing)
                if data.get("isLast", True):
                    break
                params["startAt"] += len(values)

        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out.", error_code="timeout", board_id=board_id,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                board_id=board_id,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited", board_id=board_id,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                board_id=board_id,
            )

        self.status = f"Found {len(all_sprints)} sprint(s) for board {board_id}"
        return Data(data={"board_id": board_id, "sprints": all_sprints})

    # ------------------------------------------------------------------
    # 5. Get Backlog
    # ------------------------------------------------------------------

    def _get_backlog(
        self,
        board_id: int,
        max_results: int = 50,
        story_points_field: str = "customfield_10016",
    ) -> Data:
        """Get backlog issues for a board with pagination.

        Endpoint: ``GET /rest/agile/1.0/board/{boardId}/backlog``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc), error_code="auth_failed", board_id=board_id,
            )

        url = f"{auth['base_url']}{AGILE_API}/board/{board_id}/backlog"
        max_results = max(1, min(100, max_results))

        params: dict = {"maxResults": max_results, "startAt": 0}

        all_issues: list[dict] = []
        total = 0

        try:
            self.status = f"Fetching backlog for board {board_id}..."
            while True:
                response = jira_request(
                    "GET", url, auth["headers"], params=params, log=self.log,
                )

                if response.status_code != 200:
                    msg = parse_jira_error(response)
                    code = error_code_from_status(response.status_code)
                    return build_error_response(
                        msg, error_code=code, board_id=board_id,
                    )

                data = response.json()
                total = data.get("total", 0)
                issues = data.get("issues", [])

                for issue in issues:
                    simplified = simplify_issue(issue)
                    raw_fields = issue.get("fields", {})
                    simplified["story_points"] = raw_fields.get(
                        story_points_field
                    )
                    all_issues.append(simplified)

                # Check if we have all issues
                if params["startAt"] + len(issues) >= total:
                    break
                params["startAt"] += len(issues)

        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out.", error_code="timeout", board_id=board_id,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                board_id=board_id,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited", board_id=board_id,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                board_id=board_id,
            )

        self.status = f"Fetched {len(all_issues)} backlog issue(s) for board {board_id}"
        return Data(
            data={
                "board_id": board_id,
                "total": total,
                "issues": all_issues,
            }
        )

    # ------------------------------------------------------------------
    # 6. Move to Sprint
    # ------------------------------------------------------------------

    def _move_to_sprint(self, sprint_id: int, issue_keys: str) -> Data:
        """Move issues into a sprint.

        Endpoint: ``POST /rest/agile/1.0/sprint/{sprintId}/issue``

        Accepts a comma-separated string of issue keys. Max 50 per call.
        Returns 204 No Content on success; the component constructs a
        meaningful response.
        """
        import requests as _requests

        keys = [k.strip() for k in issue_keys.split(",") if k.strip()]
        if not keys:
            return build_error_response(
                "No issue keys provided.",
                error_code="validation_error",
                sprint_id=sprint_id,
            )

        if len(keys) > 50:
            return build_error_response(
                f"Too many issue keys ({len(keys)}). Maximum 50 per request.",
                error_code="validation_error",
                sprint_id=sprint_id,
            )

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(
                str(exc), error_code="auth_failed", sprint_id=sprint_id,
            )

        url = f"{auth['base_url']}{AGILE_API}/sprint/{sprint_id}/issue"
        body = {"issues": keys}

        try:
            self.status = f"Moving {len(keys)} issue(s) to sprint {sprint_id}..."
            response = jira_request(
                "POST",
                url,
                auth["headers"],
                json=body,
                log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out.", error_code="timeout", sprint_id=sprint_id,
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
                sprint_id=sprint_id,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited", sprint_id=sprint_id,
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}",
                error_code="api_error",
                sprint_id=sprint_id,
            )

        # 204 No Content = success
        if response.status_code == 204:
            self.status = f"Moved {len(keys)} issue(s) to sprint {sprint_id}"
            return Data(
                data={
                    "sprint_id": sprint_id,
                    "moved": keys,
                    "count": len(keys),
                }
            )

        msg = parse_jira_error(response)
        code = error_code_from_status(response.status_code)
        return build_error_response(msg, error_code=code, sprint_id=sprint_id)

    # ------------------------------------------------------------------
    # Tool building (Agent integration)
    # ------------------------------------------------------------------

    def build_tool(self) -> list:
        """Build and return the sprint tools for Agent use."""
        return self._build_tools()

    async def _get_tools(self):
        """Return all six tools with proper names and tags."""
        tools = self._build_tools()
        for t in tools:
            if not t.tags:
                t.tags = [t.name]
        return tools

    def _build_tools(self) -> list[StructuredTool]:
        """Construct the six StructuredTool objects."""

        # --- Schema definitions ----------------------------------------

        class FindBoardInput(BaseModel):
            """Input schema for cg_jira_find_board."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )

        class GetActiveSprintInput(BaseModel):
            """Input schema for cg_jira_get_active_sprint."""

            board_id: int = Field(
                description="Agile board ID. Use cg_jira_find_board to discover it."
            )

        class GetSprintIssuesInput(BaseModel):
            """Input schema for cg_jira_get_sprint_issues."""

            sprint_id: int = Field(
                description="Sprint ID. Use cg_jira_get_active_sprint to discover it."
            )
            fields: str = Field(
                default="",
                description="Comma-separated Jira fields to include (optional).",
            )
            max_results: int = Field(
                default=50,
                description="Max issues per page (1-100). Pagination is automatic.",
            )
            story_points_field: str = Field(
                default="customfield_10016",
                description="Custom field ID for story points (varies per instance).",
            )

        class ListSprintsInput(BaseModel):
            """Input schema for cg_jira_list_sprints."""

            board_id: int = Field(
                description="Agile board ID."
            )
            state: str = Field(
                default="",
                description=(
                    "Filter by state: 'active', 'closed', 'future', "
                    "or comma-separated combination (e.g. 'active,future'). "
                    "Leave empty for all sprints."
                ),
            )

        class GetBacklogInput(BaseModel):
            """Input schema for cg_jira_get_backlog."""

            board_id: int = Field(
                description="Agile board ID."
            )
            max_results: int = Field(
                default=50,
                description="Max issues per page (1-100). Pagination is automatic.",
            )
            story_points_field: str = Field(
                default="customfield_10016",
                description="Custom field ID for story points (varies per instance).",
            )

        class MoveToSprintInput(BaseModel):
            """Input schema for cg_jira_move_to_sprint."""

            sprint_id: int = Field(
                description="Target sprint ID (must be active or future)."
            )
            issue_keys: str = Field(
                description=(
                    "Comma-separated issue keys to move (e.g. 'PROJ-1,PROJ-2'). "
                    "Max 50 per request."
                ),
            )

        # --- Closure functions -----------------------------------------

        def _find_board_fn(project_key: str) -> str:
            result = self._find_board(project_key)
            if result.data.get("error"):
                return f"Error finding boards: {result.data['error']}"
            boards = result.data.get("boards", [])
            if not boards:
                return f"No boards found for project {project_key}."
            lines = [
                f"Found {len(boards)} board(s) for {project_key}:"
            ]
            for b in boards:
                lines.append(
                    f"  - {b['name']} (id={b['id']}, type={b['type']})"
                )
            return "\n".join(lines)

        def _get_active_sprint_fn(board_id: int) -> str:
            result = self._get_active_sprint(board_id)
            if result.data.get("error"):
                return f"Error getting active sprint: {result.data['error']}"
            sprints = result.data.get("sprints", [])
            if not sprints:
                return f"No active sprint for board {board_id}."
            lines = [
                f"Board {board_id} has {len(sprints)} active sprint(s):"
            ]
            for s in sprints:
                goal = f" | Goal: {s['goal']}" if s.get("goal") else ""
                lines.append(
                    f"  - {s['name']} (id={s['id']}, "
                    f"{s['start_date']} to {s['end_date']}{goal})"
                )
            return "\n".join(lines)

        def _get_sprint_issues_fn(
            sprint_id: int,
            fields: str = "",
            max_results: int = 50,
            story_points_field: str = "customfield_10016",
        ) -> str:
            sp_field = story_points_field or (
                str(self.story_points_field).strip()
                if self.story_points_field
                else "customfield_10016"
            )
            result = self._get_sprint_issues(
                sprint_id, fields, max_results, sp_field,
            )
            if result.data.get("error"):
                return f"Error getting sprint issues: {result.data['error']}"
            total = result.data.get("total", 0)
            issues = result.data.get("issues", [])
            lines = [f"Sprint {sprint_id}: {total} issue(s)."]
            for i in issues:
                pts = i.get("story_points")
                pts_str = f" [{pts} pts]" if pts is not None else ""
                lines.append(
                    f"  - {i['key']}: {i['summary']} "
                    f"({i['status']}){pts_str}"
                )
            return "\n".join(lines)

        def _list_sprints_fn(board_id: int, state: str = "") -> str:
            result = self._list_sprints(board_id, state)
            if result.data.get("error"):
                return f"Error listing sprints: {result.data['error']}"
            sprints = result.data.get("sprints", [])
            if not sprints:
                filter_msg = f" (state={state})" if state else ""
                return f"No sprints found for board {board_id}{filter_msg}."
            lines = [
                f"Board {board_id}: {len(sprints)} sprint(s):"
            ]
            for s in sprints:
                complete = (
                    f", completed {s['complete_date']}"
                    if s.get("complete_date")
                    else ""
                )
                lines.append(
                    f"  - {s['name']} (id={s['id']}, state={s['state']}, "
                    f"{s['start_date']} to {s['end_date']}{complete})"
                )
            return "\n".join(lines)

        def _get_backlog_fn(
            board_id: int,
            max_results: int = 50,
            story_points_field: str = "customfield_10016",
        ) -> str:
            sp_field = story_points_field or (
                str(self.story_points_field).strip()
                if self.story_points_field
                else "customfield_10016"
            )
            result = self._get_backlog(board_id, max_results, sp_field)
            if result.data.get("error"):
                return f"Error getting backlog: {result.data['error']}"
            total = result.data.get("total", 0)
            issues = result.data.get("issues", [])
            lines = [f"Board {board_id} backlog: {total} issue(s)."]
            for i in issues:
                pts = i.get("story_points")
                pts_str = f" [{pts} pts]" if pts is not None else ""
                lines.append(
                    f"  - {i['key']}: {i['summary']} "
                    f"({i['status']}, {i['priority']}){pts_str}"
                )
            return "\n".join(lines)

        def _move_to_sprint_fn(sprint_id: int, issue_keys: str) -> str:
            result = self._move_to_sprint(sprint_id, issue_keys)
            if result.data.get("error"):
                return f"Error moving issues: {result.data['error']}"
            moved = result.data.get("moved", [])
            count = result.data.get("count", 0)
            return (
                f"Successfully moved {count} issue(s) to sprint {sprint_id}: "
                f"{', '.join(moved)}"
            )

        # --- Build tools -----------------------------------------------

        find_board_tool = StructuredTool.from_function(
            name="cg_jira_find_board",
            description=(
                "Find the Agile board(s) for a Jira project. A project can "
                "have multiple boards (Scrum, Kanban). Use this to discover "
                "the board ID needed by other sprint tools."
            ),
            args_schema=FindBoardInput,
            func=_find_board_fn,
            return_direct=False,
            tags=["cg_jira_find_board"],
        )

        get_active_sprint_tool = StructuredTool.from_function(
            name="cg_jira_get_active_sprint",
            description=(
                "Get the currently active sprint(s) for an Agile board. "
                "Returns 0, 1, or multiple active sprints (parallel sprints "
                "are possible). Use after cg_jira_find_board."
            ),
            args_schema=GetActiveSprintInput,
            func=_get_active_sprint_fn,
            return_direct=False,
            tags=["cg_jira_get_active_sprint"],
        )

        get_sprint_issues_tool = StructuredTool.from_function(
            name="cg_jira_get_sprint_issues",
            description=(
                "Get all issues in a sprint, including story points. "
                "Supports pagination automatically. Use after "
                "cg_jira_get_active_sprint to inspect sprint contents."
            ),
            args_schema=GetSprintIssuesInput,
            func=_get_sprint_issues_fn,
            return_direct=False,
            tags=["cg_jira_get_sprint_issues"],
        )

        list_sprints_tool = StructuredTool.from_function(
            name="cg_jira_list_sprints",
            description=(
                "List sprints for a board with optional state filter "
                "('active', 'closed', 'future', or comma-separated "
                "combination). Useful for velocity calculation by "
                "inspecting closed sprints."
            ),
            args_schema=ListSprintsInput,
            func=_list_sprints_fn,
            return_direct=False,
            tags=["cg_jira_list_sprints"],
        )

        get_backlog_tool = StructuredTool.from_function(
            name="cg_jira_get_backlog",
            description=(
                "Get backlog issues (not in any active or future sprint) "
                "for a board, including story points. Useful for sprint "
                "planning to see what can be pulled into the next sprint."
            ),
            args_schema=GetBacklogInput,
            func=_get_backlog_fn,
            return_direct=False,
            tags=["cg_jira_get_backlog"],
        )

        move_to_sprint_tool = StructuredTool.from_function(
            name="cg_jira_move_to_sprint",
            description=(
                "Move issues into an active or future sprint. Accepts a "
                "comma-separated list of issue keys (max 50). Use this "
                "after sprint planning to move recommended issues."
            ),
            args_schema=MoveToSprintInput,
            func=_move_to_sprint_fn,
            return_direct=False,
            tags=["cg_jira_move_to_sprint"],
        )

        self.status = "Tools created"
        return [
            find_board_tool,
            get_active_sprint_tool,
            get_sprint_issues_tool,
            list_sprints_tool,
            get_backlog_tool,
            move_to_sprint_tool,
        ]
