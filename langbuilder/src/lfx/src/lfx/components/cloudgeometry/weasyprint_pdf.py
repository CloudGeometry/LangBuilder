"""
WeasyPrint PDF Generator - LangBuilder Custom Component

Converts rendered HTML into high-quality PDF documents using
the WeasyPrint library.

Author: CloudGeometry
Project: Carter's Agents - Content Engine

PREREQUISITES:
System dependencies must be installed before WeasyPrint works:
- macOS: brew install cairo pango gdk-pixbuf libffi
- Ubuntu: apt install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
"""

from langflow.custom import Component
from langflow.inputs.inputs import HandleInput
from langflow.io import DropdownInput, StrInput, Output
from langflow.schema import Data
import base64
import time

# WeasyPrint imports - will fail if system deps missing
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError as e:
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_ERROR = str(e)


class WeasyPrintPDF(Component):
    """
    Converts HTML to PDF using WeasyPrint.

    This component is used by the Content Engine agent to convert
    rendered HTML templates into professional PDF documents for
    delivery to prospects.

    IMPORTANT: Requires system dependencies (Cairo, Pango, etc.)
    See component documentation for installation instructions.
    """

    display_name = "WeasyPrint PDF Generator"
    description = "Converts HTML to PDF using WeasyPrint"
    icon = "file-text"
    name = "WeasyPrintPDF"

    # Supported page sizes
    PAGE_SIZES = {
        "Letter": "Letter",      # 8.5 x 11 inches (US standard)
        "A4": "A4",              # 210 x 297 mm (International standard)
        "Legal": "Legal",        # 8.5 x 14 inches
        "Tabloid": "Tabloid",    # 11 x 17 inches
    }

    inputs = [
        HandleInput(
            name="html_content",
            display_name="HTML Content",
            required=True,
            input_types=["Message", "Data"],
            info="Rendered HTML string to convert to PDF. Accepts Message or Data with 'html' key."
        ),
        HandleInput(
            name="filename",
            display_name="Filename",
            required=True,
            input_types=["Message", "Data"],
            info="Output filename (should end in .pdf)"
        ),
        DropdownInput(
            name="page_size",
            display_name="Page Size",
            required=False,
            value="Letter",
            options=["Letter", "A4", "Legal", "Tabloid"],
            info="Paper size for the PDF",
            advanced=True
        ),
        StrInput(
            name="margin",
            display_name="Margin",
            required=False,
            value="1in",
            info="Page margins (e.g., '1in', '2cm', '20mm'). Default: 1in",
            advanced=True
        ),
    ]

    outputs = [
        Output(
            name="pdf",
            display_name="PDF Output",
            method="generate_pdf",
        ),
    ]

    def _extract_text(self, value, key: str = None) -> str:
        """Extract text from a Message or Data object, or return string as-is.

        Args:
            value: Message, Data, dict, or string input
            key: Optional key to extract from Data objects (e.g., 'html', 'filename')
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
            for try_key in [key, 'html', 'text', 'content', 'value']:
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

    def generate_pdf(self) -> Data:
        """
        Convert HTML to PDF using WeasyPrint.

        Returns:
            Data object with base64-encoded PDF and metadata
        """
        # Check if WeasyPrint is available (do import check here for dynamic loading)
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            weasyprint_available = True
            weasyprint_error = None
        except ImportError as e:
            weasyprint_available = False
            weasyprint_error = str(e)

        if not weasyprint_available:
            self.status = "❌ WeasyPrint not available"
            return Data(data={
                "success": False,
                "error": f"WeasyPrint import failed: {weasyprint_error}. "
                         "Please install system dependencies (Cairo, Pango, etc.)"
            })

        start_time = time.time()

        # Extract text from Message or Data objects
        html_content = self._extract_text(self.html_content, key="html")
        filename = self._extract_text(self.filename, key="filename") or "report.pdf"
        margin = self.margin or "1in"

        try:
            # Validate inputs
            if not html_content or len(html_content.strip()) == 0:
                raise ValueError("HTML content is empty")

            # Ensure filename ends with .pdf
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'

            # Initialize font configuration
            font_config = FontConfiguration()

            # Create HTML object from string
            html = HTML(string=html_content)

            # Build CSS for page layout
            page_size = self.page_size or "Letter"

            custom_css = CSS(string=f"""
                @page {{
                    size: {page_size};
                    margin: {margin};
                }}
                body {{
                    font-family: 'Helvetica', 'Arial', sans-serif;
                    line-height: 1.5;
                }}
                @media print {{
                    .no-print {{ display: none; }}
                    .page-break {{ page-break-before: always; }}
                }}
                /* Ensure images don't overflow */
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                /* Table styling for print */
                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
            """, font_config=font_config)

            # Generate PDF
            pdf_bytes = html.write_pdf(
                stylesheets=[custom_css],
                font_config=font_config
            )

            # Encode as base64 for JSON transport
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

            # Calculate metrics
            size_bytes = len(pdf_bytes)
            size_kb = round(size_bytes / 1024, 1)
            generation_time_ms = int((time.time() - start_time) * 1000)

            self.status = f"✅ Generated: {filename} ({size_kb} KB)"

            return Data(data={
                "success": True,
                "pdf_base64": pdf_base64,
                "pdf_bytes": pdf_bytes,  # For direct chaining to file upload
                "filename": filename,
                "size_bytes": size_bytes,
                "size_kb": size_kb,
                "page_size": page_size,
                "margin": margin,
                "generation_time_ms": generation_time_ms
            })

        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            self.status = f"❌ Error: {error_msg[:50]}"
            self.log(f"PDF generation failed: {error_msg}")

            return Data(data={
                "success": False,
                "error": error_msg,
                "generation_time_ms": generation_time_ms
            })
