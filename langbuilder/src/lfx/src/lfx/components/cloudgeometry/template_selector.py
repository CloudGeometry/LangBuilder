"""
Template Selector - LangBuilder Custom Component

Selects the appropriate HTML/Jinja2 template URL based on CloudGeometry
service type for personalized PDF report generation. Supports URL-based
templates stored in GitHub, S3, Google Drive, or local files.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from lfx.custom import Component
from lfx.inputs.inputs import HandleInput
from lfx.io import StrInput, DropdownInput, Output
from lfx.schema import Data


class TemplateSelector(Component):
    """
    Selects HTML template URL based on CloudGeometry service type.

    This component is used by the Content Engine agent to route
    to service-specific PDF report templates. Each service has
    a customized template with relevant terminology and design.

    The LLM then tailors the content to the prospect's specific
    industry context.

    Supports both URL-based templates (GitHub, S3, etc.) and
    local file paths.
    """

    display_name = "Template Selector"
    description = "Selects HTML template URL based on CloudGeometry service type"
    icon = "file-text"
    name = "TemplateSelector"

    # CloudGeometry core services
    SERVICES = [
        "AI Transformation",
        "App Modernization",
        "Cloud Migration",
        "DevOps Acceleration",
        "Data Platform",
        "Managed Services",
    ]

    # Service type to template filename mapping
    TEMPLATE_MAP = {
        "AI Transformation": "template_ai_transformation.html",
        "App Modernization": "template_app_modernization.html",
        "Cloud Migration": "template_cloud_migration.html",
        "DevOps Acceleration": "template_devops_acceleration.html",
        "Data Platform": "template_data_platform.html",
        "Managed Services": "template_managed_services.html",
    }

    DEFAULT_TEMPLATE = "template_default.html"

    inputs = [
        HandleInput(
            name="service_type",
            input_types=["Message", "Data"],
            display_name="Service Type",
            required=True,
            info="CloudGeometry service the prospect is interested in. Valid values: AI Transformation, App Modernization, Cloud Migration, DevOps Acceleration, Data Platform, Managed Services"
        ),
        StrInput(
            name="base_url",
            display_name="Base URL or Path",
            required=True,
            value="https://raw.githubusercontent.com/cloudgeometry/carter-templates/main/",
            info="Base URL for templates. Examples:\n"
                 "- https://raw.githubusercontent.com/ORG/REPO/BRANCH/\n"
                 "- https://bucket.s3.amazonaws.com/templates/\n"
                 "- /app/templates/ (for local files)"
        ),
        DropdownInput(
            name="source_type",
            display_name="Source Type",
            required=True,
            options=["url", "file"],
            value="url",
            info="'url' for HTTP-based templates, 'file' for local filesystem"
        ),
    ]

    outputs = [
        Output(
            name="template_source",
            display_name="Template Source",
            method="select_template",
        ),
    ]

    def _extract_text(self, value) -> str:
        """Extract text from a Message object or return string as-is."""
        if value is None:
            return ""
        if hasattr(value, 'text'):
            return str(value.text).strip()
        return str(value).strip()

    def select_template(self) -> Data:
        """
        Select the appropriate template based on service type.

        Returns:
            Data object with template URL/path and metadata
        """
        # Normalize service_type input - handle Message objects
        service_type = self._extract_text(self.service_type) or "Other"

        # Look up template name by service type
        template_name = self.TEMPLATE_MAP.get(service_type)
        is_default = False

        if template_name is None:
            template_name = self.DEFAULT_TEMPLATE
            is_default = True
            self.log(f"Service '{service_type}' not in template map, using default")

        # Ensure base_url ends with / for URL mode
        base_url = self.base_url.strip()
        if self.source_type == "url" and not base_url.endswith('/'):
            base_url = base_url + '/'
        elif self.source_type == "file" and not base_url.endswith('/'):
            base_url = base_url + '/'

        # Construct full URL or path
        template_source = f"{base_url}{template_name}"

        # Set status for UI feedback
        if is_default:
            self.status = f"Using default template"
        else:
            self.status = f"Selected: {template_name}"

        return Data(data={
            "template_source": template_source,
            "template_name": template_name,
            "service_type": service_type,
            "is_default": is_default,
            "source_type": self.source_type,
            "base_url": base_url
        })
