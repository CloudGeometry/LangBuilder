"""
JIRA State Fetcher Component (Read-Only)

Fetches JIRA tickets from a project using the direct Jira REST API.
Designed for the Enrichment Module - provides current state of JIRA
that the LLM will compare against Slack messages and meeting transcripts.

Features:
- Uses direct Jira REST API (not MCP)
- Can receive auth credentials from JiraAuth component OR manual input
- Can receive project_key from another component OR manual input
- Fetches all tickets from configured project with optional JQL filtering
- Optionally fetches detailed info for each ticket (comments, etc.)
- Outputs formatted data compatible with JIRA Enrichment Module
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any

import requests
from loguru import logger

from langbuilder.custom import Component
from langbuilder.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema import Data
from langbuilder.schema.message import Message


class JiraStateFetcherComponent(Component):
    """Fetch current JIRA state using direct REST API.

    This component connects to JIRA via the REST API and fetches all tickets
    from the configured project. Authentication can be provided via:
    1. A connected JiraAuth component (recommended)
    2. Manual credentials input

    Output is formatted for the JIRA Enrichment Module.
    """

    display_name = "JIRA State Fetcher"
    description = "Fetches all JIRA tickets from a project using direct REST API (read-only)."
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/"
    icon = "Jira"
    name = "JiraStateFetcher"

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
            advanced=False,
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
            advanced=False,
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            info="Jira API token. Used only if Jira Auth not connected. Can also use JIRA_API_KEY env var.",
            required=False,
            advanced=False,
        ),
        DropdownInput(
            name="auth_type",
            display_name="Authentication Type",
            options=["basic", "bearer"],
            value="basic",
            info="Authentication method - Basic for most cases, Bearer for specific APIs",
            advanced=True,
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
            info="The JIRA project key (e.g., PROJ, CLOUD). Used if not provided from component.",
            value="",
            required=False,
            tool_mode=True,
        ),
        MultilineInput(
            name="jql_filter",
            display_name="Additional JQL Filter",
            info="Optional additional JQL filter (e.g., 'status != Done'). Will be AND'd with project filter.",
            required=False,
            placeholder="status != Done AND updated >= -30d",
            advanced=True,
        ),
        # === Fetch Options ===
        IntInput(
            name="max_tickets",
            display_name="Max Tickets",
            value=100,
            info="Maximum number of tickets to fetch (1-1000).",
            advanced=True,
        ),
        BoolInput(
            name="fetch_details",
            display_name="Fetch Full Details",
            info="If true, fetches full details for each ticket including comments (slower but more complete).",
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="include_description",
            display_name="Include Description",
            info="Include ticket descriptions in the output.",
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_comments",
            display_name="Include Comments",
            info="Include recent comments for each ticket (requires fetch_details=True for best results).",
            value=False,
            advanced=True,
        ),
        IntInput(
            name="max_comments",
            display_name="Max Comments Per Ticket",
            value=5,
            info="Maximum number of recent comments to include per ticket.",
            advanced=True,
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (leave empty or '*all' for all fields)",
            value="*all",
            required=False,
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=60,
            info="Request timeout in seconds.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="JIRA State",
            name="jira_state",
            method="fetch_jira_state",
        ),
    ]

    def _get_email_from_input(self) -> str | None:
        """Get email from the email_input DataInput if provided.

        Returns:
            Email string if found in the input, None otherwise.
        """
        if not self.email_input:
            return None

        input_data = (
            self.email_input.data
            if hasattr(self.email_input, "data")
            else self.email_input
        )

        if isinstance(input_data, dict):
            # Check common field names for email
            email = (
                input_data.get("email")
                or input_data.get("user_email")
                or input_data.get("atlassian_email")
                or input_data.get("jira_email")
            )
            if email:
                logger.info(f"Using email from connected component: {email}")
                return str(email)
        elif isinstance(input_data, str) and input_data.strip():
            logger.info(f"Using email from connected component: {input_data}")
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
        # For email: check component input first, then manual, then env var
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
                "Either connect a Jira Auth component or provide manual credentials. "
                "You can also set JIRA_URL, JIRA_EMAIL, and JIRA_API_KEY environment variables."
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

        logger.info(f"Using manual authentication for {email} at {jira_url}")

        return {
            "jira_url": jira_url.rstrip("/"),
            "email": email,
            "headers": headers,
            "auth_type": self.auth_type,
            "authenticated": True,
        }

    def _get_project_key(self) -> str:
        """Get project key from component input or manual input.

        Priority:
        1. project_key_input DataInput (from another component)
        2. Manual project_key input
        """
        # Try to get from connected component first
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

        raise ValueError(
            "Project key is required. Either connect a component providing 'project_key' "
            "or enter it manually in the 'Project Key (Manual)' field."
        )

    def _search_issues(
        self, auth_data: dict[str, Any], jql: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Search for issues using Jira REST API.

        Args:
            auth_data: Authentication data with jira_url and headers
            jql: JQL query string
            max_results: Maximum number of results to return

        Returns:
            List of issue dictionaries
        """
        jira_url = auth_data["jira_url"]
        headers = auth_data["headers"]

        # Parse fields
        fields_list = (
            ["*all"]
            if not self.fields or self.fields == "*all"
            else [f.strip() for f in self.fields.split(",")]
        )

        # Add comment field if needed
        if self.include_comments and "comment" not in fields_list and "*all" not in fields_list:
            fields_list.append("comment")

        # Prepare search payload
        payload = {
            "jql": jql,
            "maxResults": min(max_results, 1000),  # API limit
            "fields": fields_list,
        }

        logger.info(f"Searching Jira with JQL: {jql}")

        # Make API request using the v3 search endpoint
        response = requests.post(
            f"{jira_url}/rest/api/3/search/jql",
            headers=headers,
            data=json.dumps(payload),
            timeout=self.timeout,
        )

        response.raise_for_status()
        result_data = response.json()

        issues = result_data.get("issues", [])
        total = result_data.get("total", 0)

        logger.info(f"Found {total} total issues, retrieved {len(issues)}")

        return issues

    def _get_issue_details(
        self, auth_data: dict[str, Any], issue_key: str
    ) -> dict[str, Any] | None:
        """Get detailed information for a single issue.

        Args:
            auth_data: Authentication data with jira_url and headers
            issue_key: The issue key (e.g., PROJ-123)

        Returns:
            Issue details dictionary or None if failed
        """
        jira_url = auth_data["jira_url"]
        headers = auth_data["headers"]

        try:
            response = requests.get(
                f"{jira_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                params={"expand": "renderedFields,changelog"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch details for {issue_key}: {e}")
            return None

    def _extract_nested_value(self, obj: Any, key: str) -> str:
        """Extract value from nested object or return string."""
        if not obj:
            return ""
        if isinstance(obj, dict):
            return obj.get(key, obj.get("name", ""))
        return str(obj)

    def _extract_user(self, user_data: Any) -> str:
        """Extract user display name from user object."""
        if not user_data:
            return "Unassigned"
        if isinstance(user_data, dict):
            return user_data.get("displayName", user_data.get("name", "Unknown"))
        return str(user_data)

    def _extract_adf_text(self, adf: Any) -> str:
        """Extract plain text from Atlassian Document Format.

        Args:
            adf: ADF document (dict) or plain text string

        Returns:
            Plain text content
        """
        if not adf:
            return ""
        if isinstance(adf, str):
            return adf

        if not isinstance(adf, dict):
            return str(adf)

        texts: list[str] = []

        def extract_text_recursive(node: dict) -> None:
            """Recursively extract text from ADF nodes."""
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                if isinstance(child, dict):
                    extract_text_recursive(child)

        extract_text_recursive(adf)
        return " ".join(texts)

    def _normalize_ticket_data(
        self, issue: dict[str, Any], fetch_details: bool = False
    ) -> dict[str, Any]:
        """Normalize ticket data from Jira API response.

        Args:
            issue: Raw issue data from Jira API
            fetch_details: Whether detailed info was fetched

        Returns:
            Normalized ticket dictionary
        """
        fields = issue.get("fields", {})

        ticket: dict[str, Any] = {
            "key": issue.get("key", ""),
            "id": issue.get("id", ""),
            "summary": fields.get("summary", ""),
            "status": self._extract_nested_value(fields.get("status"), "name"),
            "status_category": self._extract_nested_value(
                fields.get("status", {}).get("statusCategory", {}), "name"
            ),
            "issue_type": self._extract_nested_value(fields.get("issuetype"), "name"),
            "priority": self._extract_nested_value(fields.get("priority"), "name"),
            "assignee": self._extract_user(fields.get("assignee")),
            "reporter": self._extract_user(fields.get("reporter")),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "due_date": fields.get("duedate") or "Not set",
            "labels": fields.get("labels", []),
            "components": [
                c.get("name", "") for c in fields.get("components", []) if isinstance(c, dict)
            ],
            "resolution": self._extract_nested_value(fields.get("resolution"), "name") or "Unresolved",
        }

        # Add sprint info if available
        sprint_field = fields.get("customfield_10020")  # Common sprint field
        if sprint_field and isinstance(sprint_field, list) and sprint_field:
            last_sprint = sprint_field[-1]
            if isinstance(last_sprint, dict):
                ticket["sprint"] = last_sprint.get("name", "")
            elif isinstance(last_sprint, str):
                ticket["sprint"] = last_sprint

        # Add story points if available
        story_points = fields.get("customfield_10016")  # Common story points field
        if story_points is not None:
            ticket["story_points"] = story_points

        # Include description if requested
        if self.include_description:
            description = fields.get("description")
            ticket["description"] = self._extract_adf_text(description)

        # Include comments if requested
        if self.include_comments:
            comments_data = fields.get("comment", {})
            comments = comments_data.get("comments", []) if isinstance(comments_data, dict) else []
            max_comments = self.max_comments or 5

            ticket["recent_comments"] = [
                {
                    "author": self._extract_user(c.get("author")),
                    "body": self._extract_adf_text(c.get("body")),
                    "created": c.get("created", ""),
                }
                for c in comments[-max_comments:]
            ]

        return ticket

    def _fetch_all_tickets(self) -> dict[str, Any]:
        """Fetch all tickets from the configured project.

        Returns:
            Dictionary with project info and tickets list
        """
        # Get auth and project key
        auth_data = self._get_auth_data()
        project_key = self._get_project_key()

        # Build JQL query
        jql = f"project = {project_key}"
        if self.jql_filter and self.jql_filter.strip():
            jql += f" AND ({self.jql_filter.strip()})"
        jql += " ORDER BY updated DESC"

        logger.info(f"Fetching JIRA tickets with JQL: {jql}")
        self.status = f"Fetching tickets from {project_key}..."

        # Search for issues
        issues = self._search_issues(auth_data, jql, self.max_tickets)

        # Process each issue
        tickets: list[dict[str, Any]] = []
        total_issues = len(issues)

        for idx, issue in enumerate(issues):
            issue_key = issue.get("key", "")

            # Update status periodically
            if (idx + 1) % 10 == 0:
                self.status = f"Processing {idx + 1}/{total_issues} tickets..."

            # Optionally fetch full details
            if self.fetch_details and issue_key:
                detailed_issue = self._get_issue_details(auth_data, issue_key)
                if detailed_issue:
                    issue = detailed_issue

            ticket_data = self._normalize_ticket_data(issue, self.fetch_details)
            tickets.append(ticket_data)

        return {
            "project_key": project_key,
            "total_tickets": len(tickets),
            "jql_query": jql,
            "tickets": tickets,
        }

    def _format_output(self, jira_data: dict[str, Any]) -> dict[str, Any]:
        """Format JIRA data for the Enrichment Module.

        Args:
            jira_data: Raw data from _fetch_all_tickets

        Returns:
            Formatted output dictionary
        """
        output: dict[str, Any] = {
            "project": jira_data["project_key"],
            "total_tickets": jira_data["total_tickets"],
            "jql_query": jira_data["jql_query"],
            "fetched_at": datetime.now().isoformat(),
            "tickets": [],
        }

        for ticket in jira_data["tickets"]:
            formatted_ticket: dict[str, Any] = {
                "key": ticket["key"],
                "summary": ticket["summary"],
                "status": ticket["status"],
                "status_category": ticket.get("status_category", ""),
                "type": ticket["issue_type"],
                "priority": ticket["priority"],
                "assignee": ticket["assignee"],
                "reporter": ticket["reporter"],
                "created": ticket["created"],
                "updated": ticket["updated"],
                "due_date": ticket["due_date"],
                "labels": ticket["labels"],
                "components": ticket.get("components", []),
                "resolution": ticket.get("resolution", "Unresolved"),
            }

            # Include optional fields
            if "sprint" in ticket:
                formatted_ticket["sprint"] = ticket["sprint"]
            if "story_points" in ticket:
                formatted_ticket["story_points"] = ticket["story_points"]

            if self.include_description and ticket.get("description"):
                # Truncate long descriptions
                desc = ticket["description"]
                formatted_ticket["description"] = desc[:1000] if len(desc) > 1000 else desc

            if self.include_comments and ticket.get("recent_comments"):
                formatted_ticket["recent_comments"] = ticket["recent_comments"]

            output["tickets"].append(formatted_ticket)

        return output

    def fetch_jira_state(self) -> Message:
        """Fetch all JIRA tickets and return formatted state.

        Returns:
            Message containing JSON text with JIRA state
        """
        try:
            jira_data = self._fetch_all_tickets()
            formatted_output = self._format_output(jira_data)

            self.status = f"Fetched {jira_data['total_tickets']} tickets from {jira_data['project_key']}"
            self.log(
                f"Successfully fetched {jira_data['total_tickets']} tickets "
                f"from project {jira_data['project_key']}"
            )

            return Message(text=json.dumps(formatted_output, indent=2))

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.exception(error_msg)
            self.status = f"Error: {e.response.status_code}"
            return self._error_response(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            logger.exception(error_msg)
            self.status = f"Network error: {e!s}"
            return self._error_response(error_msg)

        except ValueError as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.status = f"Configuration error: {e!s}"
            return self._error_response(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {e!s}"
            logger.exception(error_msg)
            self.status = f"Error: {e!s}"
            return self._error_response(error_msg)

    def _error_response(self, error_msg: str) -> Message:
        """Create error response as a Message.

        Args:
            error_msg: Error message to include

        Returns:
            Message with error information as JSON
        """
        project_key = ""
        try:
            project_key = self._get_project_key()
        except ValueError:
            pass

        error_data = {
            "error": error_msg,
            "project": project_key,
            "total_tickets": 0,
            "tickets": [],
        }

        return Message(text=json.dumps(error_data, indent=2))
