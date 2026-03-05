"""CG-Jira Core Component

Multi-tool component providing the six foundational Jira operations:
search, create, get, update, add-comment, and get-issue-links.

All tools share authentication from CG-JiraAuth and use the shared
utility layer for ADF conversion, retry logic, and error handling.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from langflow.field_typing import Tool
from langflow.io import DataInput, FloatInput, MessageTextInput, StrInput
from langflow.schema.data import Data

from lfx.components.chez_antoine.cg_jira_utils import (
    adf_to_text,
    build_error_response,
    error_code_from_status,
    extract_auth,
    jira_request,
    parse_jira_error,
    simplify_issue,
    text_to_adf,
)

if TYPE_CHECKING:
    pass


class CGJiraCoreComponent(LCToolComponent):
    """Core Jira operations: search, create, get, update, comment, and links.

    Provides six tools that share a single authentication context from
    CG-JiraAuth. Every tool returns structured ``Data`` and never raises
    exceptions into the flow.

    **Tools:**

    1. ``cg_jira_search`` -- Search issues via JQL (cursor-based pagination)
    2. ``cg_jira_create_issue`` -- Create a new issue
    3. ``cg_jira_get_issue`` -- Retrieve a single issue by key
    4. ``cg_jira_update_issue`` -- Update fields on an existing issue
    5. ``cg_jira_add_comment`` -- Add a comment to an issue
    6. ``cg_jira_get_issue_links`` -- Get issue links (blocks, blocked by, relates to)
    """

    display_name = "CG-Jira Core"
    description = (
        "Core Jira operations: search issues (JQL), create, get, update, "
        "add comments, and get issue links. Requires CG-JiraAuth for authentication."
    )
    documentation = (
        "https://developer.atlassian.com/cloud/jira/platform/rest/v3/"
    )
    icon = "Jira"
    name = "CGJiraCore"

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    inputs = [
        # Auth -- consumed from CG-JiraAuth
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Connect a CG-JiraAuth component to provide authentication.",
            required=True,
        ),
        # Agent-passable inputs (tool_mode=True)
        MessageTextInput(
            name="jql",
            display_name="JQL Query",
            info="JQL query string for searching issues.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="issue_key",
            display_name="Issue Key",
            info="Jira issue key (e.g. PROJ-123) for get/update/comment.",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="summary",
            display_name="Summary",
            info="Issue summary / title (create or update).",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="description",
            display_name="Description",
            info="Plain-text description (auto-converted to ADF).",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="comment_body",
            display_name="Comment Body",
            info="Plain-text comment body (auto-converted to ADF).",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="project_key",
            display_name="Project Key",
            info="Jira project key for issue creation (e.g. PROJ).",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="issue_type",
            display_name="Issue Type",
            info="Issue type name (default: Task).",
            value="Task",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="priority",
            display_name="Priority",
            info="Priority name: Highest, High, Medium, Low, or Lowest.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="assignee_account_id",
            display_name="Assignee Account ID",
            info="Jira account ID of the assignee (NOT email). Use cg_jira_search_user to resolve.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="labels",
            display_name="Labels",
            info="Comma-separated labels.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        FloatInput(
            name="story_points",
            display_name="Story Points",
            info="Story-point estimate (float).",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="story_points_field",
            display_name="Story Points Field ID",
            info="Custom field ID for story points (default: customfield_10016).",
            value="customfield_10016",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="fields",
            display_name="Fields",
            info="Comma-separated field list (default *all). Used by search and get.",
            value="*all",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="expand",
            display_name="Expand",
            info="Comma-separated expand options for get_issue (e.g. changelog).",
            required=False,
            advanced=True,
        ),
    ]

    # Uses default LCToolComponent outputs (api_run_model, api_build_tool)

    # ------------------------------------------------------------------
    # Auth helper
    # ------------------------------------------------------------------

    def _extract_auth(self) -> dict:
        """Extract auth headers and base_url from the connected credential.

        Returns:
            dict with ``headers`` and ``base_url`` keys.

        Raises:
            ValueError: On missing or invalid credentials.
        """
        return extract_auth(self.auth_credentials)

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _search(
        self,
        jql: str,
        max_results: int = 50,
        fields: str = "*all",
    ) -> Data:
        """Search Jira issues using JQL with cursor-based pagination.

        Args:
            jql: JQL query string.
            max_results: Maximum results to return (capped at 100).
            fields: Comma-separated field list or ``*all``.

        Returns:
            Data with ``total``, ``count``, ``issues``, and
            ``next_page_token`` keys.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                total=0,
                count=0,
                issues=[],
                next_page_token=None,
            )

        if not jql or not jql.strip():
            return build_error_response(
                "JQL query is required.",
                error_code="validation_error",
                total=0,
                count=0,
                issues=[],
                next_page_token=None,
            )

        max_results = max(1, min(100, int(max_results)))

        fields_list = (
            ["*all"]
            if not fields or fields.strip() == "*all"
            else [f.strip() for f in fields.split(",") if f.strip()]
        )

        payload: dict[str, Any] = {
            "jql": jql.strip(),
            "maxResults": max_results,
            "fields": fields_list,
        }

        url = f"{auth['base_url']}/rest/api/3/search/jql"

        try:
            self.log(f"Searching Jira: {jql.strip()[:120]}")
            response = jira_request(
                "POST",
                url,
                auth["headers"],
                json=payload,
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                total=0,
                count=0,
                issues=[],
                next_page_token=None,
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                total=0,
                count=0,
                issues=[],
                next_page_token=None,
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(
                msg,
                error_code=code,
                total=0,
                count=0,
                issues=[],
                next_page_token=None,
            )

        body = response.json()
        raw_issues = body.get("issues", [])
        simplified = [simplify_issue(i) for i in raw_issues]
        total = body.get("total", len(raw_issues))
        next_token = body.get("nextPageToken", None)

        self.status = f"Found {total} issues (returned {len(simplified)})"
        self.log(self.status)

        return Data(
            data={
                "total": total,
                "count": len(simplified),
                "issues": simplified,
                "next_page_token": next_token,
            }
        )

    # ------------------------------------------------------------------

    def _create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str = "",
        priority: str = "",
        assignee_account_id: str = "",
        labels: str = "",
        story_points: float | None = None,
        story_points_field: str = "customfield_10016",
    ) -> Data:
        """Create a new Jira issue.

        Args:
            project_key: Target project key (e.g. ``PROJ``).
            summary: Issue title (max 255 chars).
            issue_type: Issue type name (default ``Task``).
            description: Plain-text description (converted to ADF).
            priority: Priority name (optional).
            assignee_account_id: Account ID of assignee (optional).
            labels: Comma-separated labels (optional).
            story_points: Story-point estimate (optional).
            story_points_field: Custom field ID for story points.

        Returns:
            Data with ``key``, ``id``, ``url``, ``created`` keys.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                key=None,
                id=None,
                url=None,
                created=False,
            )

        # Validate required fields
        if not project_key or not project_key.strip():
            return build_error_response(
                "project_key is required.",
                error_code="validation_error",
                key=None,
                id=None,
                url=None,
                created=False,
            )
        if not summary or not summary.strip():
            return build_error_response(
                "summary is required.",
                error_code="validation_error",
                key=None,
                id=None,
                url=None,
                created=False,
            )

        summary = summary.strip()
        if len(summary) > 255:
            self.log(f"Warning: Summary truncated from {len(summary)} to 255 characters")
            summary = summary[:252] + "..."

        fields: dict[str, Any] = {
            "project": {"key": project_key.strip()},
            "issuetype": {"name": issue_type.strip() if issue_type else "Task"},
            "summary": summary,
        }

        if description and description.strip():
            fields["description"] = text_to_adf(description.strip())

        if priority and priority.strip():
            fields["priority"] = {"name": priority.strip()}

        if assignee_account_id and assignee_account_id.strip():
            fields["assignee"] = {"id": assignee_account_id.strip()}

        if labels and labels.strip():
            labels_list = [
                lbl.strip() for lbl in labels.split(",") if lbl.strip()
            ]
            if labels_list:
                fields["labels"] = labels_list

        if story_points is not None:
            sp_field = (
                story_points_field.strip()
                if story_points_field
                else "customfield_10016"
            )
            fields[sp_field] = float(story_points)

        url = f"{auth['base_url']}/rest/api/3/issue"

        try:
            self.log(f"Creating issue in {project_key.strip()}: {summary[:80]}")
            response = jira_request(
                "POST",
                url,
                auth["headers"],
                json={"fields": fields},
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                key=None,
                id=None,
                url=None,
                created=False,
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                key=None,
                id=None,
                url=None,
                created=False,
            )

        if response.status_code != 201:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(
                msg,
                error_code=code,
                key=None,
                id=None,
                url=None,
                created=False,
            )

        body = response.json()
        issue_key = body.get("key")
        issue_id = body.get("id")
        issue_url = f"{auth['base_url']}/browse/{issue_key}"

        self.status = f"Created {issue_key}"
        self.log(f"Issue created: {issue_key} ({issue_url})")

        return Data(
            data={
                "key": issue_key,
                "id": issue_id,
                "url": issue_url,
                "created": True,
            }
        )

    # ------------------------------------------------------------------

    def _get_issue(
        self,
        issue_key: str,
        fields: str = "",
        expand: str = "",
    ) -> Data:
        """Retrieve a single Jira issue by key.

        Args:
            issue_key: Jira issue key (e.g. ``PROJ-123``).
            fields: Comma-separated fields to return (optional).
            expand: Comma-separated expand options (e.g. ``changelog``).

        Returns:
            Data with simplified issue dict plus optional ``changelog``.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                issue=None,
            )

        if not issue_key or not issue_key.strip():
            return build_error_response(
                "issue_key is required.",
                error_code="validation_error",
                issue=None,
            )

        issue_key = issue_key.strip().upper()
        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}"

        params: dict[str, str] = {}
        if fields and fields.strip() and fields.strip() != "*all":
            params["fields"] = fields.strip()
        if expand and expand.strip():
            params["expand"] = expand.strip()

        try:
            self.log(f"Fetching issue: {issue_key}")
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                params=params if params else None,
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                issue=None,
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                issue=None,
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code, issue=None)

        body = response.json()
        simplified = simplify_issue(body)

        # Convert ADF description to plain text for agent consumption
        raw_fields = body.get("fields", {})
        description_adf = raw_fields.get("description")
        simplified["description"] = adf_to_text(description_adf)

        # Include all raw fields for advanced consumers
        simplified["all_fields"] = raw_fields

        # Include changelog if expanded
        if body.get("changelog"):
            simplified["changelog"] = body["changelog"]

        self.status = f"Retrieved {issue_key}"
        self.log(f"Issue fetched: {issue_key} ({simplified.get('summary', '')})")

        return Data(data=simplified)

    # ------------------------------------------------------------------

    def _update_issue(
        self,
        issue_key: str,
        summary: str = "",
        description: str = "",
        priority: str = "",
        assignee_account_id: str = "",
        labels: str = "",
        story_points: float | None = None,
        story_points_field: str = "customfield_10016",
    ) -> Data:
        """Update fields on an existing Jira issue.

        Only non-empty fields are included in the payload.

        Args:
            issue_key: Jira issue key (e.g. ``PROJ-123``).
            summary: New summary (optional).
            description: New plain-text description (optional, converted to ADF).
            priority: New priority name (optional).
            assignee_account_id: New assignee account ID (optional).
            labels: Comma-separated labels (optional, replaces existing).
            story_points: Story-point estimate (optional).
            story_points_field: Custom field ID for story points.

        Returns:
            Data with ``issue_key``, ``updated``, ``fields_updated`` keys.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                issue_key=None,
                updated=False,
                fields_updated=[],
            )

        if not issue_key or not issue_key.strip():
            return build_error_response(
                "issue_key is required.",
                error_code="validation_error",
                issue_key=None,
                updated=False,
                fields_updated=[],
            )

        issue_key = issue_key.strip().upper()

        fields: dict[str, Any] = {}
        fields_updated: list[str] = []

        if summary and summary.strip():
            fields["summary"] = summary.strip()
            fields_updated.append("summary")

        if description and description.strip():
            fields["description"] = text_to_adf(description.strip())
            fields_updated.append("description")

        if priority and priority.strip():
            fields["priority"] = {"name": priority.strip()}
            fields_updated.append("priority")

        if assignee_account_id and assignee_account_id.strip():
            fields["assignee"] = {"id": assignee_account_id.strip()}
            fields_updated.append("assignee")

        if labels and labels.strip():
            labels_list = [
                lbl.strip() for lbl in labels.split(",") if lbl.strip()
            ]
            if labels_list:
                fields["labels"] = labels_list
                fields_updated.append("labels")

        if story_points is not None:
            sp_field = (
                story_points_field.strip()
                if story_points_field
                else "customfield_10016"
            )
            fields[sp_field] = float(story_points)
            fields_updated.append("story_points")

        if not fields:
            return build_error_response(
                "No fields to update. Provide at least one field.",
                error_code="validation_error",
                issue_key=issue_key,
                updated=False,
                fields_updated=[],
            )

        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}"

        try:
            self.log(f"Updating {issue_key}: {fields_updated}")
            response = jira_request(
                "PUT",
                url,
                auth["headers"],
                json={"fields": fields},
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                issue_key=issue_key,
                updated=False,
                fields_updated=[],
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                issue_key=issue_key,
                updated=False,
                fields_updated=[],
            )

        if response.status_code != 204:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(
                msg,
                error_code=code,
                issue_key=issue_key,
                updated=False,
                fields_updated=[],
            )

        self.status = f"Updated {issue_key}"
        self.log(f"Issue updated: {issue_key} (fields: {', '.join(fields_updated)})")

        return Data(
            data={
                "issue_key": issue_key,
                "updated": True,
                "fields_updated": fields_updated,
            }
        )

    # ------------------------------------------------------------------

    def _add_comment(
        self,
        issue_key: str,
        body: str,
    ) -> Data:
        """Add a comment to an existing Jira issue.

        Args:
            issue_key: Jira issue key (e.g. ``PROJ-123``).
            body: Plain-text comment body (converted to ADF).

        Returns:
            Data with ``id``, ``issue_key``, ``created`` keys.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                id=None,
                issue_key=None,
                created=False,
            )

        if not issue_key or not issue_key.strip():
            return build_error_response(
                "issue_key is required.",
                error_code="validation_error",
                id=None,
                issue_key=None,
                created=False,
            )
        if not body or not body.strip():
            return build_error_response(
                "Comment body is required.",
                error_code="validation_error",
                id=None,
                issue_key=issue_key.strip().upper(),
                created=False,
            )

        issue_key = issue_key.strip().upper()
        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}/comment"

        payload = {"body": text_to_adf(body.strip())}

        try:
            self.log(f"Adding comment to {issue_key}")
            response = jira_request(
                "POST",
                url,
                auth["headers"],
                json=payload,
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                id=None,
                issue_key=issue_key,
                created=False,
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                id=None,
                issue_key=issue_key,
                created=False,
            )

        if response.status_code != 201:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(
                msg,
                error_code=code,
                id=None,
                issue_key=issue_key,
                created=False,
            )

        resp_body = response.json()
        comment_id = resp_body.get("id")

        self.status = f"Comment added to {issue_key}"
        self.log(f"Comment {comment_id} added to {issue_key}")

        return Data(
            data={
                "id": comment_id,
                "issue_key": issue_key,
                "created": True,
            }
        )

    def _get_issue_links(
        self,
        issue_key: str,
    ) -> Data:
        """Retrieve issue links (blocks, blocked by, relates to) for an issue.

        Args:
            issue_key: Jira issue key (e.g. ``PROJ-123``).

        Returns:
            Data with list of issue links showing dependencies.
        """
        try:
            auth = self._extract_auth()
        except ValueError as exc:
            return build_error_response(
                str(exc),
                error_code="auth_failed",
                issue=None,
            )

        if not issue_key or not issue_key.strip():
            return build_error_response(
                "issue_key is required.",
                error_code="validation_error",
                issue=None,
            )

        issue_key = issue_key.strip().upper()
        url = f"{auth['base_url']}/rest/api/3/issue/{issue_key}"

        try:
            self.log(f"Fetching issue links for: {issue_key}")
            response = jira_request(
                "GET",
                url,
                auth["headers"],
                params={"fields": "issuelinks"},
                log=self.log,
            )
        except RuntimeError as exc:
            return build_error_response(
                str(exc),
                error_code="rate_limited",
                issue=None,
            )
        except Exception as exc:
            return build_error_response(
                f"Request failed: {exc}",
                error_code="connection_error",
                issue=None,
            )

        if response.status_code != 200:
            msg = parse_jira_error(response)
            code = error_code_from_status(response.status_code)
            return build_error_response(msg, error_code=code, issue=None)

        body = response.json()
        raw_links = body.get("fields", {}).get("issuelinks", [])

        # Parse links into simplified structure
        links = []
        for link in raw_links:
            link_type = link.get("type", {}).get("name", "relates to")

            # Outward link (this issue blocks/relates to another)
            if "outwardIssue" in link:
                outward = link["outwardIssue"]
                links.append({
                    "direction": "outward",
                    "type": link_type,
                    "issue_key": outward.get("key"),
                    "summary": outward.get("fields", {}).get("summary", ""),
                    "status": outward.get("fields", {}).get("status", {}).get("name", ""),
                })

            # Inward link (another issue blocks/relates to this one)
            if "inwardIssue" in link:
                inward = link["inwardIssue"]
                links.append({
                    "direction": "inward",
                    "type": link_type,
                    "issue_key": inward.get("key"),
                    "summary": inward.get("fields", {}).get("summary", ""),
                    "status": inward.get("fields", {}).get("status", {}).get("name", ""),
                })

        self.status = f"Retrieved {len(links)} links for {issue_key}"
        self.log(f"Issue links fetched: {issue_key} has {len(links)} links")

        return Data(data={
            "issue_key": issue_key,
            "link_count": len(links),
            "links": links
        })

    # ------------------------------------------------------------------
    # run_model -- default entrypoint for direct (non-agent) invocation
    # ------------------------------------------------------------------

    def run_model(self) -> Data:
        """Execute the default tool operation based on populated inputs.

        For multi-tool components the primary interaction path is via the
        Agent tool interface (``_get_tools``). ``run_model`` provides a
        sensible fallback for direct flow execution by inspecting which
        inputs are populated and dispatching accordingly.

        Returns:
            Data: Result from the dispatched operation.
        """
        # Determine operation from populated inputs
        issue_key = str(self.issue_key).strip() if self.issue_key else ""
        jql = str(self.jql).strip() if self.jql else ""
        comment_body = str(self.comment_body).strip() if self.comment_body else ""
        summary = str(self.summary).strip() if self.summary else ""
        project_key = str(self.project_key).strip() if self.project_key else ""

        # Comment takes precedence when both issue_key and comment_body present
        if issue_key and comment_body:
            return self._add_comment(issue_key=issue_key, body=comment_body)

        # Create if project_key and summary are given (no issue_key)
        if project_key and summary and not issue_key:
            return self._create_issue(
                project_key=project_key,
                summary=summary,
                issue_type=str(self.issue_type).strip() if self.issue_type else "Task",
                description=str(self.description).strip() if self.description else "",
                priority=str(self.priority).strip() if self.priority else "",
                assignee_account_id=(
                    str(self.assignee_account_id).strip()
                    if self.assignee_account_id
                    else ""
                ),
                labels=str(self.labels).strip() if self.labels else "",
                story_points=self.story_points if self.story_points else None,
                story_points_field=(
                    str(self.story_points_field).strip()
                    if self.story_points_field
                    else "customfield_10016"
                ),
            )

        # Update if issue_key and at least one update field are provided
        has_update_field = any([
            summary,
            str(self.description).strip() if self.description else "",
            str(self.priority).strip() if self.priority else "",
            str(self.assignee_account_id).strip() if self.assignee_account_id else "",
            str(self.labels).strip() if self.labels else "",
            self.story_points is not None and self.story_points,
        ])
        if issue_key and has_update_field and not jql:
            return self._update_issue(
                issue_key=issue_key,
                summary=summary,
                description=str(self.description).strip() if self.description else "",
                priority=str(self.priority).strip() if self.priority else "",
                assignee_account_id=(
                    str(self.assignee_account_id).strip()
                    if self.assignee_account_id
                    else ""
                ),
                labels=str(self.labels).strip() if self.labels else "",
                story_points=self.story_points if self.story_points else None,
                story_points_field=(
                    str(self.story_points_field).strip()
                    if self.story_points_field
                    else "customfield_10016"
                ),
            )

        # Get issue if only issue_key is provided
        if issue_key and not jql:
            return self._get_issue(
                issue_key=issue_key,
                fields=str(self.fields).strip() if self.fields else "",
                expand=str(self.expand).strip() if self.expand else "",
            )

        # Search if JQL is provided
        if jql:
            return self._search(
                jql=jql,
                max_results=50,
                fields=str(self.fields).strip() if self.fields else "*all",
            )

        # Nothing actionable
        return build_error_response(
            "No operation could be determined. Provide jql (search), "
            "project_key+summary (create), issue_key (get/update), or "
            "issue_key+comment_body (comment).",
            error_code="validation_error",
        )

    # ------------------------------------------------------------------
    # Tool interface
    # ------------------------------------------------------------------

    def build_tool(self) -> list[Tool]:
        """Build and return all five Jira tools for Agent use."""
        return self._build_core_tools()

    async def _get_tools(self) -> list[Tool]:
        """Build and return all five Jira tools for Agent use."""
        return self._build_core_tools()

    def _build_core_tools(self) -> list[Tool]:
        """Construct the five StructuredTool instances.

        Each tool has its own Pydantic input schema and delegates to the
        corresponding private method.

        Returns:
            List of five ``StructuredTool`` instances.
        """
        tools: list[Tool] = []

        # ---- 1. cg_jira_search ----

        class SearchInput(BaseModel):
            """Input schema for cg_jira_search."""

            jql: str = Field(description="JQL query string to search for issues.")
            max_results: int = Field(
                default=50,
                description="Maximum number of results to return (1-100).",
            )
            fields: str = Field(
                default="*all",
                description="Comma-separated fields to return, or *all.",
            )

        def _do_search(jql: str, max_results: int = 50, fields: str = "*all") -> str:
            result = self._search(jql=jql, max_results=max_results, fields=fields)
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_search",
                description=(
                    "Search Jira issues using JQL (Jira Query Language). "
                    "Returns matching issues with pagination support via "
                    "next_page_token. Use for finding issues by project, "
                    "status, assignee, labels, or any JQL-supported filter."
                ),
                args_schema=SearchInput,
                func=_do_search,
                return_direct=False,
                tags=["cg_jira_search"],
            )
        )

        # ---- 2. cg_jira_create_issue ----

        class CreateIssueInput(BaseModel):
            """Input schema for cg_jira_create_issue."""

            project_key: str = Field(
                description="Jira project key (e.g. PROJ)."
            )
            summary: str = Field(
                description="Issue title / summary (max 255 characters)."
            )
            issue_type: str = Field(
                default="Task",
                description="Issue type name (e.g. Task, Bug, Story).",
            )
            description: str = Field(
                default="",
                description="Plain-text description (auto-converted to ADF).",
            )
            priority: str = Field(
                default="",
                description="Priority: Highest, High, Medium, Low, or Lowest.",
            )
            assignee_account_id: str = Field(
                default="",
                description="Jira account ID of the assignee (use cg_jira_search_user to resolve email to ID).",
            )
            labels: str = Field(
                default="",
                description="Comma-separated labels to apply.",
            )
            story_points: float | None = Field(
                default=None,
                description="Story-point estimate (optional).",
            )
            story_points_field: str = Field(
                default="customfield_10016",
                description="Custom field ID for story points.",
            )

        def _do_create_issue(
            project_key: str,
            summary: str,
            issue_type: str = "Task",
            description: str = "",
            priority: str = "",
            assignee_account_id: str = "",
            labels: str = "",
            story_points: float | None = None,
            story_points_field: str = "customfield_10016",
        ) -> str:
            result = self._create_issue(
                project_key=project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
                priority=priority,
                assignee_account_id=assignee_account_id,
                labels=labels,
                story_points=story_points,
                story_points_field=story_points_field,
            )
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_create_issue",
                description=(
                    "Create a new Jira issue. Requires project_key and summary. "
                    "Description is plain text (auto-converted to ADF). "
                    "Assignee must be an account ID, not email -- use "
                    "cg_jira_search_user to resolve email to account ID first."
                ),
                args_schema=CreateIssueInput,
                func=_do_create_issue,
                return_direct=False,
                tags=["cg_jira_create_issue"],
            )
        )

        # ---- 3. cg_jira_get_issue ----

        class GetIssueInput(BaseModel):
            """Input schema for cg_jira_get_issue."""

            issue_key: str = Field(
                description="Jira issue key (e.g. PROJ-123)."
            )
            fields: str = Field(
                default="",
                description="Comma-separated fields to return (leave empty for all).",
            )
            expand: str = Field(
                default="",
                description="Comma-separated expand options (e.g. changelog, renderedFields).",
            )

        def _do_get_issue(
            issue_key: str,
            fields: str = "",
            expand: str = "",
        ) -> str:
            result = self._get_issue(
                issue_key=issue_key,
                fields=fields,
                expand=expand,
            )
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_get_issue",
                description=(
                    "Get a single Jira issue by key. Returns summary, status, "
                    "priority, assignee, description (as plain text), labels, "
                    "and all fields. Use expand=changelog to include full "
                    "change history."
                ),
                args_schema=GetIssueInput,
                func=_do_get_issue,
                return_direct=False,
                tags=["cg_jira_get_issue"],
            )
        )

        # ---- 4. cg_jira_update_issue ----

        class UpdateIssueInput(BaseModel):
            """Input schema for cg_jira_update_issue."""

            issue_key: str = Field(
                description="Jira issue key to update (e.g. PROJ-123)."
            )
            summary: str = Field(
                default="",
                description="New summary / title (leave empty to keep current).",
            )
            description: str = Field(
                default="",
                description="New plain-text description (leave empty to keep current).",
            )
            priority: str = Field(
                default="",
                description="New priority name (leave empty to keep current).",
            )
            assignee_account_id: str = Field(
                default="",
                description="New assignee account ID (leave empty to keep current).",
            )
            labels: str = Field(
                default="",
                description="Comma-separated labels to set (replaces existing, leave empty to keep current).",
            )
            story_points: float | None = Field(
                default=None,
                description="New story-point estimate (leave empty to keep current).",
            )
            story_points_field: str = Field(
                default="customfield_10016",
                description="Custom field ID for story points.",
            )

        def _do_update_issue(
            issue_key: str,
            summary: str = "",
            description: str = "",
            priority: str = "",
            assignee_account_id: str = "",
            labels: str = "",
            story_points: float | None = None,
            story_points_field: str = "customfield_10016",
        ) -> str:
            result = self._update_issue(
                issue_key=issue_key,
                summary=summary,
                description=description,
                priority=priority,
                assignee_account_id=assignee_account_id,
                labels=labels,
                story_points=story_points,
                story_points_field=story_points_field,
            )
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_update_issue",
                description=(
                    "Update fields on an existing Jira issue. Only non-empty "
                    "fields are sent. Does NOT handle status transitions (use "
                    "CG-JiraTransitions) or comments (use cg_jira_add_comment)."
                ),
                args_schema=UpdateIssueInput,
                func=_do_update_issue,
                return_direct=False,
                tags=["cg_jira_update_issue"],
            )
        )

        # ---- 5. cg_jira_add_comment ----

        class AddCommentInput(BaseModel):
            """Input schema for cg_jira_add_comment."""

            issue_key: str = Field(
                description="Jira issue key to comment on (e.g. PROJ-123)."
            )
            body: str = Field(
                description="Plain-text comment body (auto-converted to ADF)."
            )

        def _do_add_comment(issue_key: str, body: str) -> str:
            result = self._add_comment(issue_key=issue_key, body=body)
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_add_comment",
                description=(
                    "Add a comment to an existing Jira issue. The comment body "
                    "is plain text that gets auto-converted to Atlassian "
                    "Document Format (ADF)."
                ),
                args_schema=AddCommentInput,
                func=_do_add_comment,
                return_direct=False,
                tags=["cg_jira_add_comment"],
            )
        )

        # ---- 6. cg_jira_get_issue_links ----

        class GetIssueLinksInput(BaseModel):
            """Input schema for cg_jira_get_issue_links."""

            issue_key: str = Field(
                description="Jira issue key (e.g. PROJ-123) to get links for."
            )

        def _do_get_issue_links(issue_key: str) -> str:
            result = self._get_issue_links(issue_key=issue_key)
            if result.data.get("error"):
                return json.dumps({"error": result.data["error"], "error_code": result.data.get("error_code", "api_error")})
            return json.dumps(result.data, default=str)

        tools.append(
            StructuredTool.from_function(
                name="cg_jira_get_issue_links",
                description=(
                    "Get all issue links (blocks, blocked by, relates to) for "
                    "a Jira issue. Returns list of linked issues with their "
                    "keys, summaries, statuses, and relationship types. Use for "
                    "identifying dependencies before sprint planning."
                ),
                args_schema=GetIssueLinksInput,
                func=_do_get_issue_links,
                return_direct=False,
                tags=["cg_jira_get_issue_links"],
            )
        )

        return tools
