"""
Atlassian MCP Component

Connect to community mcp-atlassian server for Jira and Confluence access.
Uses API token authentication via a self-hosted MCP server.

Repository: https://github.com/sooperset/mcp-atlassian
Supports: Jira Cloud, Confluence Cloud, Server/Data Center
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

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
    - Access Jira (search, get, create, update issues)
    - Access Confluence (search, get, create pages)
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
            info="URL of the mcp-atlassian server (e.g., http://localhost:9000)",
            value="http://localhost:9000",
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

        # Check if we have a cached session for this endpoint
        if mcp_url in self._mcp_sessions:
            logger.debug(f"Using cached MCP session for {mcp_url}")
            return self._mcp_sessions[mcp_url]

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
        }

        logger.debug(f"Initializing MCP session at {mcp_url}")

        response = await client.post(
            mcp_url,
            json=init_request,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            error_msg = f"MCP initialization failed: {response.status_code} - {response.text}"
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

        # Cache the session
        self._mcp_sessions[mcp_url] = session_id
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
                self._mcp_sessions.pop(mcp_url, None)
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

            return result.get("result", {})

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

            if self.tool_name == "confluence_search" and "cql" in arguments:
                original_cql = arguments["cql"]
                arguments["cql"] = self._substitute_user_email(original_cql)
                if arguments["cql"] != original_cql:
                    logger.info(f"CQL substitution: {original_cql} -> {arguments['cql']}")

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
            self.tool_arguments = json.dumps({"issueKey": issue_key})
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
                "projectKey": project_key,
                "summary": summary,
                "issueType": issue_type,
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
            self.tool_arguments = json.dumps({"cql": cql, "limit": max_results})
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
            self.tool_arguments = json.dumps({"pageId": page_id})
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

        self.status = "Tools built"
        return [
            jira_search_tool,
            jira_get_issue_tool,
            jira_create_issue_tool,
            confluence_search_tool,
            confluence_get_page_tool,
        ]
