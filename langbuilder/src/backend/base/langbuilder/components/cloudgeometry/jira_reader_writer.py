"""
JIRA Reader/Writer Component (Combined Read & Write Operations)

A unified component for all JIRA operations using direct REST API:
- READ: Get Issue, Search Issues, Get Transitions, Get Projects, Search Users
- WRITE: Create Issue, Update Issue, Transition Issue, Add Comment, Set Due Date, Assign Issue

This component can be used in both regular mode and tool mode by AI agents.

Architecture:
Component/Agent → JIRA Reader/Writer → JIRA Cloud REST API (direct)
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from loguru import logger

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import (
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.message import Message
from langbuilder.services.tracing.spans import ComponentSpanTracker


class JiraReaderWriterComponent(Component):
    """JIRA Reader/Writer for unified read and write operations using direct REST API.

    This component provides all JIRA operations in one place:
    - READ: Get Issue, Search Issues, Get Transitions, Get Projects, Search Users
    - WRITE: Create Issue, Update Issue, Transition Issue, Add Comment, Set Due Date, Assign Issue

    Authentication can be provided via:
    1. A connected JiraAuth component (recommended for multi-user flows)
    2. Manual credentials input
    3. Environment variables (JIRA_URL, JIRA_EMAIL, JIRA_API_KEY)

    Project key and email can also come from connected components (e.g., database lookup).
    """

    display_name = "JIRA Reader/Writer"
    description = "Unified JIRA operations - Search, create, update, transition issues using direct REST API"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/"
    icon = "Jira"
    name = "JiraReaderWriter"

    inputs = [
        # === Authentication (from component or manual) ===
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth (Optional)",
            info="Authentication credentials from Jira Auth component. If not provided, use manual credentials below.",
            required=False,
        ),
        # === Manual Authentication Credentials ===
        StrInput(
            name="jira_url",
            display_name="Jira URL",
            info="Your Jira instance URL (e.g., https://your-domain.atlassian.net). Used only if Jira Auth not connected.",
            required=False,
            placeholder="https://your-domain.atlassian.net",
        ),
        DataInput(
            name="email_input",
            display_name="Email (from component)",
            info="Email from another component (e.g., database lookup). Data object with 'email' field.",
            required=False,
        ),
        StrInput(
            name="email",
            display_name="Email (Manual)",
            info="Your Atlassian account email. Used if not provided from component. Can also use JIRA_EMAIL env var.",
            required=False,
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            info="Jira API token. Used only if Jira Auth not connected. Can also use JIRA_API_KEY env var.",
            required=False,
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            options=["basic", "bearer"],
            value="basic",
            info="Authentication method - Basic for most cases, Bearer for specific APIs",
            advanced=True,
        ),
        # === Action Selection ===
        DropdownInput(
            name="action",
            display_name="Action",
            options=[
                "Search Issues",
                "Get Issue",
                "Create Issue",
                "Update Issue",
                "Transition Issue",
                "Add Comment",
                "Set Due Date",
                "Assign Issue",
                "Search Users",
                "Get Transitions",
                "Get Projects",
            ],
            value="Search Issues",
            info="Action to perform",
            tool_mode=True,
        ),
        # === Project Configuration ===
        DataInput(
            name="project_key_input",
            display_name="Project Key (from component)",
            info="Project key from another component (Data object with 'project_key' field).",
            required=False,
        ),
        MessageTextInput(
            name="project_key",
            display_name="Project Key (Manual)",
            info="JIRA project key (e.g., LAN, PROJ). Required for Create Issue, optional for Search.",
            value="",
            required=False,
            tool_mode=True,
        ),
        # === Issue Key (for single issue operations) ===
        MessageTextInput(
            name="issue_key",
            display_name="Issue Key",
            info="Issue key (e.g., 'LAN-92'). Required for: Get Issue, Update Issue, Transition, Comment, Assign",
            tool_mode=True,
        ),
        # === Search Filters ===
        MessageTextInput(
            name="issue_status",
            display_name="Status Filter",
            info="Filter by status for Search Issues (e.g., 'In Progress', 'To Do', 'Done')",
            tool_mode=True,
        ),
        MessageTextInput(
            name="assignee_filter",
            display_name="Assignee Filter",
            info="Filter by assignee name for Search Issues, or 'currentUser()'",
            tool_mode=True,
            advanced=True,
        ),
        MessageTextInput(
            name="jql",
            display_name="JQL Query",
            info="Custom JQL query for Search Issues (overrides other search filters)",
            tool_mode=True,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of results for Search Issues/Users",
            value=50,
            advanced=True,
        ),
        # === Create/Update Fields ===
        MessageTextInput(
            name="summary",
            display_name="Summary",
            info="Issue summary/title. Required for Create Issue, optional for Update.",
            tool_mode=True,
        ),
        MultilineInput(
            name="description",
            display_name="Description",
            info="Issue description for Create/Update Issue",
            tool_mode=True,
            advanced=True,
        ),
        DropdownInput(
            name="issue_type",
            display_name="Issue Type",
            options=["Task", "Story", "Bug", "Epic", "Subtask"],
            value="Task",
            info="Issue type for Create Issue",
            tool_mode=True,
            advanced=True,
        ),
        DropdownInput(
            name="priority",
            display_name="Priority",
            options=["", "Highest", "High", "Medium", "Low", "Lowest"],
            value="",
            info="Priority for Create/Update Issue",
            tool_mode=True,
            advanced=True,
        ),
        # === Assignee ===
        MessageTextInput(
            name="assignee",
            display_name="Assignee",
            info="Assignee for Create/Update/Assign. Accepts display name (e.g., 'Joaquin') or account ID",
            tool_mode=True,
        ),
        # === Due Date ===
        MessageTextInput(
            name="due_date",
            display_name="Due Date",
            info="Due date. Accepts: 'YYYY-MM-DD', 'end of week', 'friday', 'tomorrow', 'Feb 7'",
            tool_mode=True,
        ),
        # === Transition ===
        MessageTextInput(
            name="transition_to",
            display_name="Transition To",
            info="Target status for Transition Issue (e.g., 'In Progress', 'Done')",
            tool_mode=True,
        ),
        # === Comment ===
        MultilineInput(
            name="comment",
            display_name="Comment",
            info="Comment text for Add Comment action",
            tool_mode=True,
        ),
        # === Labels ===
        MessageTextInput(
            name="labels",
            display_name="Labels",
            info="Comma-separated labels for Create/Update Issue",
            tool_mode=True,
            advanced=True,
        ),
        # === Components ===
        MessageTextInput(
            name="components",
            display_name="Components",
            info="Comma-separated component names for Create/Update Issue",
            tool_mode=True,
            advanced=True,
        ),
        # === User Search ===
        MessageTextInput(
            name="user_query",
            display_name="User Search Query",
            info="Search query for Search Users action (name, email, or partial match)",
            tool_mode=True,
        ),
        # === Settings ===
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            info="Request timeout in seconds.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="message", display_name="Message", method="execute_action"),
    ]

    def _get_email_from_input(self) -> str | None:
        """Get email from the email_input DataInput if provided."""
        if not self.email_input:
            return None

        input_data = (
            self.email_input.data
            if hasattr(self.email_input, "data")
            else self.email_input
        )

        if isinstance(input_data, dict):
            email = (
                input_data.get("email")
                or input_data.get("user_email")
                or input_data.get("atlassian_email")
                or input_data.get("jira_email")
            )
            if email:
                return str(email)
        elif isinstance(input_data, str) and input_data.strip():
            return input_data.strip()

        return None

    def _get_auth_data(self) -> dict[str, Any]:
        """Get authentication data from component input or manual credentials.

        Priority:
        1. auth_credentials DataInput (from JiraAuth component)
        2. Individual inputs (email_input, jira_url, api_token)
        3. Manual credentials (jira_url, email, api_token)
        4. Environment variables (JIRA_URL, JIRA_EMAIL, JIRA_API_KEY)
        """
        # Try to get auth from connected component first
        if self.auth_credentials:
            auth_data = (
                self.auth_credentials.data
                if hasattr(self.auth_credentials, "data")
                else self.auth_credentials
            )
            if isinstance(auth_data, dict) and auth_data.get("authenticated", False):
                logger.info("Using authentication from connected Jira Auth component")
                return auth_data

        # Fall back to manual credentials or environment variables
        jira_url = self.jira_url or os.getenv("JIRA_URL", "")
        email = self._get_email_from_input() or self.email or os.getenv("JIRA_EMAIL", "")
        api_token = self.api_token or os.getenv("JIRA_API_KEY", "")

        if not jira_url or not email or not api_token:
            missing = []
            if not jira_url:
                missing.append("jira_url")
            if not email:
                missing.append("email")
            if not api_token:
                missing.append("api_token")
            raise ValueError(
                f"Missing Jira credentials: {', '.join(missing)}. "
                "Either connect a Jira Auth component or provide manual credentials."
            )

        # Get the actual token value if it's a secret
        token_value = (
            api_token.get_secret_value()
            if hasattr(api_token, "get_secret_value")
            else str(api_token)
        )

        # Validate URL format
        if not jira_url.startswith(("http://", "https://")):
            raise ValueError("Jira URL must start with http:// or https://")

        # Build auth headers
        if self.auth_type == "basic":
            credentials_string = f"{email}:{token_value}"
            encoded_credentials = base64.b64encode(
                credentials_string.encode("utf-8")
            ).decode("utf-8")
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        else:  # bearer
            headers = {
                "Authorization": f"Bearer {token_value}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

        return {
            "jira_url": jira_url.rstrip("/"),
            "email": email,
            "headers": headers,
            "auth_type": self.auth_type,
            "authenticated": True,
        }

    def _get_project_key(self, override: str | None = None) -> str | None:
        """Get project key from override, component input, or manual input.

        Args:
            override: Optional override value (e.g., from tool call)

        Priority:
        1. Override value
        2. project_key_input DataInput (from another component)
        3. Manual project_key input

        Returns:
            Project key string or None
        """
        # Use override if provided
        if override and override.strip():
            return override.strip()

        # Try to get from connected component
        if self.project_key_input:
            input_data = (
                self.project_key_input.data
                if hasattr(self.project_key_input, "data")
                else self.project_key_input
            )
            if isinstance(input_data, dict):
                pk = input_data.get("project_key") or input_data.get("projectKey")
                if pk:
                    logger.info(f"Using project key from connected component: {pk}")
                    return str(pk)
            elif isinstance(input_data, str) and input_data.strip():
                logger.info(f"Using project key from connected component: {input_data}")
                return input_data.strip()

        # Fall back to manual input
        if self.project_key and self.project_key.strip():
            return self.project_key.strip()

        return None

    def _get_client(self) -> httpx.Client:
        """Create authenticated HTTP client."""
        auth_data = self._get_auth_data()
        return httpx.Client(
            base_url=auth_data["jira_url"],
            headers=auth_data["headers"],
            timeout=float(self.timeout),
        )

    def _parse_due_date(self, date_str: str) -> str | None:
        """Parse relative or absolute due date to YYYY-MM-DD format."""
        if not date_str:
            return None

        date_str_lower = date_str.lower().strip()
        today = datetime.now()

        # Handle relative dates
        if date_str_lower in ("today",):
            return today.strftime("%Y-%m-%d")
        elif date_str_lower in ("tomorrow",):
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_str_lower in ("end of week", "end of this week", "eow", "friday", "fri"):
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.weekday() == 4:
                days_until_friday = 0
            elif days_until_friday == 0:
                days_until_friday = 7
            return (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")
        elif date_str_lower in ("next week", "next monday", "monday", "mon"):
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            return (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")
        elif date_str_lower in ("next friday",):
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday <= 0:
                days_until_friday += 7
            return (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")

        # Try to parse as absolute date
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Try natural date like "Feb 7" or "February 7"
        try:
            parsed = datetime.strptime(f"{date_str} {today.year}", "%b %d %Y")
            if parsed < today:
                parsed = parsed.replace(year=today.year + 1)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            parsed = datetime.strptime(f"{date_str} {today.year}", "%B %d %Y")
            if parsed < today:
                parsed = parsed.replace(year=today.year + 1)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

        return date_str  # Return as-is if can't parse

    def _build_adf_content(self, text: str) -> dict[str, Any]:
        """Build Atlassian Document Format (ADF) content from plain text.

        Args:
            text: Plain text content

        Returns:
            ADF document structure
        """
        # Split text into paragraphs
        paragraphs = text.split("\n\n") if "\n\n" in text else [text]

        content = []
        for para in paragraphs:
            if para.strip():
                # Handle line breaks within paragraphs
                lines = para.split("\n")
                para_content = []
                for i, line in enumerate(lines):
                    if line.strip():
                        para_content.append({"type": "text", "text": line})
                        if i < len(lines) - 1:
                            para_content.append({"type": "hardBreak"})

                if para_content:
                    content.append({
                        "type": "paragraph",
                        "content": para_content,
                    })

        return {
            "type": "doc",
            "version": 1,
            "content": content if content else [
                {"type": "paragraph", "content": [{"type": "text", "text": text or " "}]}
            ],
        }

    def _format_issue(self, issue: dict) -> dict:
        """Format issue to return only key fields."""
        fields = issue.get("fields", {})
        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        # Extract assignee
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName") if assignee else "Unassigned"
        assignee_id = assignee.get("accountId") if assignee else None

        # Extract description text
        description = ""
        desc_field = fields.get("description")
        if desc_field and isinstance(desc_field, dict):
            content = desc_field.get("content", [])
            for block in content:
                if block.get("type") == "paragraph":
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            description += item.get("text", "")
                    description += "\n"
        elif isinstance(desc_field, str):
            description = desc_field

        # Extract issue type
        issue_type = fields.get("issuetype", {})
        type_name = issue_type.get("name") if issue_type else None

        # Extract parent info
        parent = fields.get("parent")
        parent_key = parent.get("key") if parent else None

        # Extract labels
        labels = fields.get("labels", [])

        result = {
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "description": description.strip(),
            "assignee": assignee_name,
            "assignee_id": assignee_id,
            "status": fields.get("status", {}).get("name"),
            "due_date": fields.get("duedate"),
            "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
            "type": type_name,
            "labels": labels,
            "url": f"{jira_url}/browse/{issue.get('key')}",
        }

        if parent_key:
            result["parent"] = parent_key

        return result

    def execute_action(self) -> Message:
        """Execute the selected Jira action."""
        action = self.action
        tracker = ComponentSpanTracker(self)

        try:
            with self._get_client() as client:
                if action == "Get Issue":
                    result = self._get_issue(client, tracker)
                elif action == "Search Issues":
                    result = self._search_issues(client, tracker)
                elif action == "Create Issue":
                    result = self._create_issue(client, tracker)
                elif action == "Update Issue":
                    result = self._update_issue(client, tracker)
                elif action == "Transition Issue":
                    result = self._transition_issue(client, tracker)
                elif action == "Add Comment":
                    result = self._add_comment(client, tracker)
                elif action == "Set Due Date":
                    result = self._set_due_date(client, tracker)
                elif action == "Assign Issue":
                    result = self._assign_issue(client, tracker)
                elif action == "Search Users":
                    result = self._search_users(client, tracker)
                elif action == "Get Transitions":
                    result = self._get_transitions(client, tracker)
                elif action == "Get Projects":
                    result = self._get_projects(client, tracker)
                else:
                    result = {"error": f"Unknown action: {action}"}

            return Message(text=json.dumps(result, indent=2))

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            try:
                error_json = e.response.json()
                error_body = json.dumps(error_json, indent=2)
            except Exception:
                pass
            logger.error(f"Jira API error: {e.response.status_code} - {error_body}")
            return Message(text=json.dumps({
                "success": False,
                "error": f"Jira API error {e.response.status_code}",
                "details": error_body,
            }, indent=2))
        except Exception as e:
            logger.exception(f"Error executing Jira action: {e}")
            return Message(text=json.dumps({
                "success": False,
                "error": str(e),
            }, indent=2))

    def _get_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Get issue by key with formatted output."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}

        with tracker.span_sync("Get Issue", span_type="api", inputs={"issue_key": self.issue_key}) as span:
            response = client.get(f"/rest/api/3/issue/{self.issue_key}")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            result = self._format_issue(response.json())
            result["success"] = True
            span.set_output("summary", result.get("summary", "")[:100])
            span.set_output("status", result.get("status"))
            return result

    def _search_issues(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Search issues with formatted output including subtasks."""
        project_key = self._get_project_key()
        assignee_filter_value = None

        if self.jql:
            jql = self.jql
        else:
            conditions = []
            if project_key:
                conditions.append(f'project = "{project_key}"')
            if self.issue_status:
                conditions.append(f'status = "{self.issue_status}"')
            if self.assignee_filter:
                if self.assignee_filter.lower() == "currentuser()":
                    conditions.append("assignee = currentUser()")
                else:
                    assignee_filter_value = self.assignee_filter.lower()

            if not conditions:
                jql = "ORDER BY updated DESC"
            else:
                jql = " AND ".join(conditions) + " ORDER BY updated DESC"

        fetch_limit = self.max_results or 50
        if assignee_filter_value:
            fetch_limit = max(fetch_limit * 3, 100)

        body = {
            "jql": jql,
            "maxResults": fetch_limit,
            "fields": ["summary", "description", "assignee", "status", "duedate", "priority", "parent", "issuetype", "labels"],
        }

        with tracker.span_sync("Search Issues", span_type="api", inputs={"jql": jql, "max_results": fetch_limit}) as span:
            response = client.post("/rest/api/3/search/jql", json=body)
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            data = response.json()
            span.set_output("total_found", data.get("total", 0))

        issues = [self._format_issue(issue) for issue in data.get("issues", [])]

        if assignee_filter_value:
            issues = [
                issue for issue in issues
                if assignee_filter_value in issue.get("assignee", "").lower()
            ]

        max_to_return = self.max_results or 50
        issues = issues[:max_to_return]

        return {
            "success": True,
            "total": data.get("total", 0),
            "showing": len(issues),
            "filtered_by_assignee": assignee_filter_value,
            "jql_used": jql,
            "issues": issues,
        }

    def _create_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Create a new issue."""
        project_key = self._get_project_key()

        if not project_key:
            return {"success": False, "error": "Project key is required for creating issues"}
        if not self.summary:
            return {"success": False, "error": "Summary is required for creating issues"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": self.summary,
            "issuetype": {"name": self.issue_type or "Task"},
        }

        if self.description:
            fields["description"] = self._build_adf_content(self.description)

        if self.priority:
            fields["priority"] = {"name": self.priority}

        if self.assignee:
            with tracker.span_sync("Resolve User", span_type="api", inputs={"user": self.assignee}) as span:
                resolved = self._resolve_user(client, self.assignee)
                if "error" in resolved:
                    span.set_output("error", resolved["error"])
                    return {"success": False, **resolved}
                span.set_output("account_id", resolved["accountId"][:12] + "...")
            fields["assignee"] = {"accountId": resolved["accountId"]}

        if self.due_date:
            parsed_date = self._parse_due_date(self.due_date)
            if parsed_date:
                fields["duedate"] = parsed_date

        if self.labels:
            fields["labels"] = [label.strip() for label in self.labels.split(",") if label.strip()]

        if self.components:
            fields["components"] = [
                {"name": c.strip()} for c in self.components.split(",") if c.strip()
            ]

        with tracker.span_sync("Create Issue", span_type="api", inputs={"project": project_key, "summary": self.summary[:50]}) as span:
            response = client.post("/rest/api/3/issue", json={"fields": fields})
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            created = response.json()
            span.set_output("issue_key", created.get("key"))

        issue_key = created.get("key")
        return {
            "success": True,
            "action": "create_issue",
            "key": issue_key,
            "url": f"{jira_url}/browse/{issue_key}",
            "message": f"Created issue {issue_key}: {self.summary}",
        }

    def _update_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Update an existing issue."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        fields: dict[str, Any] = {}

        if self.summary:
            fields["summary"] = self.summary

        if self.description:
            fields["description"] = self._build_adf_content(self.description)

        if self.priority:
            fields["priority"] = {"name": self.priority}

        if self.labels is not None and self.labels:
            fields["labels"] = [label.strip() for label in self.labels.split(",") if label.strip()]

        if self.components is not None and self.components:
            fields["components"] = [
                {"name": c.strip()} for c in self.components.split(",") if c.strip()
            ]

        if not fields:
            return {"success": False, "error": "No fields to update. Provide at least one field."}

        with tracker.span_sync("Update Issue", span_type="api", inputs={"issue_key": self.issue_key, "fields": list(fields.keys())}) as span:
            response = client.put(f"/rest/api/3/issue/{self.issue_key}", json={"fields": fields})
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()

        return {
            "success": True,
            "action": "update_issue",
            "key": self.issue_key,
            "fields_updated": list(fields.keys()),
            "url": f"{jira_url}/browse/{self.issue_key}",
            "message": f"Updated issue {self.issue_key}",
        }

    def _transition_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Transition an issue to a new status by name."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}
        if not self.transition_to:
            return {"success": False, "error": "Target status (transition_to) is required"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        with tracker.span_sync("Get Transitions", span_type="api", inputs={"issue_key": self.issue_key}) as span:
            response = client.get(f"/rest/api/3/issue/{self.issue_key}/transitions")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            transitions = response.json().get("transitions", [])
            span.set_output("available_count", len(transitions))

        target_lower = self.transition_to.lower()
        transition_id = None
        matched_name = None
        available = []

        for t in transitions:
            available.append(t.get("name"))
            if t.get("name", "").lower() == target_lower:
                transition_id = t.get("id")
                matched_name = t.get("name")
                break

        if not transition_id:
            return {
                "success": False,
                "error": f"Transition to '{self.transition_to}' not available",
                "available_transitions": available,
            }

        with tracker.span_sync("Execute Transition", span_type="api", inputs={"issue_key": self.issue_key, "target": self.transition_to}) as span:
            body = {"transition": {"id": transition_id}}
            response = client.post(f"/rest/api/3/issue/{self.issue_key}/transitions", json=body)
            span.set_metadata("status_code", response.status_code)
            span.set_output("transition_id", transition_id)
            response.raise_for_status()

        return {
            "success": True,
            "action": "transition_issue",
            "key": self.issue_key,
            "new_status": matched_name,
            "url": f"{jira_url}/browse/{self.issue_key}",
            "message": f"Transitioned {self.issue_key} to '{matched_name}'",
        }

    def _add_comment(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Add a comment to an issue."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}
        if not self.comment:
            return {"success": False, "error": "Comment text is required"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        body = {"body": self._build_adf_content(self.comment)}

        with tracker.span_sync("Add Comment", span_type="api", inputs={"issue_key": self.issue_key, "comment_length": len(self.comment)}) as span:
            response = client.post(f"/rest/api/3/issue/{self.issue_key}/comment", json=body)
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            result = response.json()

        return {
            "success": True,
            "action": "add_comment",
            "key": self.issue_key,
            "comment_id": result.get("id"),
            "url": f"{jira_url}/browse/{self.issue_key}",
            "message": f"Added comment to {self.issue_key}",
        }

    def _set_due_date(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Set due date for an issue."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}
        if not self.due_date:
            return {"success": False, "error": "Due date is required"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        parsed_date = self._parse_due_date(self.due_date)

        with tracker.span_sync("Set Due Date", span_type="api", inputs={"issue_key": self.issue_key, "due_date": parsed_date}) as span:
            response = client.put(
                f"/rest/api/3/issue/{self.issue_key}",
                json={"fields": {"duedate": parsed_date}}
            )
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()

        return {
            "success": True,
            "action": "set_due_date",
            "key": self.issue_key,
            "due_date": parsed_date,
            "url": f"{jira_url}/browse/{self.issue_key}",
            "message": f"Set due date for {self.issue_key} to {parsed_date}",
        }

    def _assign_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Assign an issue to a user by name or account ID."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}

        auth_data = self._get_auth_data()
        jira_url = auth_data["jira_url"]

        # If no assignee provided, unassign
        if not self.assignee:
            with tracker.span_sync("Unassign Issue", span_type="api", inputs={"issue_key": self.issue_key}) as span:
                response = client.put(
                    f"/rest/api/3/issue/{self.issue_key}/assignee",
                    json={"accountId": None}
                )
                span.set_metadata("status_code", response.status_code)
                response.raise_for_status()
            return {
                "success": True,
                "action": "unassign_issue",
                "key": self.issue_key,
                "url": f"{jira_url}/browse/{self.issue_key}",
                "message": f"Unassigned {self.issue_key}",
            }

        # Resolve user by name or ID
        with tracker.span_sync("Resolve User", span_type="api", inputs={"user": self.assignee}) as span:
            resolved = self._resolve_user(client, self.assignee)
            if "error" in resolved:
                span.set_output("error", resolved.get("error"))
                return {"success": False, **resolved}
            span.set_output("account_id", resolved["accountId"][:12] + "...")
            span.set_output("display_name", resolved.get("displayName"))

        account_id = resolved["accountId"]
        display_name = resolved.get("displayName", self.assignee)

        with tracker.span_sync("Assign Issue", span_type="api", inputs={"issue_key": self.issue_key, "assignee": display_name}) as span:
            response = client.put(
                f"/rest/api/3/issue/{self.issue_key}/assignee",
                json={"accountId": account_id}
            )
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()

        return {
            "success": True,
            "action": "assign_issue",
            "key": self.issue_key,
            "assigned_to": display_name,
            "assigned_to_id": account_id,
            "url": f"{jira_url}/browse/{self.issue_key}",
            "message": f"Assigned {self.issue_key} to {display_name}",
        }

    def _search_users(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Search for users by name or email."""
        query = self.user_query
        if not query:
            return {"success": False, "error": "User search query is required"}

        project_key = self._get_project_key()
        max_results = self.max_results or 10

        with tracker.span_sync("Search Users", span_type="api", inputs={"query": query}) as span:
            if project_key:
                # Search for users assignable to specific project
                url = "/rest/api/3/user/assignable/search"
                params = {"query": query, "project": project_key, "maxResults": max_results}
            else:
                # General user search
                url = "/rest/api/3/user/search"
                params = {"query": query, "maxResults": max_results}

            response = client.get(url, params=params)
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            users = response.json()
            span.set_output("count", len(users))

        formatted_users = []
        for user in users:
            formatted_users.append({
                "account_id": user.get("accountId"),
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress", ""),
                "active": user.get("active", True),
            })

        return {
            "success": True,
            "action": "search_users",
            "query": query,
            "count": len(formatted_users),
            "users": formatted_users,
            "message": f"Found {len(formatted_users)} user(s) matching '{query}'",
        }

    def _get_transitions(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Get available transitions for an issue."""
        if not self.issue_key:
            return {"success": False, "error": "Issue key is required"}

        with tracker.span_sync("Get Transitions", span_type="api", inputs={"issue_key": self.issue_key}) as span:
            response = client.get(f"/rest/api/3/issue/{self.issue_key}/transitions")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            data = response.json()
            span.set_output("transition_count", len(data.get("transitions", [])))

        transitions = [
            {"id": t.get("id"), "name": t.get("name")}
            for t in data.get("transitions", [])
        ]

        return {
            "success": True,
            "action": "get_transitions",
            "issue_key": self.issue_key,
            "available_transitions": transitions,
        }

    def _get_projects(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Get all accessible projects."""
        with tracker.span_sync("Get Projects", span_type="api") as span:
            response = client.get("/rest/api/3/project")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            data = response.json()
            span.set_output("project_count", len(data))

        projects = [
            {"key": p.get("key"), "name": p.get("name")}
            for p in data
        ]

        return {
            "success": True,
            "action": "get_projects",
            "count": len(projects),
            "projects": projects,
        }

    def _resolve_user(self, client: httpx.Client, user_input: str) -> dict:
        """Resolve a user by display name or account ID.

        Returns dict with 'accountId' on success, or 'error' on failure.
        """
        if not user_input:
            return {"error": "No user specified"}

        # If it looks like an account ID, validate it exists
        if len(user_input) == 24 or user_input.startswith("5") or user_input.startswith("6"):
            try:
                response = client.get("/rest/api/3/user", params={"accountId": user_input})
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "accountId": user_input,
                        "displayName": user_data.get("displayName", user_input),
                    }
            except Exception:
                pass

        # Search for user by display name
        response = client.get(
            "/rest/api/3/user/search",
            params={"query": user_input, "maxResults": 10}
        )
        response.raise_for_status()
        users = response.json()

        if not users:
            return {"error": f"No user found matching '{user_input}'"}

        # Try exact match first (case-insensitive)
        user_lower = user_input.lower()
        for user in users:
            if user.get("displayName", "").lower() == user_lower:
                return {"accountId": user.get("accountId"), "displayName": user.get("displayName")}

        # If only one result, use it
        if len(users) == 1:
            return {"accountId": users[0].get("accountId"), "displayName": users[0].get("displayName")}

        # Multiple matches, return them for disambiguation
        matches = [{"name": u.get("displayName"), "accountId": u.get("accountId")} for u in users]
        return {"error": f"Multiple users match '{user_input}'", "matches": matches}
