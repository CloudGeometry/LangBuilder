import json
from datetime import datetime, timedelta

import httpx

from langflow.custom.custom_component.component import Component
from lfx.components.cloudgeometry._span_tracker import ComponentSpanTracker
from langflow.inputs import (
    IntInput,
    MessageTextInput,
    MultilineInput,
    SecretStrInput,
)
from langflow.io import Output
from langflow.logging import logger
from langflow.schema.message import Message


class JiraAPIComponent(Component):
    """Jira API component for direct interaction with Jira Cloud REST API.

    Use as a tool for agents to search, create, update, and transition Jira issues.
    """

    display_name: str = "Jira"
    description: str = "Connect directly to Jira Cloud API - Search, create, update, and transition issues"
    icon = "Jira"
    documentation: str = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/"

    inputs = [
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            info="Jira API Token from https://id.atlassian.com/manage-profile/security/api-tokens",
            required=True,
        ),
        MessageTextInput(
            name="email",
            display_name="Email",
            info="Your Atlassian account email",
            required=True,
        ),
        MessageTextInput(
            name="jira_url",
            display_name="Jira URL",
            info="Your Jira Cloud URL (e.g., https://yourcompany.atlassian.net)",
            required=True,
        ),
        MessageTextInput(
            name="action",
            display_name="Action",
            info="Action to perform: Get Issue, Search Issues, Create Issue, Update Issue, Transition Issue, Add Comment, Set Due Date, Assign Issue, Get Transitions, Get Projects",
            value="Search Issues",
            required=True,
            tool_mode=True,
        ),
        # Common fields
        MessageTextInput(
            name="issue_key",
            display_name="Issue Key",
            info="The issue key (e.g., 'LAN-92'). Required for: Get Issue, Update Issue, Transition Issue, Add Comment, Set Due Date, Assign Issue, Get Transitions",
            tool_mode=True,
        ),
        # Search fields
        MessageTextInput(
            name="project_key",
            display_name="Project Key",
            info="The project key (e.g., 'LAN'). Required for: Create Issue, Search Issues",
            tool_mode=True,
        ),
        MessageTextInput(
            name="issue_status",
            display_name="Status",
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
            info="Maximum number of results to return for Search Issues",
            value=50,
            advanced=True,
        ),
        # Create/Update fields
        MessageTextInput(
            name="summary",
            display_name="Summary",
            info="Issue summary/title. Required for: Create Issue. Optional for: Update Issue",
            tool_mode=True,
        ),
        MultilineInput(
            name="description",
            display_name="Description",
            info="Issue description for Create Issue or Update Issue",
            tool_mode=True,
            advanced=True,
        ),
        MessageTextInput(
            name="issue_type",
            display_name="Issue Type",
            info="Issue type for Create Issue (e.g., 'Bug', 'Task', 'Story')",
            value="Task",
            tool_mode=True,
            advanced=True,
        ),
        MessageTextInput(
            name="priority",
            display_name="Priority",
            info="Priority for Create Issue or Update Issue (e.g., 'High', 'Medium', 'Low')",
            tool_mode=True,
            advanced=True,
        ),
        # Assignee
        MessageTextInput(
            name="assignee",
            display_name="Assignee",
            info="Assignee for Create Issue or Assign Issue. Accepts display name (e.g., 'John Smith') or account ID",
            tool_mode=True,
            advanced=True,
        ),
        # Due date
        MessageTextInput(
            name="due_date",
            display_name="Due Date",
            info="Due date for Set Due Date or Create Issue. Accepts: 'YYYY-MM-DD', 'end of week', 'friday', 'tomorrow', 'Feb 7'",
            tool_mode=True,
        ),
        # Transition
        MessageTextInput(
            name="transition_to",
            display_name="Transition To",
            info="Target status name for Transition Issue (e.g., 'In Progress', 'Done', 'Ready for QA')",
            tool_mode=True,
        ),
        # Comment
        MultilineInput(
            name="comment",
            display_name="Comment",
            info="Comment text for Add Comment action",
            tool_mode=True,
            advanced=True,
        ),
        # Labels
        MessageTextInput(
            name="labels",
            display_name="Labels",
            info="Comma-separated labels for Create Issue or Update Issue",
            tool_mode=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="message", display_name="Message", method="execute_action"),
    ]

    def _get_client(self) -> httpx.Client:
        """Create authenticated HTTP client."""
        import base64

        auth_string = f"{self.email}:{self.api_token}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        base_url = self.jira_url.rstrip("/")

        return httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def _parse_due_date(self, date_str: str) -> str:
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
            # Find next Friday (or this Friday if today is before Friday)
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.weekday() == 4:
                days_until_friday = 0  # It's Friday, use today
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
            # Add current year
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

    def _format_issue(self, issue: dict) -> dict:
        """Format issue to return only key fields."""
        fields = issue.get("fields", {})

        # Extract assignee
        assignee = fields.get("assignee")
        assignee_name = assignee.get("displayName") if assignee else "Unassigned"

        # Extract description text
        description = ""
        desc_field = fields.get("description")
        if desc_field and isinstance(desc_field, dict):
            # ADF format - extract text
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
        is_subtask = issue_type.get("subtask", False) if issue_type else False

        # Extract parent info
        parent = fields.get("parent")
        parent_key = parent.get("key") if parent else None

        result = {
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "description": description.strip(),
            "assignee": assignee_name,
            "status": fields.get("status", {}).get("name"),
            "due_date": fields.get("duedate"),
            "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
            "type": type_name,
            "url": f"{self.jira_url}/browse/{issue.get('key')}",
        }

        # Add parent info if it's a subtask
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
            return Message(text=f"Error {e.response.status_code}: {error_body}")
        except Exception as e:
            logger.error(f"Error executing Jira action: {e}")
            return Message(text=f"Error: {e!s}")

    def _get_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Get issue by key with formatted output."""
        if not self.issue_key:
            return {"error": "Issue key is required"}

        with tracker.span_sync("Get Issue", span_type="api", inputs={"issue_key": self.issue_key}) as span:
            response = client.get(f"/rest/api/3/issue/{self.issue_key}")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            result = self._format_issue(response.json())
            span.set_output("summary", result.get("summary", "")[:100])
            span.set_output("status", result.get("status"))
            return result

    def _search_issues(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Search issues with formatted output including subtasks."""
        # Build JQL
        assignee_filter_value = None
        if self.jql:
            jql = self.jql
        else:
            conditions = []
            if self.project_key:
                conditions.append(f'project = "{self.project_key}"')
            if self.issue_status:
                conditions.append(f'status = "{self.issue_status}"')
            if self.assignee_filter:
                if self.assignee_filter.lower() == "currentuser()":
                    conditions.append("assignee = currentUser()")
                else:
                    # Store for client-side filtering (JQL assignee doesn't support partial match)
                    assignee_filter_value = self.assignee_filter.lower()

            if not conditions:
                # Default: get all issues from all projects (limited by max_results)
                jql = "ORDER BY updated DESC"
            else:
                jql = " AND ".join(conditions) + " ORDER BY updated DESC"

        # If filtering by assignee name, fetch more results to filter client-side
        fetch_limit = self.max_results or 50
        if assignee_filter_value:
            fetch_limit = max(fetch_limit * 3, 100)  # Fetch more to filter

        body = {
            "jql": jql,
            "maxResults": fetch_limit,
            "fields": ["summary", "description", "assignee", "status", "duedate", "priority", "parent", "issuetype"],
        }

        with tracker.span_sync("Search Issues", span_type="api", inputs={"jql": jql, "max_results": fetch_limit}) as span:
            response = client.post("/rest/api/3/search/jql", json=body)
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            data = response.json()
            span.set_output("total_found", data.get("total", 0))

        issues = [self._format_issue(issue) for issue in data.get("issues", [])]

        # Client-side filter by assignee name (partial match)
        if assignee_filter_value:
            issues = [
                issue for issue in issues
                if assignee_filter_value in issue.get("assignee", "").lower()
            ]

        # Limit to requested max
        max_to_return = self.max_results or 50
        issues = issues[:max_to_return]

        return {
            "total": data.get("total", 0),
            "showing": len(issues),
            "filtered_by_assignee": assignee_filter_value,
            "jql_used": jql,
            "issues": issues,
        }

    def _create_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Create a new issue."""
        if not self.project_key or not self.summary:
            return {"error": "Project key and summary are required"}

        fields = {
            "project": {"key": self.project_key},
            "summary": self.summary,
            "issuetype": {"name": self.issue_type or "Task"},
        }

        if self.description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": self.description}]
                    }
                ]
            }

        if self.priority:
            fields["priority"] = {"name": self.priority}

        if self.assignee:
            with tracker.span_sync("Resolve User", span_type="api", inputs={"user": self.assignee}) as span:
                resolved = self._resolve_user(client, self.assignee)
                if "error" in resolved:
                    span.set_output("error", resolved["error"])
                    return resolved
                span.set_output("account_id", resolved["accountId"][:12] + "...")
            fields["assignee"] = {"accountId": resolved["accountId"]}

        if self.due_date:
            parsed_date = self._parse_due_date(self.due_date)
            if parsed_date:
                fields["duedate"] = parsed_date

        if self.labels:
            fields["labels"] = [label.strip() for label in self.labels.split(",")]

        with tracker.span_sync("Create Issue", span_type="api", inputs={"project": self.project_key, "summary": self.summary[:50]}) as span:
            response = client.post("/rest/api/3/issue", json={"fields": fields})
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            created = response.json()
            span.set_output("issue_key", created.get("key"))

        return {
            "success": True,
            "key": created.get("key"),
            "url": f"{self.jira_url}/browse/{created.get('key')}",
            "message": f"Created issue {created.get('key')}: {self.summary}",
        }

    def _update_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Update an existing issue."""
        if not self.issue_key:
            return {"error": "Issue key is required"}

        fields = {}

        if self.summary:
            fields["summary"] = self.summary

        if self.description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": self.description}]
                    }
                ]
            }

        if self.priority:
            fields["priority"] = {"name": self.priority}

        if self.labels:
            fields["labels"] = [label.strip() for label in self.labels.split(",")]

        if not fields:
            return {"error": "No fields to update"}

        with tracker.span_sync("Update Issue", span_type="api", inputs={"issue_key": self.issue_key, "fields": list(fields.keys())}) as span:
            response = client.put(f"/rest/api/3/issue/{self.issue_key}", json={"fields": fields})
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()

        return {
            "success": True,
            "key": self.issue_key,
            "message": f"Updated issue {self.issue_key}",
        }

    def _transition_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Transition an issue to a new status by name."""
        if not self.issue_key or not self.transition_to:
            return {"error": "Issue key and target status are required"}

        # First, get available transitions
        with tracker.span_sync("Get Transitions", span_type="api", inputs={"issue_key": self.issue_key}) as span:
            response = client.get(f"/rest/api/3/issue/{self.issue_key}/transitions")
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()
            transitions = response.json().get("transitions", [])
            span.set_output("available_count", len(transitions))

        # Find matching transition
        target_lower = self.transition_to.lower()
        transition_id = None
        available = []

        for t in transitions:
            available.append(t.get("name"))
            if t.get("name", "").lower() == target_lower:
                transition_id = t.get("id")
                break

        if not transition_id:
            return {
                "error": f"Transition to '{self.transition_to}' not available",
                "available_transitions": available,
            }

        # Execute transition
        with tracker.span_sync("Execute Transition", span_type="api", inputs={"issue_key": self.issue_key, "target": self.transition_to}) as span:
            body = {"transition": {"id": transition_id}}
            response = client.post(f"/rest/api/3/issue/{self.issue_key}/transitions", json=body)
            span.set_metadata("status_code", response.status_code)
            span.set_output("transition_id", transition_id)
            response.raise_for_status()

        return {
            "success": True,
            "key": self.issue_key,
            "message": f"Transitioned {self.issue_key} to '{self.transition_to}'",
        }

    def _add_comment(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Add a comment to an issue."""
        if not self.issue_key or not self.comment:
            return {"error": "Issue key and comment are required"}

        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": self.comment}]
                    }
                ]
            }
        }

        with tracker.span_sync("Add Comment", span_type="api", inputs={"issue_key": self.issue_key, "comment_length": len(self.comment)}) as span:
            response = client.post(f"/rest/api/3/issue/{self.issue_key}/comment", json=body)
            span.set_metadata("status_code", response.status_code)
            response.raise_for_status()

        return {
            "success": True,
            "key": self.issue_key,
            "message": f"Added comment to {self.issue_key}",
        }

    def _set_due_date(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Set due date for an issue."""
        if not self.issue_key or not self.due_date:
            return {"error": "Issue key and due date are required"}

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
            "key": self.issue_key,
            "due_date": parsed_date,
            "message": f"Set due date for {self.issue_key} to {parsed_date}",
        }

    def _assign_issue(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Assign an issue to a user by name or account ID."""
        if not self.issue_key:
            return {"error": "Issue key is required"}

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
                "key": self.issue_key,
                "message": f"Unassigned {self.issue_key}",
            }

        # Resolve user by name or ID
        with tracker.span_sync("Resolve User", span_type="api", inputs={"user": self.assignee}) as span:
            resolved = self._resolve_user(client, self.assignee)
            if "error" in resolved:
                span.set_output("error", resolved.get("error"))
                return resolved
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
            "key": self.issue_key,
            "assigned_to": display_name,
            "message": f"Assigned {self.issue_key} to {display_name}",
        }

    def _get_transitions(self, client: httpx.Client, tracker: ComponentSpanTracker) -> dict:
        """Get available transitions for an issue."""
        if not self.issue_key:
            return {"error": "Issue key is required"}

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
            "issue_key": self.issue_key,
            "available_transitions": transitions,
        }

    def _resolve_user(self, client: httpx.Client, user_input: str) -> dict:
        """Resolve a user by display name or account ID.

        Returns dict with 'accountId' on success, or 'error' on failure.
        """
        if not user_input:
            return {"error": "No user specified"}

        # If it looks like an account ID (typically 24 hex chars or specific format), use directly
        if len(user_input) == 24 or user_input.startswith("5") or user_input.startswith("6"):
            # Likely an account ID, validate it exists
            try:
                response = client.get(f"/rest/api/3/user", params={"accountId": user_input})
                if response.status_code == 200:
                    return {"accountId": user_input}
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

        return {"projects": projects}
