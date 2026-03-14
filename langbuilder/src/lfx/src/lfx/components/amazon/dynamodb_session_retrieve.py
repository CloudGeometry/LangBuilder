"""
DynamoDB Session Retrieve Component for LangBuilder

Retrieves conversation session data from AWS DynamoDB for session resumption
and analytics.

Adapted for LangBuilder 1.65 (CloudGeometry fork)
"""

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.message import Message

# AWS region options (same as store component)
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1"
]


class DynamoDBSessionRetrieveComponent(Component):
    """
    Retrieve session data from AWS DynamoDB table.

    This component fetches stored session data by session_id. Returns the full
    session data if found, or an error message if not found.
    """

    display_name = "DynamoDB Retrieve"
    description = (
        "Retrieve session data from Amazon DynamoDB by session_id. "
        "Returns stored metadata for session resumption and analytics."
    )
    icon = "Amazon"
    name = "DynamoDBSessionRetrieve"

    inputs = [
        # Session identification
        MessageTextInput(
            name="session_id",
            display_name="Session ID",
            info="UUID or unique identifier to retrieve",
            required=True,
            tool_mode=True,
        ),

        # DynamoDB configuration
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="DynamoDB table name",
            value="langbuilder_sessions",
            required=True,
        ),

        # AWS credentials (secured inputs)
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="AWS Access Key ID (leave empty to use IAM role or environment credentials)",
            value="AWS_ACCESS_KEY_ID",
            required=False,
        ),

        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="AWS Secret Access Key (leave empty to use IAM role or environment credentials)",
            value="AWS_SECRET_ACCESS_KEY",
            required=False,
        ),

        DropdownInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region where DynamoDB table is located",
            options=AWS_REGIONS,
            value="us-west-2",
            required=True,
        ),
    ]

    outputs = [
        # Success path - session found
        Output(
            name="session_data",
            display_name="Session Data",
            method="retrieve_session",
        ),
    ]

    def retrieve_session(self) -> Message:
        """
        Retrieve session data from DynamoDB.

        Returns:
            Message object with session data or error message
        """
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

        # Initialize DynamoDB client
        try:
            if self.aws_access_key_id and self.aws_secret_access_key:
                dynamodb = boto3.resource(
                    "dynamodb",
                    region_name=self.region_name,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
                self.log("Using provided AWS credentials")
            else:
                dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self.log("Using IAM role or environment credentials")

            table = dynamodb.Table(self.table_name)

        except Exception as e:
            msg = f"Failed to initialize DynamoDB client: {e}"
            raise ValueError(msg) from e

        # Log operation
        self.log(f"Retrieving session {self.session_id} from table {self.table_name}")

        # Get item from DynamoDB
        try:
            response = table.get_item(Key={"session_id": str(self.session_id)})

            # Check if item was found
            if "Item" in response:
                item = response["Item"]
                self.log(f"Session {self.session_id} found")
                self.log(f"Session data keys: {list(item.keys())}")

                # Update status
                self.status = f"Retrieved session {self.session_id}"

                # Return session data
                return Message(
                    text=f"Session {self.session_id} retrieved successfully",
                    data=item,
                )
            else:
                # Session not found
                self.log(f"Session {self.session_id} not found in table")
                self.status = f"Session {self.session_id} not found"

                # Return not found message
                return Message(
                    text=f"Session {self.session_id} not found in {self.table_name}",
                    data={
                        "session_id": str(self.session_id),
                        "found": False,
                        "table_name": self.table_name,
                    },
                )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            msg = f"DynamoDB error ({error_code}): {error_msg}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

        except Exception as e:
            msg = f"Unexpected error retrieving session: {e}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e
