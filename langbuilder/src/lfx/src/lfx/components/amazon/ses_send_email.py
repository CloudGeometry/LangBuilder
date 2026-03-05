"""
SES (Simple Email Service) Send Email Component for LangBuilder

Sends emails using AWS Simple Email Service (SES).
Supports both sandbox and production modes with verified sender addresses.

Adapted for LangBuilder 1.65 (CloudGeometry fork)

References:
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses/client/send_email.html
- https://docs.aws.amazon.com/ses/latest/dg/send-an-email-using-sdk-programmatically.html
"""

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from langflow.field_typing import Tool
from langflow.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langflow.schema.data import Data

# AWS region options for dropdown
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1"
]


class SESSendEmailComponent(LCToolComponent):
    """
    Send emails using AWS Simple Email Service (SES).

    This component sends emails via AWS SES API. It supports:
    - Plain text and HTML email bodies
    - Multiple recipients (To, CC, BCC)
    - Temporary AWS credentials (session tokens)
    - Both sandbox and production SES modes

    Can be used as an Agent tool to send emails programmatically.

    Requirements:
    - Sender email must be verified in SES
    - In sandbox mode, recipients must also be verified
    - boto3 must be installed
    """

    display_name = "SES (Simple Email Service)"
    description = (
        "Send emails using Amazon Simple Email Service (SES). "
        "Use this tool to send emails with subject, body, and recipient addresses. "
        "Requires verified sender address. Supports HTML and plain text."
    )
    icon = "Amazon"
    name = "SESSendEmail"

    inputs = [
        # Optional Data input for integration with Email Composer
        DataInput(
            name="email_data",
            display_name="Email Data",
            info="Optional: Data from Email Composer component (overrides manual inputs if provided)",
            required=False,
        ),

        # Sender configuration
        StrInput(
            name="sender_email",
            display_name="Sender Email (From)",
            info="Verified sender email address. Must be verified in SES.",
            required=True,
        ),

        # Recipient configuration
        MessageTextInput(
            name="to_addresses",
            display_name="To Address(es)",
            info="Recipient email address(es). Separate multiple with commas.",
            required=False,
            tool_mode=True,  # Agent can set this when used as tool
        ),

        MessageTextInput(
            name="cc_addresses",
            display_name="CC Address(es)",
            info="Carbon copy recipient(s). Separate multiple with commas.",
            required=False,
            advanced=True,
        ),

        MessageTextInput(
            name="bcc_addresses",
            display_name="BCC Address(es)",
            info="Blind carbon copy recipient(s). Separate multiple with commas.",
            required=False,
            advanced=True,
        ),

        # Email content
        MessageTextInput(
            name="subject",
            display_name="Subject",
            info="Email subject line",
            required=False,
            tool_mode=True,  # Agent can set this when used as tool
        ),

        MessageTextInput(
            name="body_text",
            display_name="Body (Plain Text)",
            info="Plain text version of the email body",
            required=False,
            tool_mode=True,  # Agent can set this when used as tool
        ),

        MessageTextInput(
            name="body_html",
            display_name="Body (HTML)",
            info="HTML version of the email body (optional, takes precedence for HTML-capable clients)",
            required=False,
            advanced=True,
        ),

        # Reply-to configuration
        MessageTextInput(
            name="reply_to_addresses",
            display_name="Reply-To Address(es)",
            info="Address(es) that receive replies. Separate multiple with commas.",
            required=False,
            advanced=True,
        ),

        # AWS credentials
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="AWS Access Key ID (leave empty to use IAM role or environment credentials)",
            required=False,
        ),

        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="AWS Secret Access Key (leave empty to use IAM role or environment credentials)",
            required=False,
        ),

        SecretStrInput(
            name="aws_session_token",
            display_name="AWS Session Token",
            info="AWS Session Token for temporary credentials (optional)",
            required=False,
            advanced=True,
        ),

        DropdownInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region for SES. Must match where your sender is verified.",
            options=AWS_REGIONS,
            value="us-east-1",
            required=True,
        ),

        # Advanced options
        StrInput(
            name="configuration_set_name",
            display_name="Configuration Set",
            info="SES Configuration Set name for tracking/analytics (optional)",
            required=False,
            advanced=True,
        ),

        StrInput(
            name="charset",
            display_name="Character Set",
            info="Character encoding for subject and body",
            value="UTF-8",
            required=False,
            advanced=True,
        ),

        BoolInput(
            name="dry_run",
            display_name="Dry Run (Test Mode)",
            info="If enabled, logs email details without actually sending",
            value=False,
            advanced=True,
        ),
    ]

    # Uses default outputs from LCToolComponent base class

    def _parse_addresses(self, addresses_str: str) -> list[str]:
        """Parse comma-separated email addresses into a list."""
        if not addresses_str:
            return []
        # Split by comma, strip whitespace, filter empty
        return [addr.strip() for addr in str(addresses_str).split(",") if addr.strip()]

    def _get_email_params(self) -> dict:
        """
        Extract email parameters from either email_data input or manual inputs.
        email_data takes precedence if provided.
        """
        # Check if email_data was provided
        if self.email_data:
            data = self.email_data
            if hasattr(data, "data"):
                data = data.data
            elif isinstance(data, list) and data:
                data = data[0]
                if hasattr(data, "data"):
                    data = data.data

            if isinstance(data, dict) and data:
                # Extract from email_data, fall back to manual inputs
                return {
                    "to": data.get("to") or self.to_addresses,
                    "cc": data.get("cc") or self.cc_addresses,
                    "bcc": data.get("bcc") or self.bcc_addresses,
                    "subject": data.get("subject") or self.subject,
                    "body_text": data.get("body_text") or data.get("body") or self.body_text,
                    "body_html": data.get("body_html") or self.body_html,
                    "reply_to": data.get("reply_to") or self.reply_to_addresses,
                }

        # Use manual inputs
        return {
            "to": self.to_addresses,
            "cc": self.cc_addresses,
            "bcc": self.bcc_addresses,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "reply_to": self.reply_to_addresses,
        }

    def run_model(self) -> Data:
        """
        Send email using AWS SES.

        Can be invoked in two ways:
        1. As a tool: Agent provides to_addresses, subject, body_text via tool parameters
        2. Via email_data: Receives structured data from upstream Email Composer component

        Returns:
            Data object with message_id and send status
        """
        # Upstream data (Webhook, Email Composer) takes priority over UI/tool fields
        if self.email_data:
            data = self.email_data
            if hasattr(data, "data"):
                data = data.data
            elif isinstance(data, list) and data:
                data = data[0]
                if hasattr(data, "data"):
                    data = data.data

            # Only skip if upstream explicitly set _skipped flag
            if isinstance(data, dict) and data.get("_skipped", False):
                self.log("Skipped: upstream component was skipped")
                self.status = "Skipped"
                return Data(data={"sent": False, "_skipped": True})
            self.log("Using email_data from upstream component")
        elif self.to_addresses and self.subject and self.body_text:
            self.log("Using direct parameters (tool/UI)")
        else:
            self.log("Skipped: no email_data and no complete direct params (to+subject+body)")
            self.status = "Skipped: no input"
            return Data(data={"sent": False, "_skipped": True})

        # Import boto3
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as e:
            msg = (
                "boto3 is not installed. Please install it using: "
                "uv pip install boto3"
            )
            raise ImportError(msg) from e

        # Get email parameters
        params = self._get_email_params()

        # Parse addresses
        to_list = self._parse_addresses(params["to"])
        cc_list = self._parse_addresses(params["cc"])
        bcc_list = self._parse_addresses(params["bcc"])
        reply_to_list = self._parse_addresses(params["reply_to"])

        # Validate required fields
        if not to_list and not cc_list and not bcc_list:
            msg = "At least one recipient (To, CC, or BCC) is required"
            raise ValueError(msg)

        if not params["subject"]:
            msg = "Email subject is required"
            raise ValueError(msg)

        if not params["body_text"] and not params["body_html"]:
            msg = "Email body (text or HTML) is required"
            raise ValueError(msg)

        if not self.sender_email:
            msg = "Sender email address is required"
            raise ValueError(msg)

        # Log email details
        self.log(f"Preparing to send email from: {self.sender_email}")
        self.log(f"To: {to_list}")
        if cc_list:
            self.log(f"CC: {cc_list}")
        if bcc_list:
            self.log(f"BCC: {bcc_list}")
        self.log(f"Subject: {params['subject']}")

        # Dry run mode - just log, don't send
        if self.dry_run:
            self.log("DRY RUN MODE - Email not actually sent")
            self.status = f"[DRY RUN] Would send to: {', '.join(to_list)}"
            return Data(data={
                "sent": False,
                "dry_run": True,
                "to": to_list,
                "cc": cc_list,
                "bcc": bcc_list,
                "subject": params["subject"],
                "sender": self.sender_email,
            })

        # Initialize SES client with credentials
        try:
            client_kwargs = {
                "service_name": "ses",
                "region_name": self.region_name,
            }

            # Add credentials if provided
            if self.aws_access_key_id:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            if self.aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_session_token:
                client_kwargs["aws_session_token"] = self.aws_session_token

            ses_client = boto3.client(**client_kwargs)

            if self.aws_access_key_id:
                self.log("Using provided AWS credentials")
                if self.aws_session_token:
                    self.log("Using temporary session credentials")
            else:
                self.log("Using IAM role or environment credentials")

        except Exception as e:
            msg = f"Failed to initialize SES client: {e}"
            raise ValueError(msg) from e

        # Build destination
        destination = {}
        if to_list:
            destination["ToAddresses"] = to_list
        if cc_list:
            destination["CcAddresses"] = cc_list
        if bcc_list:
            destination["BccAddresses"] = bcc_list

        # Build message body
        body = {}
        if params["body_text"]:
            body["Text"] = {
                "Data": str(params["body_text"]),
                "Charset": self.charset,
            }
        if params["body_html"]:
            body["Html"] = {
                "Data": str(params["body_html"]),
                "Charset": self.charset,
            }

        # Build send_email parameters
        send_params = {
            "Source": self.sender_email,
            "Destination": destination,
            "Message": {
                "Subject": {
                    "Data": str(params["subject"]),
                    "Charset": self.charset,
                },
                "Body": body,
            },
        }

        # Add optional parameters
        if reply_to_list:
            send_params["ReplyToAddresses"] = reply_to_list

        if self.configuration_set_name:
            send_params["ConfigurationSetName"] = self.configuration_set_name

        # Send the email
        try:
            self.log("Sending email via SES...")
            response = ses_client.send_email(**send_params)

            message_id = response.get("MessageId", "unknown")
            self.log(f"Email sent successfully! MessageId: {message_id}")

            # Update status
            recipient_count = len(to_list) + len(cc_list) + len(bcc_list)
            self.status = f"Sent to {recipient_count} recipient(s) - ID: {message_id[:20]}..."

            return Data(data={
                "sent": True,
                "message_id": message_id,
                "to": to_list,
                "cc": cc_list,
                "bcc": bcc_list,
                "subject": params["subject"],
                "sender": self.sender_email,
                "region": self.region_name,
            })

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]

            # Provide helpful messages for common errors
            if error_code == "MessageRejected":
                if "not verified" in error_msg.lower():
                    help_msg = (
                        "Email address not verified. In sandbox mode, both sender "
                        "and recipient must be verified in SES console."
                    )
                else:
                    help_msg = "Message was rejected by SES."
            elif error_code == "MailFromDomainNotVerified":
                help_msg = "Sender domain is not verified. Verify the domain in SES console."
            elif error_code == "ConfigurationSetDoesNotExist":
                help_msg = "The specified configuration set does not exist."
            elif error_code == "AccessDenied":
                help_msg = "Access denied. Check IAM permissions for ses:SendEmail."
            else:
                help_msg = f"SES error: {error_code}"

            full_msg = f"{help_msg}\nDetails: {error_msg}"
            self.log(f"Error: {full_msg}")
            self.status = f"Failed: {error_code}"
            raise ValueError(full_msg) from e

        except Exception as e:
            msg = f"Unexpected error sending email: {e}"
            self.log(f"Error: {msg}")
            self.status = "Failed: Unexpected error"
            raise ValueError(msg) from e

    async def _get_tools(self):
        """Override to return the named tool from build_tool() instead of generic outputs."""
        tool = self.build_tool()
        # Ensure tool has tags for framework compatibility
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """
        Build a LangChain tool for sending emails via SES.

        Returns:
            StructuredTool: A tool that can be used by an Agent to send emails.
        """
        # Define the input schema for the tool
        class SendEmailInput(BaseModel):
            to_addresses: str = Field(
                description="Email recipient address(es). Separate multiple with commas."
            )
            subject: str = Field(
                description="Email subject line"
            )
            body_text: str = Field(
                description="Plain text body of the email"
            )

        # Create a wrapper that sets instance attributes then calls run_model
        def _send_email_tool(to_addresses: str, subject: str, body_text: str) -> str:
            """Tool function that sends email via SES."""
            # Set instance attributes (like DynamoDB pattern)
            self.to_addresses = to_addresses
            self.subject = subject
            self.body_text = body_text
            self._tool_mode = True  # Flag to indicate tool mode

            # Call run_model with no params
            result = self.run_model()

            # Format response
            if hasattr(result, 'data'):
                data = result.data
                if data.get('sent'):
                    return f"Email sent successfully to {to_addresses}. Message ID: {data.get('message_id', 'unknown')}"
                elif data.get('_skipped'):
                    return f"Email skipped: {data}"
                else:
                    return f"Email failed: {data}"
            return str(result)

        tool = StructuredTool.from_function(
            name="send_email",
            description=(
                "Send an email using AWS SES. "
                "Use this to send emails to users with a subject and body. "
                "Provide recipient email, subject, and body text."
            ),
            args_schema=SendEmailInput,
            func=_send_email_tool,
            return_direct=False,
            tags=["send_email"],
        )

        self.status = "SES Email Tool created"
        return tool
