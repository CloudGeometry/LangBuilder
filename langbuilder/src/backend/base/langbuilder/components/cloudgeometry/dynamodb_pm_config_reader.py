"""
DynamoDB PM Config Reader Component for LangBuilder

Reads Product Manager configurations from the pm_configurations DynamoDB table.
Used by the JIRA Slack Agent trigger flow to:
1. List all enabled PMs
2. Get a specific PM's config by slack_id
3. Return configs for iteration (detecting new transcripts, etc.)

Adapted for LangBuilder 1.65 (CloudGeometry fork)
"""

import json

from langbuilder.custom.custom_component.component import Component
from langbuilder.io import BoolInput, DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from langbuilder.schema.data import Data
from langbuilder.schema.message import Message

# AWS region options
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1",
]


class DynamoDBPMConfigReaderComponent(Component):
    """
    Read PM configurations from the pm_configurations DynamoDB table.

    Supports two operations:
    - **get_item**: Retrieve a single PM config by Slack user ID
    - **scan_enabled**: List all enabled PM configurations

    Returns structured data that can be used to build LangBuilder tweaks
    for injecting per-PM JIRA/GDrive credentials into flows.
    """

    display_name = "DynamoDB PM Config Reader"
    description = (
        "Read PM configurations from DynamoDB. "
        "Supports fetching a single PM by slack_id or listing all enabled PMs."
    )
    icon = "Amazon"
    name = "DynamoDBPMConfigReader"

    inputs = [
        # === Operation ===
        DropdownInput(
            name="operation",
            display_name="Operation",
            info="get_item: fetch one PM by slack_id. scan_enabled: list all enabled PMs.",
            options=["get_item", "scan_enabled"],
            value="scan_enabled",
            required=True,
        ),

        # === Query parameter ===
        MessageTextInput(
            name="slack_id",
            display_name="Slack User ID",
            info="Slack user ID to look up (required for get_item operation). Format: U + 10 chars.",
            required=False,
            tool_mode=True,
        ),

        # === Table configuration ===
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="DynamoDB table name for PM configurations",
            value="pm_configurations",
            required=True,
        ),

        # === AWS credentials ===
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="Leave empty to use IAM role or environment credentials",
            value="",
            required=False,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="Leave empty to use IAM role or environment credentials",
            value="",
            required=False,
        ),
        DropdownInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region where the DynamoDB table is located",
            options=AWS_REGIONS,
            value="us-east-1",
            required=True,
        ),

        # === Output options ===
        BoolInput(
            name="include_credentials",
            display_name="Include Credentials in Output",
            info=(
                "If true, include JIRA api_token and GDrive private_key in the output. "
                "Enable when building tweaks for LangBuilder flows. "
                "Disable for display/logging purposes."
            ),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="pm_configs",
            display_name="PM Configurations",
            method="read_configs",
        ),
        Output(
            name="pm_configs_message",
            display_name="PM Configs (Message)",
            method="read_configs_as_message",
        ),
    ]

    def _get_dynamodb_table(self):
        """Initialize and return the DynamoDB table resource."""
        try:
            import boto3
        except ImportError as e:
            msg = "boto3 is not installed. Please install it using: uv pip install boto3"
            raise ImportError(msg) from e

        try:
            kwargs = {"region_name": self.region_name}
            if self.aws_access_key_id and self.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.aws_secret_access_key
                self.log("Using provided AWS credentials")
            else:
                self.log("Using IAM role or environment credentials")

            dynamodb = boto3.resource("dynamodb", **kwargs)
            return dynamodb.Table(self.table_name)
        except Exception as e:
            msg = f"Failed to initialize DynamoDB client: {e}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

    def _sanitize_config(self, item: dict) -> dict:
        """Optionally redact sensitive credentials from a PM config."""
        if self.include_credentials:
            return item

        sanitized = dict(item)

        # Redact JIRA api_token
        jira_config = sanitized.get("jira_config")
        if isinstance(jira_config, dict) and "api_token" in jira_config:
            jira_config = dict(jira_config)
            jira_config["api_token"] = "***REDACTED***"
            sanitized["jira_config"] = jira_config

        # Redact GDrive private_key
        gdrive_config = sanitized.get("gdrive_config")
        if isinstance(gdrive_config, dict) and "private_key" in gdrive_config:
            gdrive_config = dict(gdrive_config)
            gdrive_config["private_key"] = "***REDACTED***"
            sanitized["gdrive_config"] = gdrive_config

        return sanitized

    def _get_single_pm(self, table) -> list[dict]:
        """Fetch a single PM config by slack_id."""
        from botocore.exceptions import ClientError

        if not self.slack_id:
            msg = "slack_id is required for get_item operation"
            raise ValueError(msg)

        slack_id = str(self.slack_id).strip()
        self.log(f"Fetching PM config for slack_id={slack_id}")

        try:
            response = table.get_item(Key={"slack_id": slack_id})
        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            msg = f"DynamoDB error: {error_msg}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

        item = response.get("Item")
        if not item:
            self.log(f"No PM config found for slack_id={slack_id}")
            return []

        self.log(f"Found PM config: name={item.get('name')}, enabled={item.get('enabled')}")
        return [self._sanitize_config(item)]

    def _scan_enabled_pms(self, table) -> list[dict]:
        """Scan for all enabled PM configurations."""
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        self.log(f"Scanning for enabled PMs in table {self.table_name}")

        try:
            response = table.scan(
                FilterExpression=Attr("enabled").eq(True),
            )
        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            msg = f"DynamoDB scan error: {error_msg}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

        items = response.get("Items", [])

        # Handle pagination for large tables
        while "LastEvaluatedKey" in response:
            try:
                response = table.scan(
                    FilterExpression=Attr("enabled").eq(True),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))
            except ClientError:
                break

        self.log(f"Found {len(items)} enabled PMs")
        return [self._sanitize_config(item) for item in items]

    def read_configs(self) -> Data:
        """
        Read PM configurations from DynamoDB.

        Returns:
            Data object with list of PM configs and metadata.
        """
        table = self._get_dynamodb_table()

        if self.operation == "get_item":
            configs = self._get_single_pm(table)
        else:
            configs = self._scan_enabled_pms(table)

        self.status = f"Retrieved {len(configs)} PM config(s)"

        return Data(data={
            "pm_configs": configs,
            "count": len(configs),
            "operation": self.operation,
            "table_name": self.table_name,
        })

    def read_configs_as_message(self) -> Message:
        """
        Read PM configurations and return as a Message.

        Useful for passing into downstream components that expect Message input.
        Returns a JSON-formatted message with PM configs.
        """
        table = self._get_dynamodb_table()

        if self.operation == "get_item":
            configs = self._get_single_pm(table)
        else:
            configs = self._scan_enabled_pms(table)

        self.status = f"Retrieved {len(configs)} PM config(s)"

        # Build summary for message text
        if not configs:
            summary = "No PM configurations found."
        elif self.operation == "get_item":
            pm = configs[0]
            summary = (
                f"PM Config: {pm.get('name', 'Unknown')} ({pm.get('slack_id')})\n"
                f"Enabled: {pm.get('enabled')}\n"
                f"JIRA Project: {pm.get('jira_config', {}).get('project_key', 'N/A')}\n"
                f"Transcripts Only: {pm.get('flow_config', {}).get('transcripts_only', False)}"
            )
        else:
            pm_list = [
                f"- {pm.get('name', 'Unknown')} ({pm.get('slack_id')})"
                for pm in configs
            ]
            summary = f"Found {len(configs)} enabled PMs:\n" + "\n".join(pm_list)

        return Message(
            text=summary,
            data={
                "pm_configs": configs,
                "count": len(configs),
                "operation": self.operation,
            },
        )
