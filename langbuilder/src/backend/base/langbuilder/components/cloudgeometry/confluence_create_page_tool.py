"""
Confluence Create Page Tool Component

Enables creating Confluence pages as an Agent tool.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import (
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.data import Data


class ConfluenceCreatePageToolComponent(LCToolComponent):
    """Create pages in Confluence Cloud.

    This component wraps Confluence page creation as a tool that can be
    used by LangBuilder Agents. It creates pages with markdown-to-ADF
    conversion.

    **Authentication:**
    - Set environment variables (CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN), OR
    - Provide credentials directly in the component

    **Usage:**
    - Connect to an Agent's tools input
    - Agent will call this to create PRD pages
    """

    display_name = "Confluence Create Page Tool"
    description = "Create pages in Confluence Cloud"
    documentation = "https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-content/#api-wiki-rest-api-content-post"
    icon = "Confluence"
    name = "ConfluenceCreatePageTool"

    inputs = [
        StrInput(
            name="base_url",
            display_name="Confluence Base URL",
            info="Confluence instance URL. Can also be set via CONFLUENCE_BASE_URL env var.",
            placeholder="https://yourcompany.atlassian.net/wiki",
            required=False,
        ),
        StrInput(
            name="space_key",
            display_name="Space Key",
            info="Confluence space key where pages will be created",
            placeholder="PRD",
            required=True,
        ),
        StrInput(
            name="email",
            display_name="Email",
            info="Confluence user email. Can also be set via CONFLUENCE_EMAIL env var.",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="api_token",
            display_name="API Token",
            info="Confluence API token. Can also be set via CONFLUENCE_API_TOKEN env var.",
            required=False,
            advanced=True,
        ),
    ]

    def run_model(self) -> Data:
        """Execute create - called when component is run directly (not as tool)."""
        return Data(data={
            "page_id": None,
            "page_url": None,
            "error": "This component is designed to be used as an Agent tool. Connect it to an Agent's tools input.",
        })

    def _markdown_to_adf(self, markdown_text: str) -> dict:
        """Convert markdown to Atlassian Document Format (ADF).

        This is a simplified converter that handles common markdown patterns.

        Args:
            markdown_text: Markdown formatted text

        Returns:
            dict: ADF document structure
        """
        content = []
        lines = markdown_text.split('\n')
        current_para = []

        for line in lines:
            stripped = line.strip()

            # Headers
            if stripped.startswith('# '):
                if current_para:
                    content.append(self._make_paragraph(current_para))
                    current_para = []
                content.append({
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": stripped[2:]}]
                })
            elif stripped.startswith('## '):
                if current_para:
                    content.append(self._make_paragraph(current_para))
                    current_para = []
                content.append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": stripped[3:]}]
                })
            elif stripped.startswith('### '):
                if current_para:
                    content.append(self._make_paragraph(current_para))
                    current_para = []
                content.append({
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": stripped[4:]}]
                })
            # Bullet points
            elif stripped.startswith('- ') or stripped.startswith('* '):
                if current_para:
                    content.append(self._make_paragraph(current_para))
                    current_para = []
                content.append({
                    "type": "bulletList",
                    "content": [{
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": stripped[2:]}]
                        }]
                    }]
                })
            # Empty line = new paragraph
            elif not stripped:
                if current_para:
                    content.append(self._make_paragraph(current_para))
                    current_para = []
            # Regular text
            else:
                current_para.append(stripped)

        # Don't forget remaining paragraph
        if current_para:
            content.append(self._make_paragraph(current_para))

        # Ensure at least one paragraph
        if not content:
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": " "}]
            })

        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

    def _make_paragraph(self, lines: list) -> dict:
        """Create a paragraph from multiple lines."""
        text = ' '.join(lines)
        return {
            "type": "paragraph",
            "content": [{"type": "text", "text": text}]
        }

    def _do_create_page(self, title: str, content: str) -> dict:
        """Create a Confluence page.

        Args:
            title: Page title
            content: Page content in markdown

        Returns:
            dict: Result with page_id, page_url, and any errors
        """
        import base64
        import os

        try:
            import requests
        except ImportError as e:
            return {
                "page_id": None,
                "page_url": None,
                "error": f"Missing dependency: {e}. Install with: pip install requests",
            }

        # Get credentials (handle SecretStr objects)
        base_url = self.base_url or os.environ.get("CONFLUENCE_BASE_URL", "")

        email = self.email
        if hasattr(email, 'get_secret_value'):
            email = email.get_secret_value()
        email = email or os.environ.get("CONFLUENCE_EMAIL", "")

        api_token = self.api_token
        if hasattr(api_token, 'get_secret_value'):
            api_token = api_token.get_secret_value()
        api_token = api_token or os.environ.get("CONFLUENCE_API_TOKEN", "")

        if not base_url:
            return {"page_id": None, "page_url": None, "error": "Confluence base URL not configured"}
        if not email or not api_token:
            return {"page_id": None, "page_url": None, "error": "Confluence credentials not configured"}

        try:
            # Build auth
            credentials = f"{email}:{api_token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Convert markdown to ADF
            self.status = "Converting content..."
            adf_content = self._markdown_to_adf(content)

            # Create page
            self.status = "Creating page..."
            url = f"{base_url.rstrip('/')}/rest/api/content"

            payload = {
                "type": "page",
                "title": title,
                "space": {"key": self.space_key},
                "body": {
                    "atlas_doc_format": {
                        "value": adf_content,
                        "representation": "atlas_doc_format"
                    }
                }
            }

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code in (200, 201):
                data = response.json()
                page_id = data.get("id")
                # Build page URL
                page_url = f"{base_url.rstrip('/')}/pages/{page_id}"

                # Try to get the proper URL from _links
                if "_links" in data:
                    web_ui = data["_links"].get("webui", "")
                    if web_ui:
                        page_url = f"{base_url.rstrip('/')}{web_ui}"

                self.status = f"Created: {page_id}"
                return {
                    "page_id": page_id,
                    "page_url": page_url,
                    "error": None,
                }
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                except:
                    error_msg = response.text[:200]

                self.status = f"Error: {error_msg}"
                return {
                    "page_id": None,
                    "page_url": None,
                    "error": error_msg,
                }

        except Exception as e:
            self.status = f"Error: {e}"
            return {
                "page_id": None,
                "page_url": None,
                "error": str(e),
            }

    async def _get_tools(self):
        """Return named tool for Agent use."""
        tool = self.build_tool()
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """Build LangChain tool for Agent use."""

        class ConfluenceCreatePageInput(BaseModel):
            """Input schema for Confluence page creation."""
            title: str = Field(
                description="Page title (e.g., 'PRD: Feature Name')"
            )
            content: str = Field(
                description="Page content in markdown format"
            )

        def _create_page(title: str, content: str) -> str:
            """Inner function that Agent calls."""
            result = self._do_create_page(title, content)

            if result.get("error"):
                return f"Error creating page: {result['error']}"

            if result.get("page_id"):
                return f"Created Confluence page '{title}': {result['page_url']}"
            else:
                return "Failed to create page"

        tool = StructuredTool.from_function(
            name="confluence_create_page",
            description=(
                "Create a page in Confluence. Use this to publish PRDs and feature documentation. "
                "The content should be in markdown format and will be converted to Confluence format. "
                "Always call this BEFORE creating a Jira ticket so you have the page URL to link."
            ),
            args_schema=ConfluenceCreatePageInput,
            func=_create_page,
            return_direct=False,
            tags=["confluence_create_page"],
        )

        self.status = "Tool created"
        return tool
