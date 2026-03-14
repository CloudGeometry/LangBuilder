"""
JIRA Writer Tools Component (Write Operations - TOOL MODE)

Exposes JIRA write operations as tools for the LLM Agent using direct REST API:
- jira_create_issue: Create a new issue
- jira_update_issue: Update fields on an existing issue
- jira_add_comment: Add a comment to an issue
- jira_transition_issue: Change issue status/workflow state

This component is designed for TOOL MODE - the LLM Agent decides when to call these
tools based on the approved proposals from the user.

Architecture:
LLM Agent → JIRA Writer Tools → JIRA Cloud REST API (direct)
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests
from langchain_core.tools import StructuredTool
from loguru import logger
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.io import (
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
    StrInput,
)
from lfx.schema import Data


class JiraWriterToolsComponent(LCToolComponent):
    """JIRA Write Operations for LLM Agent (TOOL MODE) using direct REST API.

    This component exposes JIRA write tools that the LLM can use to execute
    approved changes. The LLM decides when to call these based on user approvals.

    Available Tools:
    - jira_create_issue: Create a new issue with all fields
    - jira_update_issue: Update issue fields (description, summary, due_date, etc.)
    - jira_add_comment: Add a comment to an issue
    - jira_transition_issue: Change issue status

    Authentication can be provided via:
    1. A connected JiraAuth component (recommended)
    2. Manual credentials input
    3. Environment variables

    **IMPORTANT:** This component should only be used after user approval.
    The LLM receives approval decisions and decides which updates to execute.
    """

    display_name = "JIRA Writer Tools"
    description = "JIRA write operations (create, update, comment, transition) for LLM Agent tool mode using direct REST API."
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/"
    icon = "Jira"
    name = "JiraWriterTools"

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
            info="Default JIRA project key for creating issues (e.g., PROJ, CLOUD). Used if not provided from component or by agent.",
            value="",
            required=False,
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

    def _get_project_key(self, override: str | None = None) -> str:
        """Get project key from override, component input, or manual input.

        Args:
            override: Optional override value (e.g., from agent tool call)

        Priority:
        1. Override value (from agent tool call)
        2. project_key_input DataInput (from another component)
        3. Manual project_key input

        Returns:
            Project key string

        Raises:
            ValueError: If no project key is available
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

        raise ValueError(
            "Project key is required for creating issues. Either connect a component "
            "providing 'project_key', enter it manually, or provide it in the tool call."
        )

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

    def _create_issue(
        self,
        summary: str,
        project_key: str | None = None,
        issue_type: str = "Task",
        description: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: str | None = None,
        due_date: str | None = None,
        components: str | None = None,
    ) -> str:
        """Create a new JIRA issue.

        Args:
            summary: Issue summary/title
            project_key: Project key (e.g., PROJ). If not provided, uses configured default.
            issue_type: Type of issue (Task, Story, Bug, Epic, Subtask)
            description: Detailed description
            priority: Priority level (High, Medium, Low, etc.)
            assignee: Assignee account ID or email
            labels: Comma-separated labels
            due_date: Due date in YYYY-MM-DD format
            components: Comma-separated component names

        Returns:
            JSON string with result
        """
        try:
            auth_data = self._get_auth_data()
            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            # Get project key (from parameter, component input, or manual config)
            resolved_project_key = self._get_project_key(project_key)

            # Build issue fields
            fields: dict[str, Any] = {
                "project": {"key": resolved_project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }

            if description:
                fields["description"] = self._build_adf_content(description)

            if priority:
                fields["priority"] = {"name": priority}

            if assignee:
                if "@" in assignee:
                    fields["assignee"] = {"emailAddress": assignee}
                else:
                    fields["assignee"] = {"id": assignee}

            if labels:
                fields["labels"] = [l.strip() for l in labels.split(",") if l.strip()]

            if due_date:
                fields["duedate"] = due_date

            if components:
                fields["components"] = [
                    {"name": c.strip()} for c in components.split(",") if c.strip()
                ]

            payload = {"fields": fields}

            logger.info(f"Creating JIRA issue in {resolved_project_key}: {summary[:50]}...")

            response = requests.post(
                f"{jira_url}/rest/api/3/issue",
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            issue_key = result.get("key")
            return json.dumps({
                "success": True,
                "action": "create_issue",
                "issue_key": issue_key,
                "issue_id": result.get("id"),
                "url": f"{jira_url}/browse/{issue_key}",
                "message": f"Successfully created issue {issue_key}",
            }, indent=2)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "action": "create_issue",
                "error": error_msg,
            }, indent=2)
        except Exception as e:
            logger.exception(f"Error creating issue: {e}")
            return json.dumps({
                "success": False,
                "action": "create_issue",
                "error": str(e),
            }, indent=2)

    def _update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: str | None = None,
        due_date: str | None = None,
        components: str | None = None,
    ) -> str:
        """Update fields on an existing JIRA issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            summary: New summary/title
            description: New description
            priority: New priority
            assignee: New assignee (account ID or email)
            labels: New labels (comma-separated, replaces existing)
            due_date: New due date (YYYY-MM-DD format)
            components: New components (comma-separated, replaces existing)

        Returns:
            JSON string with result
        """
        try:
            auth_data = self._get_auth_data()
            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            fields: dict[str, Any] = {}

            if summary:
                fields["summary"] = summary

            if description:
                fields["description"] = self._build_adf_content(description)

            if priority:
                fields["priority"] = {"name": priority}

            if assignee:
                if "@" in assignee:
                    fields["assignee"] = {"emailAddress": assignee}
                else:
                    fields["assignee"] = {"id": assignee}

            if labels is not None:  # Allow empty string to clear labels
                fields["labels"] = [l.strip() for l in labels.split(",") if l.strip()] if labels else []

            if due_date:
                fields["duedate"] = due_date

            if components is not None:
                fields["components"] = [
                    {"name": c.strip()} for c in components.split(",") if c.strip()
                ] if components else []

            if not fields:
                return json.dumps({
                    "success": False,
                    "action": "update_issue",
                    "issue_key": issue_key,
                    "error": "No fields to update. Provide at least one field.",
                }, indent=2)

            payload = {"fields": fields}

            logger.info(f"Updating JIRA issue {issue_key}: {list(fields.keys())}")

            response = requests.put(
                f"{jira_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()

            return json.dumps({
                "success": True,
                "action": "update_issue",
                "issue_key": issue_key,
                "fields_updated": list(fields.keys()),
                "url": f"{jira_url}/browse/{issue_key}",
                "message": f"Successfully updated issue {issue_key}",
            }, indent=2)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "action": "update_issue",
                "issue_key": issue_key,
                "error": error_msg,
            }, indent=2)
        except Exception as e:
            logger.exception(f"Error updating issue: {e}")
            return json.dumps({
                "success": False,
                "action": "update_issue",
                "issue_key": issue_key,
                "error": str(e),
            }, indent=2)

    def _add_comment(self, issue_key: str, comment: str) -> str:
        """Add a comment to a JIRA issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            comment: Comment text

        Returns:
            JSON string with result
        """
        try:
            auth_data = self._get_auth_data()
            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            payload = {"body": self._build_adf_content(comment)}

            logger.info(f"Adding comment to {issue_key}: {comment[:50]}...")

            response = requests.post(
                f"{jira_url}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            return json.dumps({
                "success": True,
                "action": "add_comment",
                "issue_key": issue_key,
                "comment_id": result.get("id"),
                "url": f"{jira_url}/browse/{issue_key}",
                "message": f"Successfully added comment to {issue_key}",
            }, indent=2)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "action": "add_comment",
                "issue_key": issue_key,
                "error": error_msg,
            }, indent=2)
        except Exception as e:
            logger.exception(f"Error adding comment: {e}")
            return json.dumps({
                "success": False,
                "action": "add_comment",
                "issue_key": issue_key,
                "error": str(e),
            }, indent=2)

    def _transition_issue(self, issue_key: str, transition_name: str) -> str:
        """Transition a JIRA issue to a new status.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            transition_name: Name of the target status (e.g., "In Progress", "Done")

        Returns:
            JSON string with result
        """
        try:
            auth_data = self._get_auth_data()
            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            # Get available transitions
            logger.info(f"Getting available transitions for {issue_key}...")
            transitions_response = requests.get(
                f"{jira_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                timeout=self.timeout,
            )
            transitions_response.raise_for_status()
            transitions = transitions_response.json().get("transitions", [])

            # Find matching transition (case-insensitive)
            transition_id = None
            matched_name = None
            for transition in transitions:
                if transition["name"].lower() == transition_name.lower():
                    transition_id = transition["id"]
                    matched_name = transition["name"]
                    break

            if not transition_id:
                available = [t["name"] for t in transitions]
                return json.dumps({
                    "success": False,
                    "action": "transition_issue",
                    "issue_key": issue_key,
                    "error": f"Transition '{transition_name}' not available. Available transitions: {available}",
                    "available_transitions": available,
                }, indent=2)

            # Execute transition
            payload = {"transition": {"id": transition_id}}

            logger.info(f"Transitioning {issue_key} to: {matched_name}")

            response = requests.post(
                f"{jira_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()

            return json.dumps({
                "success": True,
                "action": "transition_issue",
                "issue_key": issue_key,
                "new_status": matched_name,
                "url": f"{jira_url}/browse/{issue_key}",
                "message": f"Successfully transitioned {issue_key} to '{matched_name}'",
            }, indent=2)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "action": "transition_issue",
                "issue_key": issue_key,
                "error": error_msg,
            }, indent=2)
        except Exception as e:
            logger.exception(f"Error transitioning issue: {e}")
            return json.dumps({
                "success": False,
                "action": "transition_issue",
                "issue_key": issue_key,
                "error": str(e),
            }, indent=2)

    def _search_users(
        self,
        query: str,
        project_key: str | None = None,
        max_results: int = 10,
    ) -> str:
        """Search for JIRA users by name or email.

        Args:
            query: Search query (name, email, or part of either)
            project_key: Optional project key to filter assignable users
            max_results: Maximum number of results to return

        Returns:
            JSON string with list of matching users
        """
        try:
            auth_data = self._get_auth_data()
            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            # Use assignable search if project_key provided, otherwise general search
            if project_key:
                # Search for users assignable to a specific project
                url = f"{jira_url}/rest/api/3/user/assignable/search"
                params = {
                    "query": query,
                    "project": project_key,
                    "maxResults": max_results,
                }
            else:
                # General user search
                url = f"{jira_url}/rest/api/3/user/search"
                params = {
                    "query": query,
                    "maxResults": max_results,
                }

            logger.info(f"Searching for users matching: {query}")

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            users = response.json()

            # Format user results
            formatted_users = []
            for user in users:
                formatted_users.append({
                    "account_id": user.get("accountId"),
                    "display_name": user.get("displayName"),
                    "email": user.get("emailAddress", ""),
                    "active": user.get("active", True),
                })

            return json.dumps({
                "success": True,
                "action": "search_users",
                "query": query,
                "count": len(formatted_users),
                "users": formatted_users,
                "message": f"Found {len(formatted_users)} user(s) matching '{query}'",
            }, indent=2)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "action": "search_users",
                "query": query,
                "error": error_msg,
            }, indent=2)
        except Exception as e:
            logger.exception(f"Error searching users: {e}")
            return json.dumps({
                "success": False,
                "action": "search_users",
                "query": query,
                "error": str(e),
            }, indent=2)

    def run_model(self) -> Data:
        """Default run method - returns tool information.

        Returns:
            Data object with available tools info
        """
        self.status = "JIRA Writer Tools ready"
        return Data(data={
            "status": "ready",
            "available_tools": [
                "jira_search_users",
                "jira_create_issue",
                "jira_update_issue",
                "jira_add_comment",
                "jira_transition_issue",
            ],
            "message": "Use the tools via Agent mode to search users, create, update, comment on, or transition JIRA issues.",
        })

    async def _get_tools(self) -> list[Tool]:
        """Override to return named tools from build_tool()."""
        tools = self.build_tool()
        if isinstance(tools, list):
            for tool in tools:
                if tool and not tool.tags:
                    tool.tags = [tool.name]
            return tools
        if tools and not tools.tags:
            tools.tags = [tools.name]
        return [tools] if tools else []

    def build_tool(self) -> Tool | list[Tool]:
        """Build LangChain tools for Agent use.

        Returns:
            List of JIRA write operation tools
        """

        # ========================================
        # JIRA SEARCH USERS TOOL
        # ========================================
        class JiraSearchUsersInput(BaseModel):
            query: str = Field(
                description="Search query - name, email, or partial match (e.g., 'john', 'john.doe', 'john@')"
            )
            project_key: str | None = Field(
                default=None,
                description="Optional project key to filter users assignable to that project"
            )
            max_results: int = Field(
                default=10,
                description="Maximum number of users to return (default: 10)"
            )

        jira_search_users_tool = StructuredTool.from_function(
            name="jira_search_users",
            description="""Search for JIRA users by name or email.

Use this tool BEFORE assigning issues to find the correct account_id for a user.

When a user says "assign to John" or "assign to Joaquin":
1. First call jira_search_users(query="John") or jira_search_users(query="Joaquin")
2. Get the account_id from the results
3. Then call jira_update_issue with assignee=account_id

Returns a list of matching users with:
- account_id: Use this value for the assignee parameter
- display_name: The user's display name
- email: The user's email (if available)

Example workflow:
1. User says: "Assign LAN-92 to Joaquin"
2. Call: jira_search_users(query="Joaquin")
3. Response shows: account_id="5b10ac8d82e05b22cc7d4ef5", display_name="Joaquin Garcia"
4. Call: jira_update_issue(issue_key="LAN-92", assignee="5b10ac8d82e05b22cc7d4ef5")""",
            args_schema=JiraSearchUsersInput,
            func=lambda **kwargs: self._search_users(**kwargs),
            return_direct=False,
            tags=["jira_search_users", "jira", "read"],
        )

        # ========================================
        # JIRA CREATE ISSUE TOOL
        # ========================================
        class JiraCreateIssueInput(BaseModel):
            summary: str = Field(
                description="Issue summary/title - brief description of the issue"
            )
            project_key: str | None = Field(
                default=None,
                description="JIRA project key (e.g., PROJ, DEV). If not provided, uses the configured default project."
            )
            issue_type: str = Field(
                default="Task",
                description="Type of issue: Task, Story, Bug, Epic, or Subtask"
            )
            description: str | None = Field(
                default=None,
                description="Detailed description of the issue. Supports plain text with line breaks."
            )
            priority: str | None = Field(
                default=None,
                description="Priority level: Highest, High, Medium, Low, or Lowest"
            )
            assignee: str | None = Field(
                default=None,
                description="Assignee - account ID or email address"
            )
            labels: str | None = Field(
                default=None,
                description="Comma-separated list of labels (e.g., 'backend,urgent,bug')"
            )
            due_date: str | None = Field(
                default=None,
                description="Due date in YYYY-MM-DD format (e.g., '2025-03-15')"
            )
            components: str | None = Field(
                default=None,
                description="Comma-separated list of component names (e.g., 'API,Backend')"
            )

        jira_create_issue_tool = StructuredTool.from_function(
            name="jira_create_issue",
            description="""Create a new JIRA issue.

Required fields:
- summary: Brief title/summary of the issue

Optional fields:
- project_key: Project key (e.g., "PROJ"). Uses configured default if not provided.
- issue_type: Task (default), Story, Bug, Epic, or Subtask
- description: Detailed description with context
- priority: Highest, High, Medium, Low, or Lowest
- assignee: Account ID or email of the person to assign
- labels: Comma-separated labels (e.g., "backend,urgent")
- due_date: Due date in YYYY-MM-DD format
- components: Comma-separated component names

IMPORTANT: Only use this tool for actions that were APPROVED by the user.""",
            args_schema=JiraCreateIssueInput,
            func=lambda **kwargs: self._create_issue(**kwargs),
            return_direct=False,
            tags=["jira_create_issue", "jira", "write"],
        )

        # ========================================
        # JIRA UPDATE ISSUE TOOL
        # ========================================
        class JiraUpdateIssueInput(BaseModel):
            issue_key: str = Field(
                description="JIRA issue key (e.g., PROJ-123)"
            )
            summary: str | None = Field(
                default=None,
                description="New summary/title for the issue"
            )
            description: str | None = Field(
                default=None,
                description="New description for the issue. Supports plain text with line breaks."
            )
            priority: str | None = Field(
                default=None,
                description="New priority: Highest, High, Medium, Low, or Lowest"
            )
            assignee: str | None = Field(
                default=None,
                description="New assignee - account ID or email address"
            )
            labels: str | None = Field(
                default=None,
                description="New labels (comma-separated). Replaces existing labels. Use empty string to clear."
            )
            due_date: str | None = Field(
                default=None,
                description="New due date in YYYY-MM-DD format (e.g., '2025-03-15')"
            )
            components: str | None = Field(
                default=None,
                description="New components (comma-separated). Replaces existing. Use empty string to clear."
            )

        jira_update_issue_tool = StructuredTool.from_function(
            name="jira_update_issue",
            description="""Update fields on an existing JIRA issue.

Required:
- issue_key: The issue to update (e.g., "PROJ-123")

Optional fields (provide at least one):
- summary: New title/summary
- description: New detailed description
- priority: Highest, High, Medium, Low, or Lowest
- assignee: Account ID or email of new assignee
- labels: Comma-separated labels (replaces existing)
- due_date: Due date in YYYY-MM-DD format
- components: Comma-separated component names (replaces existing)

Note: Only provided fields will be updated. Others remain unchanged.

IMPORTANT: Only use this tool for changes that were APPROVED by the user.""",
            args_schema=JiraUpdateIssueInput,
            func=lambda **kwargs: self._update_issue(**kwargs),
            return_direct=False,
            tags=["jira_update_issue", "jira", "write"],
        )

        # ========================================
        # JIRA ADD COMMENT TOOL
        # ========================================
        class JiraAddCommentInput(BaseModel):
            issue_key: str = Field(
                description="JIRA issue key (e.g., PROJ-123)"
            )
            comment: str = Field(
                description="Comment text to add. Supports plain text with line breaks for formatting."
            )

        jira_add_comment_tool = StructuredTool.from_function(
            name="jira_add_comment",
            description="""Add a comment to a JIRA issue.

Use this to add comments that document:
- Decisions from meetings or Slack discussions
- Status updates or progress notes
- Information about blockers or dependencies
- Meeting notes or action items
- Links to related discussions

The comment supports plain text with line breaks for formatting.

IMPORTANT: Only use this tool for comments that were APPROVED by the user.""",
            args_schema=JiraAddCommentInput,
            func=lambda **kwargs: self._add_comment(**kwargs),
            return_direct=False,
            tags=["jira_add_comment", "jira", "write"],
        )

        # ========================================
        # JIRA TRANSITION ISSUE TOOL
        # ========================================
        class JiraTransitionIssueInput(BaseModel):
            issue_key: str = Field(
                description="JIRA issue key (e.g., PROJ-123)"
            )
            transition_name: str = Field(
                description="Target status name (e.g., 'In Progress', 'Done', 'To Do', 'In Review', 'Blocked')"
            )

        jira_transition_issue_tool = StructuredTool.from_function(
            name="jira_transition_issue",
            description="""Transition a JIRA issue to a new workflow status.

Use this to change the status of an issue:
- "To Do" - Work not started
- "In Progress" - Work actively being done
- "In Review" - Work completed, awaiting review
- "Done" - Work completed and verified
- "Blocked" - Work blocked by dependencies

Note: Available transitions depend on the project's workflow configuration.
The tool will return available transitions if the requested one is not valid.

IMPORTANT: Only use this tool for status changes that were APPROVED by the user.""",
            args_schema=JiraTransitionIssueInput,
            func=lambda **kwargs: self._transition_issue(**kwargs),
            return_direct=False,
            tags=["jira_transition_issue", "jira", "write"],
        )

        self.status = "JIRA Writer Tools ready"
        return [
            jira_search_users_tool,
            jira_create_issue_tool,
            jira_update_issue_tool,
            jira_add_comment_tool,
            jira_transition_issue_tool,
        ]
