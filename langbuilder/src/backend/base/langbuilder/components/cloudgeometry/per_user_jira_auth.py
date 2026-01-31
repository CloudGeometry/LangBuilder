"""
Per-User Jira Auth Component for MeetBot

Looks up a user's Atlassian credentials from DynamoDB and returns
auth data compatible with the AtlassianMCPComponent. Falls back to
service account credentials for the demo.
"""

from __future__ import annotations

import base64
import json
import os

from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data

AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1",
]


class PerUserJiraAuthComponent(Component):
    """
    Resolve per-user Atlassian credentials for MeetBot.

    Looks up the user's Atlassian email and API token from the
    ``user_registry`` DynamoDB table. Falls back to service account
    credentials if the user is not registered (demo mode).
    """

    display_name = "Per-User Jira Auth"
    description = (
        "Look up a user's Atlassian credentials from DynamoDB. "
        "Falls back to service account for demo."
    )
    icon = "Jira"
    name = "PerUserJiraAuth"

    inputs = [
        StrInput(
            name="user_slack_id",
            display_name="User Slack ID",
            info="Slack user ID to look up in the registry",
            required=True,
        ),
        StrInput(
            name="table_name",
            display_name="User Registry Table",
            info="DynamoDB table name for user registry",
            value="meetbot_user_registry_demo",
        ),
        StrInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region for DynamoDB",
            value="us-west-2",
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="Leave empty for IAM role",
            required=False,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="Leave empty for IAM role",
            required=False,
        ),
        # Service account fallback
        StrInput(
            name="fallback_jira_url",
            display_name="Fallback Jira URL",
            info="Jira URL for service account fallback",
            value="https://cloudgeometry.atlassian.net",
        ),
        StrInput(
            name="fallback_email",
            display_name="Fallback Email",
            info="Service account email for fallback",
            required=False,
        ),
        SecretStrInput(
            name="fallback_api_token",
            display_name="Fallback API Token",
            info="Service account API token for fallback",
            required=False,
        ),
    ]

    outputs = [
        Output(name="auth_data", display_name="Auth Data", method="resolve_auth"),
    ]

    def resolve_auth(self) -> Data:
        """Look up user credentials or fall back to service account."""
        # Try DynamoDB lookup
        user_record = self._lookup_user(self.user_slack_id)

        if user_record and user_record.get("atlassian_token"):
            email = user_record.get("atlassian_email", user_record.get("google_email", ""))
            token = user_record.get("atlassian_token", "")
            jira_url = user_record.get("jira_url", self.fallback_jira_url)
            jira_project = user_record.get("jira_project", "")
            auth_b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
            return Data(data={
                "authenticated": True,
                "auth_source": "per_user",
                "jira_url": jira_url,
                "jira_project": jira_project,
                "atlassian_email": email,
                "atlassian_api_token": token,
                "headers": {"Authorization": f"Basic {auth_b64}"},
            })

        # Fallback to service account
        email = self.fallback_email or os.environ.get("JIRA_USERNAME", "")
        token = self.fallback_api_token or os.environ.get("JIRA_API_TOKEN", "")
        if email and token:
            auth_b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
            return Data(data={
                "authenticated": True,
                "auth_source": "service_account",
                "jira_url": self.fallback_jira_url,
                "jira_project": "",
                "atlassian_email": email,
                "atlassian_api_token": token,
                "headers": {"Authorization": f"Basic {auth_b64}"},
            })

        return Data(data={
            "authenticated": False,
            "auth_source": "none",
            "error": f"No credentials found for user {self.user_slack_id} and no service account configured",
        })

    def _lookup_user(self, slack_user_id: str) -> dict | None:
        """Query user_registry DynamoDB table."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            kwargs = {"region_name": self.region_name}
            if self.aws_access_key_id and self.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            dynamodb = boto3.resource("dynamodb", **kwargs)
            table = dynamodb.Table(self.table_name)
            resp = table.get_item(Key={"slack_user_id": slack_user_id})
            return resp.get("Item")
        except Exception:
            return None
