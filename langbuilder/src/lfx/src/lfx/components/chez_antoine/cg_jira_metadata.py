"""CG-Jira Metadata Component

Retrieve Jira project metadata: project details, fields, issue types,
components, and priorities.  Used during onboarding (validate project key,
discover custom fields) and at runtime (populate dropdowns, validate inputs).

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from langflow.io import DataInput, MessageTextInput
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


class CGJiraMetadataComponent(LCToolComponent):
    """Retrieve Jira project metadata for configuration and validation.

    Exposes five tools:

    1. **cg_jira_get_project** -- get project details and validate a project key.
    2. **cg_jira_get_fields** -- list all fields (system + custom) and auto-detect
       the story points custom field.
    3. **cg_jira_get_issue_types** -- get available issue types with their valid
       workflow statuses.
    4. **cg_jira_get_components** -- get project components (team/area labels).
    5. **cg_jira_get_priorities** -- get available priority levels.

    **Authentication:** Connect a CG-JiraAuth component to the *Jira Auth*
    input.  Credentials are shared across all CG-Jira components in the flow.
    """

    display_name = "CG-Jira Metadata"
    description = (
        "Retrieve Jira project metadata: project details, fields, "
        "issue types, components, and priorities."
    )
    documentation = (
        "https://developer.atlassian.com/cloud/jira/platform/rest/v3/"
        "api-group-projects/#api-rest-api-3-project-projectidorkey-get"
    )
    icon = "Jira"
    name = "CGJiraMetadata"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Connect a CG-JiraAuth component to provide credentials.",
            required=True,
        ),
        MessageTextInput(
            name="project_key",
            display_name="Project Key",
            info="Jira project key (e.g. PROJ). Required for project, issue types, and components tools.",
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

        When called via a flow edge, returns project details if
        ``project_key`` is provided.
        """
        project_key = str(self.project_key).strip() if self.project_key else ""
        if not project_key:
            return build_error_response(
                "project_key is required.",
                error_code="validation_error",
            )
        return self._get_project(project_key)

    # ------------------------------------------------------------------
    # Private implementation methods
    # ------------------------------------------------------------------

    def _get_project(self, project_key: str) -> Data:
        """Get project details and validate the project key.

        Endpoint: ``GET /rest/api/3/project/{projectIdOrKey}``
        Uses ``expand=issueTypes`` to include issue types inline.
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = f"{auth['base_url']}/rest/api/3/project/{project_key}"

        try:
            self.status = f"Fetching project {project_key}..."
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                params={"expand": "issueTypes"},
                log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching project.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited",
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            if response.status_code == 404:
                msg = (
                    f"Project '{project_key}' not found. "
                    "Please check the project key in your Jira instance."
                )
            return build_error_response(msg, error_code=code)

        project = response.json()

        # Extract issue types from the expanded response
        raw_issue_types = project.get("issueTypes", [])
        issue_types = [
            {
                "id": str(it.get("id", "")),
                "name": it.get("name", ""),
                "subtask": it.get("subtask", False),
            }
            for it in raw_issue_types
        ]

        result = {
            "key": project.get("key", ""),
            "id": str(project.get("id", "")),
            "name": project.get("name", ""),
            "project_type": project.get("projectTypeKey", ""),
            "lead": extract_user(project.get("lead") or {}),
            "url": f"{auth['base_url']}/browse/{project.get('key', '')}",
            "issue_types": issue_types,
        }

        self.status = f"Project {result['key']}: {result['name']}"
        return Data(data=result)

    def _get_fields(self) -> Data:
        """Get all fields (system + custom) for the Jira instance.

        Endpoint: ``GET /rest/api/3/field``

        Auto-detects the story points custom field by searching for a
        field whose name contains "story point" (case-insensitive).
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = f"{auth['base_url']}/rest/api/3/field"

        try:
            self.status = "Fetching fields..."
            response = jira_request(
                "GET", url, auth["headers"], log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching fields.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited",
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code)

        # Response is a flat array, NOT { fields: [...] }
        raw_fields = response.json()

        story_points_field_id: str | None = None
        fields = []
        for f in raw_fields:
            schema = f.get("schema") or {}
            fields.append(
                {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "custom": f.get("custom", False),
                    "schema_type": schema.get("type", ""),
                }
            )
            # Auto-detect story points field (varies by instance):
            # "Story Points" (classic) or "Story point estimate" (team-managed)
            if "story point" in f.get("name", "").lower():
                story_points_field_id = f.get("id", "")

        result = {
            "fields": fields,
            "count": len(fields),
            "story_points_field_id": story_points_field_id,
        }

        sp_msg = (
            f", story points field: {story_points_field_id}"
            if story_points_field_id
            else ", story points field not found"
        )
        self.status = f"Found {len(fields)} field(s){sp_msg}"
        return Data(data=result)

    def _get_issue_types(self, project_key: str) -> Data:
        """Get available issue types with their valid statuses.

        Endpoint: ``GET /rest/api/3/project/{key}/statuses``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = f"{auth['base_url']}/rest/api/3/project/{project_key}/statuses"

        try:
            self.status = f"Fetching issue types for {project_key}..."
            response = jira_request(
                "GET", url, auth["headers"], log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching issue types.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited",
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code)

        # Response is a flat array, NOT { issue_types: [...] }
        raw_types = response.json()

        issue_types = []
        for it in raw_types:
            statuses = []
            for s in it.get("statuses", []):
                category = (s.get("statusCategory") or {}).get("key", "")
                statuses.append(
                    {
                        "id": str(s.get("id", "")),
                        "name": s.get("name", ""),
                        "category": category,
                    }
                )
            issue_types.append(
                {
                    "id": str(it.get("id", "")),
                    "name": it.get("name", ""),
                    "subtask": it.get("subtask", False),
                    "statuses": statuses,
                }
            )

        result = {
            "project_key": project_key,
            "issue_types": issue_types,
        }

        self.status = (
            f"Found {len(issue_types)} issue type(s) for {project_key}"
        )
        return Data(data=result)

    def _get_components(self, project_key: str) -> Data:
        """Get project components (team/area labels).

        Endpoint: ``GET /rest/api/3/project/{projectIdOrKey}/components``
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = (
            f"{auth['base_url']}/rest/api/3/project/{project_key}/components"
        )

        try:
            self.status = f"Fetching components for {project_key}..."
            response = jira_request(
                "GET", url, auth["headers"], log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching components.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited",
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code)

        # Response is a flat array, NOT { components: [...] }
        raw_components = response.json()

        components = []
        for c in raw_components:
            # lead field is optional
            lead = extract_user(c.get("lead") or {}) if c.get("lead") else None
            components.append(
                {
                    "id": str(c.get("id", "")),
                    "name": c.get("name", ""),
                    "description": c.get("description", ""),
                    "lead": lead,
                }
            )

        result = {
            "project_key": project_key,
            "components": components,
        }

        self.status = (
            f"Found {len(components)} component(s) for {project_key}"
        )
        return Data(data=result)

    def _get_priorities(self) -> Data:
        """Get available priority levels.

        Endpoint: ``GET /rest/api/3/priority``

        NOTE: This endpoint is **deprecated** but still functional.
        The replacement ``GET /rest/api/3/priority/search`` requires a
        higher OAuth scope.  Plan to migrate to ``/priority/search``
        when the OAuth scope can be increased.
        """
        import requests as _requests

        try:
            auth = extract_auth(self.auth_credentials)
        except ValueError as exc:
            return build_error_response(str(exc), error_code="auth_failed")

        url = f"{auth['base_url']}/rest/api/3/priority"

        try:
            self.status = "Fetching priorities..."
            response = jira_request(
                "GET", url, auth["headers"], log=self.log,
            )
        except _requests.exceptions.Timeout:
            return build_error_response(
                "Request timed out while fetching priorities.",
                error_code="timeout",
            )
        except _requests.exceptions.ConnectionError:
            return build_error_response(
                "Could not connect to Jira server.",
                error_code="connection_error",
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc), error_code="rate_limited",
            )
        except Exception as exc:
            return build_error_response(
                f"Unexpected error: {exc}", error_code="api_error",
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code)

        # Response is a flat array, NOT { priorities: [...] }
        raw_priorities = response.json()

        priorities = []
        for p in raw_priorities:
            priorities.append(
                {
                    "id": str(p.get("id", "")),
                    "name": p.get("name", ""),
                    "description": p.get("description", ""),
                }
            )

        result = {
            "priorities": priorities,
            "count": len(priorities),
        }

        self.status = f"Found {len(priorities)} priority level(s)"
        return Data(data=result)

    # ------------------------------------------------------------------
    # Tool building (Agent integration)
    # ------------------------------------------------------------------

    def build_tool(self) -> list:
        """Build and return the metadata tools for Agent use."""
        return self._build_tools()

    async def _get_tools(self):
        """Return all five tools with proper names and tags."""
        tools = self._build_tools()
        for t in tools:
            if not t.tags:
                t.tags = [t.name]
        return tools

    def _build_tools(self) -> list[StructuredTool]:
        """Construct the five StructuredTool objects."""

        # --- Schema definitions -------------------------------------------

        class GetProjectInput(BaseModel):
            """Input schema for cg_jira_get_project."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )

        class GetFieldsInput(BaseModel):
            """Input schema for cg_jira_get_fields."""

            # No parameters required

        class GetIssueTypesInput(BaseModel):
            """Input schema for cg_jira_get_issue_types."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )

        class GetComponentsInput(BaseModel):
            """Input schema for cg_jira_get_components."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )

        class GetPrioritiesInput(BaseModel):
            """Input schema for cg_jira_get_priorities."""

            # No parameters required

        # --- Closure functions that call private methods ------------------

        def _get_project_fn(project_key: str) -> str:
            result = self._get_project(project_key)
            if result.data.get("error"):
                return (
                    f"Error fetching project '{project_key}': "
                    f"{result.data['error']}"
                )
            return (
                f"Project {result.data['key']} ({result.data['name']}): "
                f"type={result.data['project_type']}, "
                f"id={result.data['id']}, "
                f"url={result.data['url']}, "
                f"issue_types={[it['name'] for it in result.data.get('issue_types', [])]}"
            )

        def _get_fields_fn() -> str:
            result = self._get_fields()
            if result.data.get("error"):
                return f"Error fetching fields: {result.data['error']}"
            sp = result.data.get("story_points_field_id")
            sp_msg = f"story_points_field_id={sp}" if sp else "story points field not found"
            return (
                f"Found {result.data['count']} field(s). {sp_msg}. "
                f"Custom fields: {[f['name'] for f in result.data['fields'] if f['custom']][:20]}"
            )

        def _get_issue_types_fn(project_key: str) -> str:
            result = self._get_issue_types(project_key)
            if result.data.get("error"):
                return (
                    f"Error fetching issue types for '{project_key}': "
                    f"{result.data['error']}"
                )
            types = result.data.get("issue_types", [])
            summaries = []
            for it in types:
                status_names = [s["name"] for s in it.get("statuses", [])]
                summaries.append(
                    f"{it['name']} (subtask={it['subtask']}, "
                    f"statuses={status_names})"
                )
            return (
                f"Project {project_key} has {len(types)} issue type(s): "
                + "; ".join(summaries)
            )

        def _get_components_fn(project_key: str) -> str:
            result = self._get_components(project_key)
            if result.data.get("error"):
                return (
                    f"Error fetching components for '{project_key}': "
                    f"{result.data['error']}"
                )
            components = result.data.get("components", [])
            if not components:
                return f"Project {project_key} has no components."
            names = [c["name"] for c in components]
            return (
                f"Project {project_key} has {len(components)} component(s): "
                + ", ".join(names)
            )

        def _get_priorities_fn() -> str:
            result = self._get_priorities()
            if result.data.get("error"):
                return f"Error fetching priorities: {result.data['error']}"
            priorities = result.data.get("priorities", [])
            names = [p["name"] for p in priorities]
            return (
                f"Found {result.data['count']} priority level(s): "
                + ", ".join(names)
            )

        # --- Build tools --------------------------------------------------

        get_project_tool = StructuredTool.from_function(
            name="cg_jira_get_project",
            description=(
                "Get Jira project details and validate a project key. "
                "Returns project name, type, lead, URL, and available "
                "issue types. Use this to verify a project key is valid "
                "before performing other operations."
            ),
            args_schema=GetProjectInput,
            func=_get_project_fn,
            return_direct=False,
            tags=["cg_jira_get_project"],
        )

        get_fields_tool = StructuredTool.from_function(
            name="cg_jira_get_fields",
            description=(
                "Get all fields (system and custom) for the Jira instance. "
                "Auto-detects the story points custom field ID. Use this "
                "during onboarding to discover custom field IDs for "
                "story points, epic link, sprint, etc."
            ),
            args_schema=GetFieldsInput,
            func=_get_fields_fn,
            return_direct=False,
            tags=["cg_jira_get_fields"],
        )

        get_issue_types_tool = StructuredTool.from_function(
            name="cg_jira_get_issue_types",
            description=(
                "Get available issue types for a Jira project, including "
                "their valid workflow statuses. Use this to populate issue "
                "type dropdowns or validate issue type inputs."
            ),
            args_schema=GetIssueTypesInput,
            func=_get_issue_types_fn,
            return_direct=False,
            tags=["cg_jira_get_issue_types"],
        )

        get_components_tool = StructuredTool.from_function(
            name="cg_jira_get_components",
            description=(
                "Get project components (team/area labels) for a Jira "
                "project. Use this for auto-tagging suggestions or to "
                "populate component dropdowns."
            ),
            args_schema=GetComponentsInput,
            func=_get_components_fn,
            return_direct=False,
            tags=["cg_jira_get_components"],
        )

        get_priorities_tool = StructuredTool.from_function(
            name="cg_jira_get_priorities",
            description=(
                "Get available priority levels for the Jira instance "
                "(e.g. Highest, High, Medium, Low, Lowest). Use this "
                "to validate priority values before creating or updating "
                "issues."
            ),
            args_schema=GetPrioritiesInput,
            func=_get_priorities_fn,
            return_direct=False,
            tags=["cg_jira_get_priorities"],
        )

        self.status = "Tools created"
        return [
            get_project_tool,
            get_fields_tool,
            get_issue_types_tool,
            get_components_tool,
            get_priorities_tool,
        ]
