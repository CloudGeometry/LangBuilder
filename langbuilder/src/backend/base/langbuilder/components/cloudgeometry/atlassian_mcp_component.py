"""
Atlassian MCP Component

Connect to Jira and Confluence via the mcp-atlassian MCP server.
Exposes 9 tools for Agent use: jira_search, jira_get_issue, jira_create_issue,
jira_update_issue, jira_transition_issue, confluence_search, confluence_get_page,
confluence_create_page, and confluence_update_page.

Architecture
============
LangBuilder Flow → AtlassianMCPComponent → mcp-atlassian server → Atlassian Cloud APIs

The component communicates with the MCP server using JSON-RPC 2.0 over HTTP
(streamable-http transport). Each request includes per-user credentials as
Authorization: Basic <base64(email:api_token)> headers. The MCP server holds
NO shared secrets — it operates in per-user auth mode (ATLASSIAN_OAUTH_ENABLE=true).

Authentication
==============
Per-user Basic Auth. Each user provides their own Atlassian email + API token
via component inputs (or tweaks at runtime). The component builds an
Authorization: Basic header and sends it with every MCP request.

If atlassian_email and atlassian_api_token are empty, the component falls back
to server-side auth (backward compatible with env-var credentials on the server).

Slack User Context
==================
Three optional Slack fields (slack_user_email, slack_user_id, slack_team_id)
provide user identity context from a Slack bridge integration. These are NOT
Slack API credentials — they enable:

1. Agent-level email context: Tool descriptions include the user's email so
   the LLM can formulate personalized JQL (e.g., assignee = "user@company.com").
2. Component-level substitution: {user_email}, {me}, and currentUser() in
   JQL/CQL are replaced with the actual email before sending to the MCP server.
   Critical for service account deployments where currentUser() would resolve
   to the service account, not the actual user.
3. Result metadata: Every result includes user_context with Slack IDs.

MCP Server Deployment
=====================
TEMPORARY — Current AWS Fargate deployment:
  ALB: http://mcp-atlassian-alb-1010564853.us-west-2.elb.amazonaws.com
  Service Discovery: atlassian.mcp.internal:9000 (VPC-internal)
  AWS Profile: ai-entourage
  CDK Stack: McpAtlassianStack (us-west-2)

Local Docker:
  docker run -p 9000:9000 -e ATLASSIAN_OAUTH_ENABLE=true \\
    -e JIRA_URL=https://cloudgeometry.atlassian.net \\
    -e CONFLUENCE_URL=https://cloudgeometry.atlassian.net/wiki \\
    mcp-atlassian --transport streamable-http --host 0.0.0.0 --port 9000

Repository: https://github.com/adubuc-cloudgeometry/mcp-atlassian (fork with per-user auth)
Upstream:   https://github.com/sooperset/mcp-atlassian
Supports:   Jira Cloud, Confluence Cloud, Server/Data Center
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from typing import TYPE_CHECKING, Any, Optional

import httpx
from langchain_core.tools import StructuredTool
from loguru import logger
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import (
    DropdownInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.data import Data

if TYPE_CHECKING:
    pass


class AtlassianMCPComponent(LCToolComponent):
    """Connect to Atlassian via community MCP server (mcp-atlassian).

    **Setup:**
    1. Run the mcp-atlassian Docker container (see microservice folder)
    2. Configure MCP endpoint URL (default: http://localhost:9000)
    3. The MCP server handles Atlassian authentication via its own config

    **Features:**
    - Access Jira (search, get, create, update, transition issues)
    - Access Confluence (search, get, create, update pages)
    - Slack user context support for personalized queries
    - Works with Cloud and Server/Data Center

    **Note:** Authentication is handled by the mcp-atlassian server.
    Configure JIRA_API_TOKEN and CONFLUENCE_API_TOKEN in the server's .env file.
    """

    display_name = "Atlassian MCP"
    description = "Access Jira and Confluence via mcp-atlassian server"
    documentation = "https://github.com/sooperset/mcp-atlassian"
    icon = "Jira"
    name = "AtlassianMCP"

    # Class-level session cache for MCP connections
    _mcp_sessions: dict[str, str] = {}

    inputs = [
        # === MCP Server Configuration ===
        StrInput(
            name="mcp_endpoint",
            display_name="MCP Server URL",
            info="URL of the mcp-atlassian server. "
                 "TEMPORARY default points to CG AWS Fargate deployment.",
            value="http://mcp-atlassian-alb-1010564853.us-west-2.elb.amazonaws.com",
            required=True,
        ),
        DropdownInput(
            name="transport",
            display_name="Transport",
            options=["sse", "http"],
            value="sse",
            info="MCP transport type (SSE recommended for stability)",
            advanced=True,
        ),

        # === Atlassian Credentials (per-user, sent per-request) ===
        StrInput(
            name="atlassian_url",
            display_name="Atlassian URL",
            info="Your Atlassian Cloud URL (e.g., https://yourcompany.atlassian.net). "
                 "Leave empty if server handles auth via env vars.",
            required=False,
        ),
        StrInput(
            name="atlassian_email",
            display_name="Atlassian Email",
            info="Email for Atlassian authentication (e.g., user@company.com).",
            required=False,
        ),
        SecretStrInput(
            name="atlassian_api_token",
            display_name="Atlassian API Token",
            info="API token for Atlassian authentication. "
                 "Generate at https://id.atlassian.com/manage-profile/security/api-tokens",
            required=False,
        ),

        # === User Context (from Slack via tweaks) ===
        StrInput(
            name="slack_user_id",
            display_name="Slack User ID",
            info="Passed automatically from Slack bridge via tweaks",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="slack_user_email",
            display_name="Slack User Email",
            info="Used for personalized JQL queries (e.g., 'my tickets')",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="slack_team_id",
            display_name="Slack Team ID",
            info="Slack workspace identifier",
            required=False,
            advanced=True,
        ),

        # === Tool Selection ===
        DropdownInput(
            name="tool_name",
            display_name="Atlassian Tool",
            options=[
                "jira_search",
                "jira_get_issue",
                "jira_create_issue",
                "jira_update_issue",
                "jira_transition_issue",
                "jira_add_comment",
                "confluence_search",
                "confluence_get_page",
                "confluence_create_page",
                "confluence_update_page",
                "confluence_add_comment",
            ],
            value="jira_search",
            info="Select the MCP tool to execute",
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="tool_arguments",
            display_name="Tool Arguments (JSON)",
            info="Arguments for the selected tool in JSON format",
            required=False,
            tool_mode=True,
        ),

        # === Advanced Settings ===
        IntInput(
            name="max_results",
            display_name="Max Results",
            value=50,
            info="Maximum results to return from searches",
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=30,
            info="Request timeout in seconds",
            advanced=True,
        ),
    ]

    def _get_auth_headers(self) -> dict[str, str]:
        """Build per-request auth headers from component credentials.

        Returns empty dict if no credentials configured, allowing
        backward compatibility with server-side auth via env vars.
        """
        email = getattr(self, "atlassian_email", None)
        token = getattr(self, "atlassian_api_token", None)
        url = getattr(self, "atlassian_url", None)

        if not email or not token:
            return {}

        # Resolve SecretStrInput to plain string
        token_str = token.get_secret_value() if hasattr(token, "get_secret_value") else str(token)

        encoded = base64.b64encode(f"{email}:{token_str}".encode()).decode()
        headers: dict[str, str] = {
            "Authorization": f"Basic {encoded}",
        }

        if url:
            base = url.rstrip("/")
            headers["X-Atlassian-Jira-Url"] = base
            headers["X-Atlassian-Confluence-Url"] = f"{base}/wiki"

        return headers

    def _get_mcp_url(self) -> str:
        """Get the full MCP endpoint URL.

        Note: Always uses /mcp endpoint (streamable-http) since it supports
        proper request/response with session management. The /sse endpoint
        is for SSE streaming which requires different client handling.
        """
        base_url = self.mcp_endpoint.rstrip("/")
        return f"{base_url}/mcp"

    async def _initialize_mcp_session(self, client: httpx.AsyncClient) -> str:
        """Initialize MCP session and return session ID.

        The MCP streamable-http transport requires session management:
        1. Call initialize to get a session ID from Mcp-Session-Id header
        2. Use that session ID in all subsequent requests

        Args:
            client: httpx AsyncClient to use for the request

        Returns:
            Session ID string

        Raises:
            ValueError: If initialization fails
        """
        mcp_url = self._get_mcp_url()

        # Key cache by (url, credentials) to prevent cross-user session reuse
        email = getattr(self, "atlassian_email", "") or ""
        cache_key = f"{mcp_url}|{hashlib.sha256(email.encode()).hexdigest()[:12]}"

        # Check if we have a cached session for this endpoint + user
        if cache_key in self._mcp_sessions:
            logger.debug(f"Using cached MCP session for {mcp_url}")
            return self._mcp_sessions[cache_key]

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "langbuilder-atlassian-mcp",
                    "version": "1.0.0",
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self._get_auth_headers(),
        }

        logger.debug(f"Initializing MCP session at {mcp_url}")

        response = await client.post(
            mcp_url,
            json=init_request,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            resp_text = response.text
            # Detect the specific OAuth fallback error when per-user credentials are missing
            if "OAuth authentication requires" in resp_text or "cloud_id" in resp_text:
                error_msg = (
                    "MCP server rejected request — no valid authentication. "
                    "Configure 'Atlassian Email' and 'Atlassian API Token' on this component. "
                    "The MCP server requires per-request Basic Auth credentials."
                )
            else:
                error_msg = f"MCP initialization failed: {response.status_code} - {resp_text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get session ID from response header
        session_id = response.headers.get("Mcp-Session-Id")
        if not session_id:
            # Try to parse from SSE response format
            text = response.text
            if "event: message" in text:
                # Parse SSE format - session ID should be in header, but check body too
                logger.warning("MCP session ID not in header, server may not support sessions")
                # Generate a placeholder - some MCP servers don't require sessions
                session_id = "no-session-required"
            else:
                error_msg = "MCP server did not return session ID"
                logger.error(error_msg)
                raise ValueError(error_msg)

        logger.info(f"MCP session initialized: {session_id[:16]}...")

        # Cache the session (keyed by url + user)
        self._mcp_sessions[cache_key] = session_id
        return session_id

    async def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on the mcp-atlassian server.

        Uses MCP streamable-http transport with proper session management.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If MCP call fails
        """
        mcp_url = self._get_mcp_url()

        async with httpx.AsyncClient() as client:
            # Initialize session first
            session_id = await self._initialize_mcp_session(client)

            # Build MCP JSON-RPC request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 2,  # Use different ID than initialize
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id,
                **self._get_auth_headers(),
            }

            logger.debug(f"Calling MCP tool {tool_name} at {mcp_url}")

            response = await client.post(
                mcp_url,
                json=mcp_request,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                # Clear cached session on error - it may have expired
                email = getattr(self, "atlassian_email", "") or ""
                evict_key = f"{mcp_url}|{hashlib.sha256(email.encode()).hexdigest()[:12]}"
                self._mcp_sessions.pop(evict_key, None)
                error_msg = f"MCP call failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Parse response - may be SSE format
            text = response.text
            if text.startswith("event:"):
                # Parse SSE format: "event: message\ndata: {...}"
                for line in text.split("\n"):
                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        result = json.loads(json_str)
                        break
                else:
                    raise ValueError(f"Could not parse SSE response: {text[:200]}")
            else:
                result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error = result["error"]
                raise ValueError(f"MCP error: {error.get('message', 'Unknown error')}")

            # Check for MCP tool-level error (isError in result content)
            mcp_result = result.get("result", {})
            if mcp_result.get("isError"):
                content = mcp_result.get("content", [])
                error_text = content[0].get("text", "Unknown error") if content else "Unknown error"
                if "OAuth authentication requires" in error_text or "cloud_id" in error_text:
                    raise ValueError(
                        "Atlassian authentication failed. "
                        "Configure 'Atlassian Email' and 'Atlassian API Token' on this component. "
                        f"Server response: {error_text}"
                    )
                raise ValueError(f"MCP tool error: {error_text}")

            return mcp_result

    async def _list_mcp_tools(self) -> list[dict]:
        """List available tools from MCP server.

        Returns:
            List of tool definitions
        """
        mcp_url = self._get_mcp_url()

        async with httpx.AsyncClient() as client:
            # Initialize session first
            session_id = await self._initialize_mcp_session(client)

            mcp_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id,
                **self._get_auth_headers(),
            }

            response = await client.post(
                mcp_url,
                json=mcp_request,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                # Parse response - may be SSE format
                text = response.text
                if text.startswith("event:"):
                    for line in text.split("\n"):
                        if line.startswith("data:"):
                            json_str = line[5:].strip()
                            result = json.loads(json_str)
                            break
                    else:
                        return []
                else:
                    result = response.json()
                return result.get("result", {}).get("tools", [])

        return []

    def _substitute_user_email(self, query: str) -> str:
        """Substitute user email placeholder in JQL/CQL queries.

        Supported placeholders:
        - {user_email} - Full email address
        - {me} - Alias for user email
        - currentUser() - JQL function (replaced when using service account)

        Args:
            query: Original JQL or CQL query

        Returns:
            Query with email substituted, or original if no email available
        """
        if not self.slack_user_email:
            logger.debug("No slack_user_email available for substitution")
            return query

        email = self.slack_user_email

        # Replace placeholders
        substitutions = [
            ("{user_email}", f'"{email}"'),
            ("{me}", f'"{email}"'),
            ("currentUser()", f'"{email}"'),
        ]

        result = query
        for placeholder, replacement in substitutions:
            if placeholder in result:
                result = result.replace(placeholder, replacement)
                logger.debug(f"Substituted {placeholder} with {replacement}")

        return result

    def run_model(self) -> Data:
        """Execute the selected Atlassian MCP tool.

        Returns:
            Data object with tool execution result
        """
        try:
            # Warn if credentials not configured
            if not getattr(self, "atlassian_email", None) or not getattr(self, "atlassian_api_token", None):
                logger.warning(
                    "Atlassian credentials not set on component — "
                    "requests will fail if MCP server requires per-user auth"
                )

            # Parse tool arguments
            arguments = {}
            if self.tool_arguments:
                try:
                    arguments = json.loads(self.tool_arguments)
                except json.JSONDecodeError as e:
                    self.status = "Error: invalid_json"
                    return Data(data={
                        "success": False,
                        "error": f"Invalid JSON in tool arguments: {e}",
                        "error_code": "invalid_json",
                    })

            # Apply email substitution for search queries
            if self.tool_name == "jira_search" and "jql" in arguments:
                original_jql = arguments["jql"]
                arguments["jql"] = self._substitute_user_email(original_jql)
                if arguments["jql"] != original_jql:
                    logger.info(f"JQL substitution: {original_jql} -> {arguments['jql']}")

            if self.tool_name == "confluence_search" and "query" in arguments:
                original_cql = arguments["query"]
                arguments["query"] = self._substitute_user_email(original_cql)
                if arguments["query"] != original_cql:
                    logger.info(f"CQL substitution: {original_cql} -> {arguments['query']}")

            # Apply limit to search operations (MCP server uses 'limit' not 'maxResults')
            if "search" in self.tool_name and "limit" not in arguments:
                arguments["limit"] = self.max_results

            # Execute MCP tool
            self.status = f"Executing {self.tool_name}..."
            result = asyncio.run(self._call_mcp_tool(self.tool_name, arguments))

            self.status = f"Completed {self.tool_name}"
            return Data(data={
                "success": True,
                "tool": self.tool_name,
                "result": result,
                "user_context": {
                    "slack_user_id": self.slack_user_id,
                    "slack_user_email": self.slack_user_email,
                    "email_substituted": self.slack_user_email is not None,
                },
            })

        except Exception as e:
            logger.exception(f"Error executing Atlassian MCP tool: {e}")
            self.status = f"Error: {e}"
            return Data(data={
                "success": False,
                "error": str(e),
                "error_code": "mcp_error",
            })

    async def _get_tools(self):
        """Override to return named tools from build_tool() instead of generic outputs.

        CRITICAL: Without this override, all tools get named "run_model" and
        Agents cannot distinguish between different component tools.
        """
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
            List of tools exposing Atlassian MCP operations
        """
        # Warn if credentials missing (tools will fail at runtime)
        if not getattr(self, "atlassian_email", None) or not getattr(self, "atlassian_api_token", None):
            logger.warning(
                "Building Atlassian tools without credentials — "
                "configure atlassian_email and atlassian_api_token for per-user auth"
            )

        # Build email context note for tool descriptions
        email_context = ""
        if self.slack_user_email:
            email_context = f"""

IMPORTANT: The current user's email is {self.slack_user_email}.
When the user says "my", "mine", or refers to themselves, use this email in queries.
Examples:
- "my tickets" → assignee = "{self.slack_user_email}"
- "bugs I created" → reporter = "{self.slack_user_email}"
You can also use {{user_email}} placeholder which will be auto-substituted."""

        # Jira Search Tool
        class JiraSearchInput(BaseModel):
            jql: str = Field(description="JQL query string (e.g., 'project = PROJ AND status = Open')")
            max_results: int = Field(default=50, description="Maximum results to return")

        def _jira_search(jql: str, max_results: int = 50) -> str:
            self.tool_name = "jira_search"
            self.tool_arguments = json.dumps({"jql": jql, "limit": max_results})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        jira_search_tool = StructuredTool.from_function(
            name="atlassian_jira_search",
            description=f"""Search Jira issues using JQL (Jira Query Language).

Common JQL patterns:
- assignee = "email" - Issues assigned to user
- reporter = "email" - Issues created by user
- project = KEY - Issues in a project
- status = "In Progress" - Issues by status
- type = Bug - Issues by type
- created >= -7d - Recent issues{email_context}""",
            args_schema=JiraSearchInput,
            func=_jira_search,
            return_direct=False,
            tags=["atlassian_jira_search"],
        )

        # Jira Get Issue Tool
        class JiraGetIssueInput(BaseModel):
            issue_key: str = Field(description="Jira issue key (e.g., PROJ-123)")

        def _jira_get_issue(issue_key: str) -> str:
            self.tool_name = "jira_get_issue"
            self.tool_arguments = json.dumps({"issue_key": issue_key})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        jira_get_issue_tool = StructuredTool.from_function(
            name="atlassian_jira_get_issue",
            description="Get details of a specific Jira issue by key (e.g., PROJ-123).",
            args_schema=JiraGetIssueInput,
            func=_jira_get_issue,
            return_direct=False,
            tags=["atlassian_jira_get_issue"],
        )

        # Jira Create Issue Tool
        class JiraCreateIssueInput(BaseModel):
            project_key: str = Field(description="Project key (e.g., PROJ)")
            summary: str = Field(description="Issue summary/title")
            issue_type: str = Field(default="Task", description="Issue type (Task, Bug, Story, etc.)")
            description: str = Field(default="", description="Issue description")

        def _jira_create_issue(
            project_key: str,
            summary: str,
            issue_type: str = "Task",
            description: str = "",
        ) -> str:
            self.tool_name = "jira_create_issue"
            self.tool_arguments = json.dumps({
                "project_key": project_key,
                "summary": summary,
                "issue_type": issue_type,
                "description": description,
            })
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        jira_create_issue_tool = StructuredTool.from_function(
            name="atlassian_jira_create_issue",
            description="Create a new Jira issue in a project.",
            args_schema=JiraCreateIssueInput,
            func=_jira_create_issue,
            return_direct=False,
            tags=["atlassian_jira_create_issue"],
        )

        # Confluence Search Tool
        class ConfluenceSearchInput(BaseModel):
            cql: str = Field(description="CQL query string (e.g., 'space = SPACE AND type = page')")
            max_results: int = Field(default=25, description="Maximum results to return")

        def _confluence_search(cql: str, max_results: int = 25) -> str:
            self.tool_name = "confluence_search"
            self.tool_arguments = json.dumps({"query": cql, "limit": max_results})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        confluence_search_tool = StructuredTool.from_function(
            name="atlassian_confluence_search",
            description=f"""Search Confluence pages using CQL (Confluence Query Language).

Common CQL patterns:
- creator = "email" - Pages created by user
- contributor = "email" - Pages edited by user
- space = KEY - Pages in a space
- type = page - Only pages (not blogs)
- title ~ "keyword" - Title contains keyword{email_context}""",
            args_schema=ConfluenceSearchInput,
            func=_confluence_search,
            return_direct=False,
            tags=["atlassian_confluence_search"],
        )

        # Confluence Get Page Tool
        class ConfluenceGetPageInput(BaseModel):
            page_id: str = Field(description="Confluence page ID")

        def _confluence_get_page(page_id: str) -> str:
            self.tool_name = "confluence_get_page"
            self.tool_arguments = json.dumps({"page_id": page_id})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        confluence_get_page_tool = StructuredTool.from_function(
            name="atlassian_confluence_get_page",
            description="Get content of a specific Confluence page by ID.",
            args_schema=ConfluenceGetPageInput,
            func=_confluence_get_page,
            return_direct=False,
            tags=["atlassian_confluence_get_page"],
        )

        # Jira Update Issue Tool
        class JiraUpdateIssueInput(BaseModel):
            issue_key: str = Field(description="Jira issue key (e.g., PROJ-123)")
            fields: str = Field(
                description="JSON string of fields to update. Example: "
                "'{\"summary\": \"New title\", \"description\": \"New desc\", \"assignee\": \"user@example.com\"}'"
            )

        def _jira_update_issue(issue_key: str, fields: str) -> str:
            self.tool_name = "jira_update_issue"
            try:
                fields_dict = json.loads(fields)
            except json.JSONDecodeError:
                return "Error: fields must be a valid JSON string"
            self.tool_arguments = json.dumps({
                "issue_key": issue_key,
                "fields": fields_dict,
            })
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        jira_update_issue_tool = StructuredTool.from_function(
            name="atlassian_jira_update_issue",
            description="Update an existing Jira issue. Pass fields as a JSON string with keys like 'summary', 'description', 'assignee' (email), 'priority', etc. Only provided fields are changed.",
            args_schema=JiraUpdateIssueInput,
            func=_jira_update_issue,
            return_direct=False,
            tags=["atlassian_jira_update_issue"],
        )

        # Jira Transition Issue Tool
        class JiraTransitionIssueInput(BaseModel):
            issue_key: str = Field(description="Jira issue key (e.g., PROJ-123)")
            target_status: str = Field(
                description="Target status name (e.g., 'In Progress', 'Done', 'To Do') "
                "OR a numeric transition ID (e.g., '31'). Status names are resolved "
                "automatically — prefer using the status name."
            )
            comment: Optional[str] = Field(
                default=None, description="Optional comment to add during the transition"
            )

        def _resolve_transition_id(issue_key: str, target_status: str) -> str:
            """Resolve a status name to a transition ID by querying available transitions."""
            self.tool_name = "jira_get_transitions"
            self.tool_arguments = json.dumps({"issue_key": issue_key})
            result = self.run_model()
            if result.data.get("error"):
                raise ValueError(f"Failed to get transitions: {result.data['error']}")

            mcp_result = result.data.get("result", {})
            content = mcp_result.get("content", [])
            if not content:
                raise ValueError("No transition data returned from Jira")

            transitions_text = content[0].get("text", "[]") if content else "[]"
            transitions = json.loads(transitions_text) if isinstance(transitions_text, str) else transitions_text

            # Match by target status name (case-insensitive)
            target_lower = target_status.lower().strip()
            for t in transitions:
                to_status = t.get("to", {}).get("name", "") if isinstance(t.get("to"), dict) else ""
                if to_status.lower().strip() == target_lower:
                    return str(t["id"])
                # Also match on transition name itself
                if t.get("name", "").lower().strip() == target_lower:
                    return str(t["id"])

            available = [
                f"{t.get('name', '?')} (id={t.get('id', '?')}) → {t.get('to', {}).get('name', '?')}"
                for t in transitions
            ]
            raise ValueError(
                f"No transition to '{target_status}' found. "
                f"Available transitions: {', '.join(available)}"
            )

        def _jira_transition_issue(
            issue_key: str,
            target_status: str,
            comment: Optional[str] = None,
        ) -> str:
            # Resolve status name to transition ID if not numeric
            if target_status.strip().isdigit():
                transition_id = target_status.strip()
            else:
                try:
                    transition_id = _resolve_transition_id(issue_key, target_status)
                    logger.info(f"Resolved '{target_status}' to transition_id={transition_id} for {issue_key}")
                except ValueError as e:
                    return f"Error: {e}"

            self.tool_name = "jira_transition_issue"
            args: dict[str, Any] = {
                "issue_key": issue_key,
                "transition_id": transition_id,
            }
            if comment is not None:
                args["comment"] = comment
            self.tool_arguments = json.dumps(args)
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"

            # Verify the transition actually changed the status
            mcp_result = result.data.get("result", {})
            content = mcp_result.get("content", [])
            if content:
                try:
                    issue_data = json.loads(content[0].get("text", "{}"))
                    new_status = issue_data.get("issue", {}).get("status", {}).get("name", "")
                    if new_status and not target_status.strip().isdigit():
                        if new_status.lower().strip() != target_status.lower().strip():
                            return (
                                f"Warning: Transition completed but status is '{new_status}', "
                                f"not '{target_status}'. The transition may have gone to an unexpected status."
                            )
                except (json.JSONDecodeError, AttributeError):
                    pass

            return json.dumps(mcp_result, indent=2)

        jira_transition_issue_tool = StructuredTool.from_function(
            name="atlassian_jira_transition_issue",
            description=(
                "Transition a Jira issue to a new status. Pass the target status name "
                "(e.g., 'In Progress', 'Done', 'To Do') and the correct transition will "
                "be resolved automatically. You can also pass a numeric transition ID directly."
            ),
            args_schema=JiraTransitionIssueInput,
            func=_jira_transition_issue,
            return_direct=False,
            tags=["atlassian_jira_transition_issue"],
        )

        # Confluence Create Page Tool
        class ConfluenceCreatePageInput(BaseModel):
            space_key: str = Field(description="Confluence space key (e.g., ENG, DEV)")
            title: str = Field(description="Page title")
            content: str = Field(description="Page content in markdown format (default) or storage format")
            parent_id: Optional[str] = Field(
                default=None, description="Parent page ID to create as a child page"
            )
            content_format: str = Field(
                default="markdown",
                description="Content format: 'markdown' (default), 'wiki', or 'storage'",
            )

        def _confluence_create_page(
            space_key: str,
            title: str,
            content: str,
            parent_id: Optional[str] = None,
            content_format: str = "markdown",
        ) -> str:
            self.tool_name = "confluence_create_page"
            args: dict[str, Any] = {
                "space_key": space_key,
                "title": title,
                "content": content,
                "content_format": content_format,
            }
            if parent_id is not None:
                args["parent_id"] = parent_id
            self.tool_arguments = json.dumps(args)
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        confluence_create_page_tool = StructuredTool.from_function(
            name="atlassian_confluence_create_page",
            description="Create a new Confluence page in a space. Content defaults to markdown format.",
            args_schema=ConfluenceCreatePageInput,
            func=_confluence_create_page,
            return_direct=False,
            tags=["atlassian_confluence_create_page"],
        )

        # Confluence Update Page Tool
        class ConfluenceUpdatePageInput(BaseModel):
            page_id: str = Field(description="Confluence page ID to update")
            title: str = Field(description="Updated page title")
            content: str = Field(description="Updated page content in markdown format (default) or storage format")
            content_format: str = Field(
                default="markdown",
                description="Content format: 'markdown' (default), 'wiki', or 'storage'",
            )
            version_comment: Optional[str] = Field(
                default=None, description="Optional comment for this version"
            )
            is_minor_edit: bool = Field(
                default=False, description="Whether this is a minor edit"
            )

        def _confluence_update_page(
            page_id: str,
            title: str,
            content: str,
            content_format: str = "markdown",
            version_comment: Optional[str] = None,
            is_minor_edit: bool = False,
        ) -> str:
            self.tool_name = "confluence_update_page"
            args: dict[str, Any] = {
                "page_id": page_id,
                "title": title,
                "content": content,
                "content_format": content_format,
                "is_minor_edit": is_minor_edit,
            }
            if version_comment is not None:
                args["version_comment"] = version_comment
            self.tool_arguments = json.dumps(args)
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        confluence_update_page_tool = StructuredTool.from_function(
            name="atlassian_confluence_update_page",
            description="Update an existing Confluence page. Replaces the title and content. Supports markdown (default), wiki, or storage format.",
            args_schema=ConfluenceUpdatePageInput,
            func=_confluence_update_page,
            return_direct=False,
            tags=["atlassian_confluence_update_page"],
        )

        # Jira Add Comment Tool
        class JiraAddCommentInput(BaseModel):
            issue_key: str = Field(description="Jira issue key (e.g., PROJ-123)")
            comment: str = Field(description="Comment text in Markdown format")

        def _jira_add_comment(issue_key: str, comment: str) -> str:
            self.tool_name = "jira_add_comment"
            self.tool_arguments = json.dumps({"issue_key": issue_key, "comment": comment})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        jira_add_comment_tool = StructuredTool.from_function(
            name="atlassian_jira_add_comment",
            description="Add a comment to a Jira issue.",
            args_schema=JiraAddCommentInput,
            func=_jira_add_comment,
            return_direct=False,
            tags=["atlassian_jira_add_comment"],
        )

        # Confluence Add Comment Tool
        class ConfluenceAddCommentInput(BaseModel):
            page_id: str = Field(description="Confluence page ID")
            content: str = Field(description="Comment content in Markdown format")

        def _confluence_add_comment(page_id: str, content: str) -> str:
            self.tool_name = "confluence_add_comment"
            self.tool_arguments = json.dumps({"page_id": page_id, "content": content})
            result = self.run_model()
            if result.data.get("error"):
                return f"Error: {result.data['error']}"
            return json.dumps(result.data.get("result", {}), indent=2)

        confluence_add_comment_tool = StructuredTool.from_function(
            name="atlassian_confluence_add_comment",
            description="Add a comment to a Confluence page.",
            args_schema=ConfluenceAddCommentInput,
            func=_confluence_add_comment,
            return_direct=False,
            tags=["atlassian_confluence_add_comment"],
        )

        self.status = "Tools built"
        return [
            jira_search_tool,
            jira_get_issue_tool,
            jira_create_issue_tool,
            jira_update_issue_tool,
            jira_transition_issue_tool,
            jira_add_comment_tool,
            confluence_search_tool,
            confluence_get_page_tool,
            confluence_create_page_tool,
            confluence_update_page_tool,
            confluence_add_comment_tool,
        ]
