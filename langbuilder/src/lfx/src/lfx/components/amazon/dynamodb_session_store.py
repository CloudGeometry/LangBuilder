"""
DynamoDB Session Store Component for LangBuilder

Stores conversation session data to AWS DynamoDB for persistence,
analytics, and session resumption capabilities.

Adapted for LangBuilder 1.65 (CloudGeometry fork)
"""

import time
import uuid
from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.field_typing import Tool
from lfx.io import BoolInput, DataInput, DropdownInput, IntInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.data import Data

# AWS region options for dropdown
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1"
]


class DynamoDBSessionStoreComponent(LCToolComponent):
    """
    Store session data to AWS DynamoDB table.

    This component saves conversation session data to DynamoDB with automatic
    TTL for cleanup. It accepts Data input from Structured Output component,
    making it easy to store structured conversation metadata.
    """

    display_name = "DynamoDB Store"
    description = (
        "Store session data to Amazon DynamoDB with automatic TTL. "
        "Accepts Data from Structured Output for easy integration."
    )
    icon = "Amazon"
    name = "DynamoDBSessionStore"

    inputs = [
        # Data input from Structured Output
        DataInput(
            name="structured_data",
            display_name="Structured Data",
            info="Data from Structured Output component containing conversation metadata",
            required=True,
            tool_mode=True,  # Agent can pass data when calling as tool
        ),

        # User message input
        MessageTextInput(
            name="user_message",
            display_name="User Message",
            info="The user's message (from Chat Input)",
            required=True,
            tool_mode=True,  # Agent can pass context when calling as tool
        ),

        # Session identification
        MessageTextInput(
            name="session_id",
            display_name="Session ID",
            info="UUID or unique identifier for this session. Auto-generates if empty.",
            required=False,
        ),

        # DynamoDB configuration
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="DynamoDB table name",
            value="langbuilder_sessions",
            required=True,
        ),

        StrInput(
            name="primary_key_name",
            display_name="Primary Key Name",
            info="Name of the DynamoDB partition key attribute. Default 'session_id'. "
                 "Set to match your table's key (e.g. 'slack_user_id'). "
                 "When using a custom key, include it in structured_data or answers JSON.",
            value="session_id",
            required=False,
            advanced=True,
        ),

        # AWS credentials (secured inputs)
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
            info="AWS region where DynamoDB table is located",
            options=AWS_REGIONS,
            value="us-west-2",
            required=True,
        ),

        # TTL configuration
        IntInput(
            name="ttl_days",
            display_name="TTL (Days)",
            info="Time To Live in days - sessions auto-delete after this period (default: 30)",
            value=30,
            required=False,
            advanced=True,
        ),

        # Auto-create table option
        BoolInput(
            name="auto_create_table",
            display_name="Auto Create Table",
            info="Automatically create the DynamoDB table if it doesn't exist",
            value=True,
            advanced=True,
        ),
    ]

    # Uses default outputs from LCToolComponent base class

    def _ensure_table_exists(self, dynamodb, table):
        """
        Check if DynamoDB table exists, create it if not.

        Args:
            dynamodb: boto3 DynamoDB resource
            table: DynamoDB Table object

        Returns:
            DynamoDB Table object (existing or newly created)
        """
        from botocore.exceptions import ClientError

        try:
            # Try to get table status - this will fail if table doesn't exist
            table.load()
            self.log(f"Table {self.table_name} exists (status: {table.table_status})")
            return table

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "ResourceNotFoundException":
                self.log(f"Table {self.table_name} not found, creating...")

                # Create the table
                try:
                    pk_name = getattr(self, "primary_key_name", "session_id") or "session_id"
                    new_table = dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {"AttributeName": pk_name, "KeyType": "HASH"}
                        ],
                        AttributeDefinitions=[
                            {"AttributeName": pk_name, "AttributeType": "S"}
                        ],
                        BillingMode="PAY_PER_REQUEST"
                    )

                    # Wait for table to be created
                    self.log(f"Waiting for table {self.table_name} to be created...")
                    new_table.wait_until_exists()
                    self.log(f"Table {self.table_name} created successfully")

                    # Enable TTL on the table
                    try:
                        client = dynamodb.meta.client
                        client.update_time_to_live(
                            TableName=self.table_name,
                            TimeToLiveSpecification={
                                "Enabled": True,
                                "AttributeName": "ttl"
                            }
                        )
                        self.log(f"TTL enabled on table {self.table_name}")
                    except Exception as ttl_error:
                        self.log(f"Warning: Could not enable TTL: {ttl_error}")

                    return new_table

                except Exception as create_error:
                    msg = f"Failed to create table {self.table_name}: {create_error}"
                    self.log(f"Error: {msg}")
                    raise ValueError(msg) from create_error
            else:
                # Re-raise other errors
                raise

    def run_model(self) -> Data:
        """
        Store session data to DynamoDB.

        Returns:
            Data object with confirmation and stored data
        """
        # Import boto3 (raises ImportError if not installed)
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as e:
            msg = (
                "boto3 is not installed. Please install it using: "
                "uv pip install boto3"
            )
            raise ImportError(msg) from e

        # Extract data from structured_data input
        data = self.structured_data
        if isinstance(data, list):
            data = data[0] if data else {}

        # Get the data dict from Data object
        if hasattr(data, "data"):
            output_data = data.data
        elif isinstance(data, dict):
            output_data = data
        else:
            output_data = {}

        # Initialize DynamoDB client
        try:
            # Use credentials if provided, otherwise use IAM role or environment
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs = {
                    "region_name": self.region_name,
                    "aws_access_key_id": self.aws_access_key_id,
                    "aws_secret_access_key": self.aws_secret_access_key,
                }
                # Add session token if provided (for temporary credentials)
                if self.aws_session_token:
                    client_kwargs["aws_session_token"] = self.aws_session_token
                    self.log("Using temporary session credentials")
                else:
                    self.log("Using provided AWS credentials")
                dynamodb = boto3.resource("dynamodb", **client_kwargs)
            else:
                dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self.log("Using IAM role or environment credentials")

            # Check if table exists, create if needed
            table = dynamodb.Table(self.table_name)

            if self.auto_create_table:
                table = self._ensure_table_exists(dynamodb, table)

        except Exception as e:
            msg = f"Failed to initialize DynamoDB client: {e}"
            raise ValueError(msg) from e

        # Calculate TTL timestamp
        now = datetime.utcnow()
        ttl_timestamp = int((now + timedelta(days=self.ttl_days)).timestamp())

        # Get session_id - priority order:
        # 1. From session_id input (if it's a string)
        # 2. From Message object's session_id (if Message passed to session_id input)
        # 3. From graph's session_id (flow-level session from API call)
        # 4. Auto-generate UUID as last resort
        raw_session_id = self.session_id
        session_id = ""

        # Check if session_id input is a plain string
        if isinstance(raw_session_id, str) and raw_session_id.strip():
            session_id = raw_session_id.strip()
        # Check if it's a Message object - extract its session_id
        elif hasattr(raw_session_id, 'session_id') and hasattr(raw_session_id, 'text'):
            msg_session_id = getattr(raw_session_id, 'session_id', None)
            if msg_session_id:
                session_id = str(msg_session_id).strip()

        # If still empty, try to get from graph's session_id (API-level session)
        if not session_id and hasattr(self, 'graph') and hasattr(self.graph, 'session_id') and self.graph.session_id:
            session_id = str(self.graph.session_id).strip()

        # Last resort: auto-generate (but this breaks conversation continuity!)
        if not session_id:
            session_id = str(uuid.uuid4())
            self.log("WARNING: Auto-generated session_id - conversation continuity will be lost!")

        # Determine primary key name (configurable, default: "session_id")
        pk_name = getattr(self, "primary_key_name", "session_id") or "session_id"

        # Prepare item to save - base required fields
        item = {
            "timestamp": now.isoformat(),
            "ttl": ttl_timestamp,  # DynamoDB TTL attribute
            "user_message": str(self.user_message),
        }

        # Dynamically include ALL fields from structured data
        # This allows storing any data shape (contact info, conversation state, etc.)
        for key, value in output_data.items():
            if key not in item:  # Don't overwrite mandatory fields
                item[key] = value

        # Set primary key: use value from structured_data if present, else session_id
        if pk_name != "session_id":
            if pk_name in item:
                # Already at top level from structured_data
                self.log(f"Using primary key '{pk_name}' = '{item[pk_name]}' from structured data")
            elif "answers" in item and isinstance(item["answers"], dict) and pk_name in item["answers"]:
                # Found inside answers dict — promote to top level as primary key
                item[pk_name] = item["answers"][pk_name]
                self.log(f"Using primary key '{pk_name}' = '{item[pk_name]}' from answers")
            else:
                # Custom key not found in data, fall back to session_id value
                item[pk_name] = session_id
                self.log(f"WARNING: '{pk_name}' not found in data, using session_id as fallback")
        else:
            # Default: use session_id as the primary key
            item[pk_name] = session_id

        # Log operation
        self.log(f"Storing to table {self.table_name} with {pk_name}={item.get(pk_name, 'unknown')}")
        self.log(f"Fields: {list(output_data.keys())}")
        self.log(f"TTL: {ttl_timestamp} ({self.ttl_days} days from now)")

        # Put item to DynamoDB
        try:
            table.put_item(Item=item)
            self.log(f"Stored successfully: {pk_name}={item.get(pk_name, 'unknown')}")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            msg = f"DynamoDB error ({error_code}): {error_msg}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

        except Exception as e:
            msg = f"Unexpected error storing session: {e}"
            self.log(f"Error: {msg}")
            raise ValueError(msg) from e

        # Update status (visible in component UI)
        self.status = f"Stored {pk_name}={item.get(pk_name, 'unknown')}"

        # Return Data object with stored information
        return Data(data=item)

    async def _get_tools(self):
        """Override to return the named tool from build_tool() instead of generic outputs."""
        tool = self.build_tool()
        # Ensure tool has tags for framework compatibility
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """
        Build a LangChain tool for storing session data to DynamoDB.

        Returns:
            StructuredTool: A tool that can be used by an Agent to store data.
        """
        # Define flexible schema for conversation state
        class StoreConversationStateInput(BaseModel):
            answers: str = Field(
                default="",
                description="JSON string of question answers, e.g. '{\"q1\": \"B\", \"q2\": \"A\"}'"
            )
            phase: str = Field(
                default="discovery",
                description="Current conversation phase: 'opening', 'discovery', 'closing', 'complete'"
            )
            current_question: str = Field(
                default="",
                description="Current question being asked, e.g. 'q3' or 'email'"
            )
            persona_hint: str = Field(
                default="",
                description="Detected persona type, e.g. 'Exec-leaning', 'Technical', 'General'"
            )
            blueprint: str = Field(
                default="",
                description="Generated blueprint or proposal content"
            )
            name: str = Field(
                default="",
                description="Contact's name (if collected)"
            )
            email: str = Field(
                default="",
                description="Contact's email (if collected)"
            )
            company: str = Field(
                default="",
                description="Contact's company (if collected)"
            )

        def _store_conversation_state(
            answers: str = "",
            phase: str = "discovery",
            current_question: str = "",
            persona_hint: str = "",
            blueprint: str = "",
            name: str = "",
            email: str = "",
            company: str = ""
        ) -> str:
            """Tool function that stores full conversation state."""
            import json as json_module

            # Parse answers if it's a JSON string
            answers_dict = {}
            if answers:
                try:
                    answers_dict = json_module.loads(answers)
                except:
                    answers_dict = {"raw": answers}

            # Build the full state object
            state_data = {
                "phase": phase,
                "current_question": current_question,
                "persona_hint": persona_hint,
                "answers": answers_dict,
                "questions_answered": list(answers_dict.keys()) if answers_dict else [],
            }

            # Add optional fields if provided
            if blueprint:
                state_data["blueprint"] = blueprint
            if name:
                state_data["name"] = name
            if email:
                state_data["email"] = email
            if company:
                state_data["company"] = company

            # Set the structured_data attribute
            self.structured_data = Data(data=state_data)

            # Set user_message
            if not self.user_message:
                self.user_message = f"Conversation state saved at phase: {phase}"

            # Call run_model to store
            result = self.run_model()
            if hasattr(result, 'data'):
                session_id = result.data.get('session_id', 'unknown')
                return f"Conversation state saved. Phase: {phase}, Questions: {list(answers_dict.keys())}, Session: {session_id}"
            return f"Conversation state saved. Phase: {phase}"

        tool = StructuredTool.from_function(
            name="store_conversation_state",
            description=(
                "Store full conversation state to DynamoDB. Use this after each question is answered "
                "to persist the conversation progress. Pass answers as a JSON string like "
                "'{\"q1\": \"B\", \"q2\": \"A\"}'. Also use this to save the blueprint/proposal content."
            ),
            args_schema=StoreConversationStateInput,
            func=_store_conversation_state,
            return_direct=False,
            tags=["store_conversation_state"],
        )

        self.status = "DynamoDB Conversation State Tool created"
        return tool
