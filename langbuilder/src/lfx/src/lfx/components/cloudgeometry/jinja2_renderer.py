"""
Jinja2 Renderer - LangBuilder Custom Component

Renders HTML from Jinja2 templates with dynamic context variables
for PDF report generation. Supports both local files AND remote URLs.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from lfx.custom import Component
from lfx.inputs.inputs import HandleInput
from lfx.io import StrInput, DropdownInput, IntInput, Output
from lfx.schema import Data
from jinja2 import Environment, BaseLoader, FileSystemLoader
from pathlib import Path
from datetime import datetime
import httpx
import time


class Jinja2Renderer(Component):
    """
    Renders HTML from Jinja2 template with context variables.

    Supports both local file paths and remote URLs (GitHub, S3,
    Google Drive, etc.) for maximum flexibility in template storage.
    """

    display_name = "Jinja2 Renderer"
    description = "Renders HTML from Jinja2 template (file or URL) with context variables"
    icon = "code"
    name = "Jinja2Renderer"

    inputs = [
        HandleInput(
            name="template_source",
            display_name="Template Source",
            required=True,
            input_types=["Message", "Data"],
            info="URL or file path to the Jinja2 template. Examples:\n"
                 "- https://raw.githubusercontent.com/.../template.html\n"
                 "- https://drive.google.com/uc?export=download&id=FILE_ID\n"
                 "- /app/templates/template_healthcare.html"
        ),
        DropdownInput(
            name="source_type",
            display_name="Source Type",
            options=["auto", "url", "file"],
            value="auto",
            required=True,
            info="How to interpret template_source. 'auto' detects based on http:// prefix."
        ),
        HandleInput(
            name="company_name",
            display_name="Company Name",
            required=True,
            input_types=["Message", "Data"],
            info="Company name for the report header"
        ),
        HandleInput(
            name="lead_name",
            display_name="Lead Name",
            required=True,
            input_types=["Message", "Data"],
            info="Contact's full name"
        ),
        HandleInput(
            name="role",
            display_name="Role",
            required=True,
            input_types=["Message", "Data"],
            info="Job title (e.g., CFO, CTO)"
        ),
        HandleInput(
            name="industry",
            display_name="Industry",
            required=True,
            input_types=["Message", "Data"],
            info="Industry vertical"
        ),
        HandleInput(
            name="ai_executive_summary",
            display_name="Executive Summary",
            required=True,
            input_types=["Message", "Data"],
            info="AI-generated executive summary text"
        ),
        HandleInput(
            name="calculated_savings",
            display_name="Calculated Savings",
            required=True,
            input_types=["Message", "Data"],
            info="Formatted savings amount (e.g., '$150,000')"
        ),
        HandleInput(
            name="annual_cloud_spend",
            display_name="Annual Cloud Spend",
            required=False,
            input_types=["Message", "Data"],
            info="Formatted annual spend (e.g., '$500,000')"
        ),
        IntInput(
            name="http_timeout",
            display_name="HTTP Timeout (seconds)",
            required=False,
            value=30,
            info="Timeout for fetching URL-based templates"
        ),
    ]

    outputs = [
        Output(
            name="html",
            display_name="Rendered HTML",
            method="render_template",
        ),
    ]

    def _extract_text(self, value, key: str = None) -> str:
        """Extract text from a Message or Data object, or return string as-is.

        Args:
            value: Message, Data, dict, or string input
            key: Optional key to extract from Data objects
        """
        if value is None:
            return ""
        # Handle Message objects
        if hasattr(value, 'text'):
            return str(value.text).strip()
        # Handle Data objects
        if hasattr(value, 'data') and isinstance(value.data, dict):
            if key and key in value.data:
                return str(value.data[key]).strip()
            # Try common keys
            for try_key in [key, 'text', 'content', 'value', 'template_source']:
                if try_key and try_key in value.data:
                    return str(value.data[try_key]).strip()
            # Return first string value found
            for v in value.data.values():
                if isinstance(v, str) and len(v) > 0:
                    return v.strip()
            return ""
        # Handle dict directly
        if isinstance(value, dict):
            if key and key in value:
                return str(value[key]).strip()
            return ""
        return str(value).strip()

    def _is_url(self, source: str) -> bool:
        """Check if the source is a URL."""
        return source.strip().lower().startswith(('http://', 'https://'))

    def _format_currency(self, value) -> str:
        """Custom Jinja2 filter for formatting currency."""
        try:
            if isinstance(value, str):
                value = value.replace('$', '').replace(',', '')
                value = float(value)
            return f"${value:,.0f}"
        except (ValueError, TypeError):
            return str(value) if value else "N/A"

    def _generate_minimal_html(self, context: dict) -> str:
        """Generate minimal fallback HTML if templates fail."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cloud Infrastructure Report - {context.get('company_name', 'Your Company')}</title>
    <style>
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            margin: 40px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1e40af;
        }}
        .summary {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .metric {{
            font-size: 28px;
            color: #059669;
            font-weight: bold;
        }}
        .meta {{
            color: #6b7280;
            font-size: 14px;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <h1>Cloud Infrastructure Report</h1>
    <h2>{context.get('company_name', 'Your Company')}</h2>
    <p class="meta">Prepared for {context.get('lead_name', 'Valued Customer')}, {context.get('role', 'Executive')} | {context.get('industry', 'Technology')}</p>

    <div class="summary">
        <h3>Executive Summary</h3>
        <p>{context.get('ai_executive_summary', 'CloudGeometry can help optimize your cloud infrastructure for better performance and lower costs.')}</p>
    </div>

    <h3>Projected Annual Savings</h3>
    <p class="metric">{context.get('calculated_savings', 'Contact us for an estimate')}</p>
    <p>Based on current annual cloud spend of {context.get('annual_cloud_spend', 'N/A')}</p>

    <footer>
        <p>Generated on {context.get('current_date', datetime.now().strftime('%B %d, %Y'))}</p>
        <p>CloudGeometry - Cloud Infrastructure Excellence</p>
    </footer>
</body>
</html>"""

    async def _fetch_template_from_url(self, url: str) -> tuple[str, int]:
        """
        Fetch template content from a URL.

        Args:
            url: The URL to fetch the template from

        Returns:
            Tuple of (template_content, fetch_time_ms)
        """
        start_time = time.time()

        headers = {
            "User-Agent": "LangBuilder/1.0 (CloudGeometry Template Fetcher)",
            "Accept": "text/html, text/plain, */*",
        }

        timeout = self.http_timeout or 30

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            content = response.text
            fetch_time_ms = int((time.time() - start_time) * 1000)

            return content, fetch_time_ms

    async def render_template(self) -> Data:
        """
        Render the Jinja2 template with context variables.

        Supports both local file paths and remote URLs.

        Returns:
            Data object with rendered HTML and metadata
        """
        start_time = time.time()
        fetch_time_ms = 0

        # Extract text from Message or Data objects
        template_source = self._extract_text(self.template_source, key="template_source")

        # Build context dictionary - extract text from all Message/Data inputs
        context = {
            "company_name": self._extract_text(self.company_name, key="company_name") or "Your Company",
            "lead_name": self._extract_text(self.lead_name, key="lead_name") or "Valued Customer",
            "role": self._extract_text(self.role, key="role") or "Executive",
            "industry": self._extract_text(self.industry, key="industry") or "Technology",
            "ai_executive_summary": self._extract_text(self.ai_executive_summary, key="ai_executive_summary") or "",
            "calculated_savings": self._extract_text(self.calculated_savings, key="calculated_savings") or "Contact us for an estimate",
            "annual_cloud_spend": self._extract_text(self.annual_cloud_spend, key="annual_spend_formatted") or "N/A",
            "current_date": datetime.now().strftime("%B %d, %Y"),
        }

        fallback_used = False
        source_type_used = self.source_type
        template_content = None

        # Determine if source is URL or file
        if self.source_type == "auto":
            is_url = self._is_url(template_source)
            source_type_used = "url" if is_url else "file"
        else:
            is_url = (self.source_type == "url")

        try:
            # Fetch template content
            if is_url:
                self.log(f"Fetching template from URL: {template_source}")
                template_content, fetch_time_ms = await self._fetch_template_from_url(
                    template_source
                )
                self.log(f"Template fetched in {fetch_time_ms}ms, {len(template_content)} chars")
            else:
                # Read from local file
                template_path = Path(template_source)
                if not template_path.exists():
                    raise FileNotFoundError(f"Template file not found: {template_source}")
                template_content = template_path.read_text(encoding='utf-8')
                self.log(f"Template loaded from file: {template_path.name}")

            # Create Jinja2 environment for string-based template
            env = Environment(
                loader=BaseLoader(),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True
            )

            # Add custom currency filter
            env.filters['currency'] = self._format_currency

            # Compile and render template
            template = env.from_string(template_content)
            html = template.render(**context)

            self.status = f"Rendered from {source_type_used}: {len(html)} chars"

        except httpx.HTTPStatusError as e:
            self.log(f"HTTP error fetching template: {e.response.status_code}")
            html = self._generate_minimal_html(context)
            fallback_used = True
            self.status = f"HTTP {e.response.status_code} - used fallback"

        except httpx.RequestError as e:
            self.log(f"Request error fetching template: {str(e)}")
            html = self._generate_minimal_html(context)
            fallback_used = True
            self.status = f"Request error - used fallback"

        except FileNotFoundError as e:
            self.log(f"File not found: {str(e)}")
            html = self._generate_minimal_html(context)
            fallback_used = True
            self.status = f"File not found - used fallback"

        except Exception as e:
            self.log(f"Template rendering error: {str(e)}")
            html = self._generate_minimal_html(context)
            fallback_used = True
            self.status = f"Error: {str(e)[:50]} - used fallback"

        # Calculate total render time
        render_time_ms = int((time.time() - start_time) * 1000)

        return Data(data={
            "html": html,
            "length": len(html),
            "template_source": template_source,
            "source_type": source_type_used,
            "render_time_ms": render_time_ms,
            "fetch_time_ms": fetch_time_ms,
            "fallback_used": fallback_used,
            "context_keys": list(context.keys())
        })
