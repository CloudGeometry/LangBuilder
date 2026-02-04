"""
JIRA State Fetcher Component (Read-Only)

Automatically fetches ALL JIRA tickets from a project without requiring any input.
This component is designed for the Enrichment Module - it provides the current
state of JIRA that the LLM will compare against Slack messages and meeting transcripts.

Features:
- No input required - runs automatically on execution
- Fetches all tickets from configured project
- Optionally fetches detailed info for each ticket
- Outputs formatted data compatible with JIRA Enrichment Module
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any

import httpx
from loguru import logger

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import (
    BoolInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.message import Message


class JiraStateFetcherComponent(Component):
    """Fetch current JIRA state automatically (read-only).

    This component connects to JIRA via MCP server and fetches all tickets
    from the configured project. No input required - it runs automatically.

    Output is formatted for the JIRA Enrichment Module.
    """

    display_name = "JIRA State Fetcher"
    description = "Automatically fetches all JIRA tickets from a project (read-only, no input required)."
    icon = "database"
    name = "JiraStateFetcher"

    # Class-level session cache for MCP connections
    _mcp_sessions: dict[str, str] = {}

    inputs = [
        # === MCP Server Configuration ===
        StrInput(
            name="mcp_endpoint",
            display_name="MCP Server URL",
            info="URL of the mcp-atlassian server.",
            value="http://mcp-atlassian-alb-1010564853.us-west-2.elb.amazonaws.com",
            required=True,
        ),

        # === Atlassian Credentials ===
        StrInput(
            name="atlassian_url",
            display_name="Atlassian URL",
            info="Your Atlassian Cloud URL (e.g., https://yourcompany.atlassian.net).",
            required=False,
        ),
        StrInput(
            name="atlassian_email",
            display_name="Atlassian Email",
            info="Email for Atlassian authentication.",
            required=False,
        ),
        SecretStrInput(
            name="atlassian_api_token",
            display_name="Atlassian API Token",
            info="API token for Atlassian authentication.",
            required=False,
        ),

        # === Project Configuration ===
        MessageTextInput(
            name="project_key",
            display_name="JIRA Project Key",
            info="The JIRA project key to fetch tickets from (e.g., PROJ, CLOUD).",
            value="PROJ",
            required=True,
        ),
        MessageTextInput(
            name="jql_filter",
            display_name="Additional JQL Filter",
            info="Optional additional JQL filter (e.g., 'status != Done'). Will be AND'd with project filter.",
            required=False,
            advanced=True,
        ),

        # === Fetch Options ===
        IntInput(
            name="max_tickets",
            display_name="Max Tickets",
            value=100,
            info="Maximum number of tickets to fetch.",
            advanced=True,
        ),
        BoolInput(
            name="fetch_details",
            display_name="Fetch Full Details",
            info="If true, fetches full details for each ticket (slower but more complete).",
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
            info="Include recent comments for each ticket.",
            value=False,
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

    def _get_auth_headers(self) -> dict[str, str]:
        """Build auth headers from credentials."""
        email = getattr(self, "atlassian_email", None)
        token = getattr(self, "atlassian_api_token", None)
        url = getattr(self, "atlassian_url", None)

        if not email or not token:
            return {}

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
        """Get the full MCP endpoint URL."""
        base_url = self.mcp_endpoint.rstrip("/")
        return f"{base_url}/mcp"

    async def _initialize_mcp_session(self, client: httpx.AsyncClient) -> str:
        """Initialize MCP session and return session ID."""
        mcp_url = self._get_mcp_url()

        if mcp_url in self._mcp_sessions:
            return self._mcp_sessions[mcp_url]

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "jira-state-fetcher",
                    "version": "1.0.0",
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self._get_auth_headers(),
        }

        response = await client.post(
            mcp_url,
            json=init_request,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise ValueError(f"MCP initialization failed: {response.status_code} - {response.text}")

        session_id = response.headers.get("Mcp-Session-Id")
        if not session_id:
            text = response.text
            if "event: message" in text:
                session_id = "no-session-required"
            else:
                raise ValueError("MCP server did not return session ID")

        self._mcp_sessions[mcp_url] = session_id
        return session_id

    async def _call_mcp_tool(
        self,
        client: httpx.AsyncClient,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        mcp_url = self._get_mcp_url()

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 2,
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

        response = await client.post(
            mcp_url,
            json=mcp_request,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            self._mcp_sessions.pop(mcp_url, None)
            raise ValueError(f"MCP call failed: {response.status_code} - {response.text}")

        # Parse response
        text = response.text
        if text.startswith("event:"):
            for line in text.split("\n"):
                if line.startswith("data:"):
                    json_str = line[5:].strip()
                    result = json.loads(json_str)
                    break
            else:
                raise ValueError(f"Could not parse SSE response: {text[:200]}")
        else:
            result = response.json()

        if "error" in result:
            error = result["error"]
            raise ValueError(f"MCP error: {error.get('message', 'Unknown error')}")

        return result.get("result", {})

    def _parse_mcp_text_response(self, result: dict) -> list[dict]:
        """Parse MCP text response to extract issues.

        MCP server returns data in various formats:
        1. Markdown table format
        2. JSON in text
        3. Direct JSON

        This method handles all formats.
        """
        issues = []

        # Try direct issues array first
        if "issues" in result:
            return result["issues"]

        # Check for content array (MCP text response format)
        if "content" not in result:
            return issues

        content = result.get("content", [])
        if not isinstance(content, list) or not content:
            return issues

        text_content = content[0].get("text", "") if content else ""

        if not text_content:
            return issues

        logger.debug(f"Raw MCP response text (first 500 chars): {text_content[:500]}")

        # Try parsing as JSON first
        try:
            parsed = json.loads(text_content)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "issues" in parsed:
                return parsed["issues"]
        except json.JSONDecodeError:
            pass

        # Parse markdown table format
        # Format: | Key | Summary | Status | Type | Priority | Assignee |
        if "|" in text_content and "---" in text_content:
            issues = self._parse_markdown_table(text_content)
            if issues:
                return issues

        # Parse line-by-line format (fallback)
        # Format: "KEY-123: Summary [Status]" or similar
        issues = self._parse_line_format(text_content)

        return issues

    def _parse_markdown_table(self, text: str) -> list[dict]:
        """Parse markdown table format from MCP response."""
        issues = []
        lines = text.strip().split("\n")

        # Find header line
        header_idx = -1
        headers = []
        for i, line in enumerate(lines):
            if "|" in line and "---" not in line:
                # This might be the header
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells and any(h.lower() in ["key", "summary", "status", "type"] for h in cells):
                    headers = [h.lower().replace(" ", "_") for h in cells]
                    header_idx = i
                    break

        if header_idx < 0 or not headers:
            return issues

        # Skip separator line (---) and parse data rows
        for line in lines[header_idx + 1:]:
            if "---" in line or not line.strip():
                continue
            if "|" not in line:
                continue

            cells = [c.strip() for c in line.split("|")]
            # Remove empty cells from edges
            cells = [c for c in cells if c]

            if len(cells) >= len(headers):
                issue = {}
                for j, header in enumerate(headers):
                    if j < len(cells):
                        value = cells[j]
                        # Map common header names to our expected format
                        if header in ["key", "issue_key"]:
                            issue["key"] = value
                        elif header in ["summary", "title"]:
                            issue["summary"] = value
                        elif header == "status":
                            issue["status"] = value
                        elif header in ["type", "issue_type", "issuetype"]:
                            issue["issue_type"] = value
                        elif header == "priority":
                            issue["priority"] = value
                        elif header == "assignee":
                            issue["assignee"] = value
                        elif header == "reporter":
                            issue["reporter"] = value
                        elif header == "created":
                            issue["created"] = value
                        elif header == "updated":
                            issue["updated"] = value
                        elif header in ["labels", "label"]:
                            issue["labels"] = [l.strip() for l in value.split(",") if l.strip()]
                        else:
                            issue[header] = value

                if issue.get("key"):
                    issues.append(issue)

        logger.info(f"Parsed {len(issues)} issues from markdown table")
        return issues

    def _parse_line_format(self, text: str) -> list[dict]:
        """Parse line-by-line format from MCP response."""
        issues = []

        # Pattern: KEY-123 or similar issue keys
        key_pattern = re.compile(r'\b([A-Z]+-\d+)\b')

        # Try to find blocks of issue data
        current_issue = {}

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                if current_issue.get("key"):
                    issues.append(current_issue)
                    current_issue = {}
                continue

            # Look for issue key
            key_match = key_pattern.search(line)
            if key_match:
                if current_issue.get("key"):
                    issues.append(current_issue)
                current_issue = {"key": key_match.group(1)}

                # Try to extract summary from the same line
                # Format might be: "KEY-123: Summary text" or "KEY-123 - Summary text"
                remainder = line[key_match.end():].strip()
                if remainder.startswith(":") or remainder.startswith("-"):
                    current_issue["summary"] = remainder[1:].strip()
                elif remainder:
                    current_issue["summary"] = remainder

            # Look for field patterns: "Field: Value"
            if ":" in line and current_issue.get("key"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    field = parts[0].strip().lower().replace(" ", "_")
                    value = parts[1].strip()
                    if field in ["status", "type", "priority", "assignee", "reporter", "summary", "description"]:
                        current_issue[field] = value

        # Don't forget the last issue
        if current_issue.get("key"):
            issues.append(current_issue)

        logger.info(f"Parsed {len(issues)} issues from line format")
        return issues

    async def _fetch_all_tickets(self) -> dict[str, Any]:
        """Fetch all tickets from the configured project."""
        # Build JQL query
        jql = f"project = {self.project_key}"
        if self.jql_filter and self.jql_filter.strip():
            jql += f" AND ({self.jql_filter})"

        # Order by updated date to get most recent first
        jql += " ORDER BY updated DESC"

        logger.info(f"Fetching JIRA tickets with JQL: {jql}")

        async with httpx.AsyncClient() as client:
            session_id = await self._initialize_mcp_session(client)

            # Search for tickets
            search_result = await self._call_mcp_tool(
                client,
                session_id,
                "jira_search",
                {"jql": jql, "limit": self.max_tickets},
            )

            # Parse the MCP response - handles markdown tables, JSON, etc.
            issues = self._parse_mcp_text_response(search_result)

            logger.info(f"Found {len(issues)} tickets")

            tickets = []

            # Process each ticket
            for issue in issues:
                ticket_data = self._normalize_ticket_data(issue)

                # Optionally fetch full details for each ticket
                if self.fetch_details and ticket_data.get("key"):
                    try:
                        detail_result = await self._call_mcp_tool(
                            client,
                            session_id,
                            "jira_get_issue",
                            {"issue_key": ticket_data["key"]},
                        )
                        # Parse detail response
                        detail_issues = self._parse_mcp_text_response(detail_result)
                        if detail_issues:
                            ticket_data = self._normalize_ticket_data(detail_issues[0], is_detail=True)
                        else:
                            # Try direct parsing for single issue
                            ticket_data = self._extract_ticket_from_detail(detail_result, ticket_data)
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for {ticket_data.get('key')}: {e}")

                tickets.append(ticket_data)

            return {
                "project_key": self.project_key,
                "total_tickets": len(tickets),
                "jql_query": jql,
                "tickets": tickets,
            }

    def _normalize_ticket_data(self, issue: dict, is_detail: bool = False) -> dict:
        """Normalize ticket data from various formats to consistent structure."""
        # Handle nested fields format (standard Jira API response)
        fields = issue.get("fields", {})

        # If fields exists and has data, use it
        if fields:
            ticket = {
                "key": issue.get("key", ""),
                "id": issue.get("id", ""),
                "summary": fields.get("summary", ""),
                "status": self._extract_nested_value(fields.get("status"), "name"),
                "issue_type": self._extract_nested_value(fields.get("issuetype"), "name"),
                "priority": self._extract_nested_value(fields.get("priority"), "name"),
                "assignee": self._extract_user(fields.get("assignee")),
                "reporter": self._extract_user(fields.get("reporter")),
                "created": fields.get("created", ""),
                "updated": fields.get("updated", ""),
                "due_date": fields.get("duedate", ""),
                "labels": fields.get("labels", []),
            }

            if self.include_description:
                description = fields.get("description", "")
                if isinstance(description, dict):
                    ticket["description"] = self._extract_adf_text(description)
                else:
                    ticket["description"] = description or ""
        else:
            # Flat format (from markdown table or simplified response)
            ticket = {
                "key": issue.get("key", ""),
                "id": issue.get("id", ""),
                "summary": issue.get("summary", ""),
                "status": issue.get("status", ""),
                "issue_type": issue.get("issue_type", issue.get("type", "")),
                "priority": issue.get("priority", ""),
                "assignee": issue.get("assignee", "Unassigned"),
                "reporter": issue.get("reporter", "Unassigned"),
                "created": issue.get("created", ""),
                "updated": issue.get("updated", ""),
                "due_date": issue.get("due_date", issue.get("duedate", "")),
                "labels": issue.get("labels", []),
            }

            if self.include_description:
                ticket["description"] = issue.get("description", "")

        # Include comments if enabled and this is a detail fetch
        if self.include_comments and is_detail:
            comments_data = fields.get("comment", {}) if fields else issue.get("comments", {})
            comments = comments_data.get("comments", []) if isinstance(comments_data, dict) else []
            ticket["recent_comments"] = [
                {
                    "author": self._extract_user(c.get("author")),
                    "body": c.get("body", ""),
                    "created": c.get("created", ""),
                }
                for c in comments[-5:]  # Last 5 comments
            ]

        return ticket

    def _extract_ticket_from_detail(self, detail_result: dict, existing_data: dict) -> dict:
        """Extract ticket data from a detail response, merging with existing data."""
        ticket = existing_data.copy()

        # Check for content array
        if "content" in detail_result:
            content = detail_result.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")

                # Try JSON parse
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return self._normalize_ticket_data(parsed, is_detail=True)
                except json.JSONDecodeError:
                    pass

                # Parse text format for additional fields
                for line in text.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        parts = line.split(":", 1)
                        field = parts[0].strip().lower().replace(" ", "_")
                        value = parts[1].strip()

                        if field == "summary" and value:
                            ticket["summary"] = value
                        elif field == "status" and value:
                            ticket["status"] = value
                        elif field in ["type", "issue_type"] and value:
                            ticket["issue_type"] = value
                        elif field == "priority" and value:
                            ticket["priority"] = value
                        elif field == "assignee" and value:
                            ticket["assignee"] = value
                        elif field == "reporter" and value:
                            ticket["reporter"] = value
                        elif field == "description" and value and self.include_description:
                            ticket["description"] = value

        return ticket

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

    def _extract_adf_text(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not adf or not isinstance(adf, dict):
            return ""

        texts = []
        content = adf.get("content", [])

        for block in content:
            if block.get("type") == "paragraph":
                for item in block.get("content", []):
                    if item.get("type") == "text":
                        texts.append(item.get("text", ""))
            elif block.get("type") == "text":
                texts.append(block.get("text", ""))

        return " ".join(texts)

    def _format_output(self, jira_data: dict) -> str:
        """Format JIRA data for the Enrichment Module."""
        from datetime import datetime

        output = {
            "project": jira_data["project_key"],
            "total_tickets": jira_data["total_tickets"],
            "fetched_at": datetime.now().isoformat(),
            "tickets": []
        }

        for ticket in jira_data["tickets"]:
            formatted_ticket = {
                "key": ticket["key"],
                "summary": ticket["summary"],
                "status": ticket["status"],
                "type": ticket["issue_type"],
                "priority": ticket["priority"],
                "assignee": ticket["assignee"],
                "reporter": ticket["reporter"],
                "due_date": ticket["due_date"] or "Not set",
                "labels": ticket["labels"],
            }

            if self.include_description and ticket.get("description"):
                formatted_ticket["description"] = ticket["description"][:500]  # Truncate long descriptions

            if self.include_comments and ticket.get("recent_comments"):
                formatted_ticket["recent_comments"] = ticket["recent_comments"]

            output["tickets"].append(formatted_ticket)

        return json.dumps(output, indent=2)

    def fetch_jira_state(self) -> Message:
        """
        Fetch all JIRA tickets and return formatted state.

        This method runs automatically - no input required.
        """
        try:
            self.status = f"Fetching tickets from {self.project_key}..."

            # Run async fetch
            jira_data = asyncio.run(self._fetch_all_tickets())

            # Format output
            formatted_output = self._format_output(jira_data)

            self.status = f"Fetched {jira_data['total_tickets']} tickets from {self.project_key}"
            return Message(text=formatted_output)

        except Exception as e:
            logger.exception(f"Error fetching JIRA state: {e}")
            self.status = f"Error: {e}"

            # Return error as formatted JSON
            error_output = json.dumps({
                "error": str(e),
                "project": self.project_key,
                "total_tickets": 0,
                "tickets": []
            }, indent=2)

            return Message(text=error_output)
