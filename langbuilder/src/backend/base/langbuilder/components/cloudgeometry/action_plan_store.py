"""
Action Plan Store Component for MeetBot

Stores action plans extracted from meeting transcripts to DynamoDB.
Forked from DynamoDBSessionStoreComponent with a schema tailored to
the MeetBot action plan data model.

The Agent calls this tool after extracting action items from a transcript
to persist the plan for downstream approval/execution by Flow 2.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.data import Data

AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1",
]


class ActionPlanStoreComponent(LCToolComponent):
    """
    Store meeting action plans to DynamoDB.

    Persists action plans extracted from transcripts so the approval flow
    (Flow 2) can retrieve, update, and track item status. Each plan is
    keyed by ``slack_thread_ts`` and contains all action items for a meeting.
    """

    display_name = "Action Plan Store"
    description = (
        "Store a meeting action plan to DynamoDB. Saves action items "
        "extracted from a transcript, keyed by Slack thread timestamp."
    )
    icon = "Amazon"
    name = "ActionPlanStore"

    inputs = [
        DataInput(
            name="structured_data",
            display_name="Structured Data",
            info="Action plan data (used in pipeline mode, not Agent mode)",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="user_message",
            display_name="User Message",
            info="Context message from the agent",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="DynamoDB table name for action plans",
            value="meetbot_action_plan_state_demo",
            required=True,
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="Leave empty to use IAM role or environment credentials",
            required=False,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="Leave empty to use IAM role or environment credentials",
            required=False,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name="AWS Session Token",
            info="For temporary credentials (optional)",
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
        IntInput(
            name="ttl_days",
            display_name="TTL (Days)",
            info="Auto-delete plans after this many days (default: 7)",
            value=7,
            required=False,
            advanced=True,
        ),
    ]

    # ------------------------------------------------------------------ #
    #  DynamoDB helpers (adapted from DynamoDBSessionStoreComponent)
    # ------------------------------------------------------------------ #

    def _get_dynamodb_resource(self):
        """Return a boto3 DynamoDB resource using configured credentials."""
        import boto3

        if self.aws_access_key_id and self.aws_secret_access_key:
            kwargs = {
                "region_name": self.region_name,
                "aws_access_key_id": self.aws_access_key_id,
                "aws_secret_access_key": self.aws_secret_access_key,
            }
            if self.aws_session_token:
                kwargs["aws_session_token"] = self.aws_session_token
            return boto3.resource("dynamodb", **kwargs)
        return boto3.resource("dynamodb", region_name=self.region_name)

    def _put_item(self, item: dict) -> None:
        """Write an item to the configured DynamoDB table."""
        from botocore.exceptions import ClientError

        dynamodb = self._get_dynamodb_resource()
        table = dynamodb.Table(self.table_name)
        try:
            table.put_item(Item=item)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            raise ValueError(f"DynamoDB error ({code}): {msg}") from exc

    def _get_item(self, key: dict) -> dict | None:
        """Read an item from the configured DynamoDB table."""
        from botocore.exceptions import ClientError

        dynamodb = self._get_dynamodb_resource()
        table = dynamodb.Table(self.table_name)
        try:
            resp = table.get_item(Key=key)
            return resp.get("Item")
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            raise ValueError(f"DynamoDB error ({code}): {msg}") from exc

    # ------------------------------------------------------------------ #
    #  run_model — pipeline (non-Agent) execution path
    # ------------------------------------------------------------------ #

    def run_model(self) -> Data:
        """Store action plan data passed via structured_data input."""
        data = self.structured_data
        if isinstance(data, list):
            data = data[0] if data else {}
        output_data = data.data if hasattr(data, "data") else (data if isinstance(data, dict) else {})

        now = datetime.utcnow()
        ttl_timestamp = int((now + timedelta(days=self.ttl_days)).timestamp())

        slack_thread_ts = output_data.get("slack_thread_ts", str(uuid.uuid4()))

        item = {
            "slack_thread_ts": slack_thread_ts,
            "timestamp": now.isoformat(),
            "ttl": ttl_timestamp,
        }
        for k, v in output_data.items():
            if k not in item:
                item[k] = v

        self._put_item(item)
        self.status = f"Stored plan {slack_thread_ts}"
        return Data(data=item)

    # ------------------------------------------------------------------ #
    #  build_tool — Agent execution path
    # ------------------------------------------------------------------ #

    def build_tool(self) -> Tool | list[Tool]:
        """Return Agent tools for storing and retrieving action plans."""

        # --- Store tool schema ---
        class StoreActionPlanInput(BaseModel):
            slack_thread_ts: str = Field(
                description="Slack thread timestamp used as the plan's primary key"
            )
            transcript_doc_id: str = Field(
                description="Google Doc ID of the source transcript"
            )
            organizer_slack_id: str = Field(
                description="Slack user ID of the meeting organizer"
            )
            organizer_email: str = Field(
                default="",
                description="Email of the meeting organizer (for dashboard notifications)",
            )
            meeting_title: str = Field(
                default="",
                description="Title of the meeting",
            )
            items: str = Field(
                description=(
                    "JSON array of action item objects. Each object must have: "
                    "item_id (str), type ('jira_create'|'jira_update'|'confluence_create'|'confluence_update'|'todo'), "
                    "title (str), description (str), assignee_email (str), assignee_slack_id (str), "
                    "jira_project (str), existing_ticket (str or null), priority ('Critical'|'High'|'Medium'|'Low'), "
                    "status ('pending'). Example: "
                    "'[{\"item_id\":\"item-001\",\"type\":\"jira_create\",\"title\":\"Fix login\","
                    "\"description\":\"...\",\"assignee_email\":\"a@co.com\",\"assignee_slack_id\":\"U123\","
                    "\"jira_project\":\"PROJ\",\"existing_ticket\":null,\"priority\":\"High\",\"status\":\"pending\"}]'"
                )
            )

        def _store_action_plan(
            slack_thread_ts: str,
            transcript_doc_id: str,
            organizer_slack_id: str,
            organizer_email: str = "",
            meeting_title: str = "",
            items: str = "[]",
        ) -> str:
            try:
                items_list = json.loads(items)
            except json.JSONDecodeError:
                return "Error: items must be a valid JSON array string"

            now = datetime.utcnow()
            ttl_timestamp = int((now + timedelta(days=self.ttl_days)).timestamp())

            item = {
                "slack_thread_ts": slack_thread_ts,
                "transcript_doc_id": transcript_doc_id,
                "organizer_slack_id": organizer_slack_id,
                "organizer_email": organizer_email,
                "meeting_title": meeting_title,
                "items": items_list,
                "organizer_dashboard_ts": "",
                "created_at": now.isoformat(),
                "ttl": ttl_timestamp,
            }

            try:
                self._put_item(item)
            except ValueError as exc:
                return f"Error: {exc}"

            return json.dumps({
                "status": "stored",
                "slack_thread_ts": slack_thread_ts,
                "item_count": len(items_list),
            })

        store_tool = StructuredTool.from_function(
            name="meetbot_store_action_plan",
            description=(
                "Store a meeting action plan to DynamoDB after extracting items from a transcript. "
                "Call this once per meeting with all action items. The plan is keyed by slack_thread_ts "
                "so the approval flow can retrieve and update it."
            ),
            args_schema=StoreActionPlanInput,
            func=_store_action_plan,
            return_direct=False,
            tags=["meetbot_store_action_plan"],
        )

        # --- Retrieve tool schema ---
        class GetActionPlanInput(BaseModel):
            slack_thread_ts: str = Field(
                description="Slack thread timestamp to look up the action plan"
            )

        def _get_action_plan(slack_thread_ts: str) -> str:
            try:
                item = self._get_item({"slack_thread_ts": slack_thread_ts})
            except ValueError as exc:
                return f"Error: {exc}"

            if item is None:
                return json.dumps({"error": "Plan not found", "slack_thread_ts": slack_thread_ts})
            return json.dumps(item, indent=2, default=str)

        get_tool = StructuredTool.from_function(
            name="meetbot_get_action_plan",
            description=(
                "Retrieve a meeting action plan from DynamoDB by its Slack thread timestamp. "
                "Returns all items and their current statuses."
            ),
            args_schema=GetActionPlanInput,
            func=_get_action_plan,
            return_direct=False,
            tags=["meetbot_get_action_plan"],
        )

        # --- Update item status tool schema ---
        class UpdateItemStatusInput(BaseModel):
            slack_thread_ts: str = Field(
                description="Slack thread timestamp of the action plan"
            )
            item_id: str = Field(
                description="ID of the item to update (e.g., 'item-001')"
            )
            status: str = Field(
                description="New status: 'approved', 'executed', 'rejected', 'timeout_reassigned'"
            )
            executed_ref: str = Field(
                default="",
                description="Reference for executed items (e.g., 'PROJ-456' for JIRA tickets)",
            )

        def _update_item_status(
            slack_thread_ts: str,
            item_id: str,
            status: str,
            executed_ref: str = "",
        ) -> str:
            try:
                plan = self._get_item({"slack_thread_ts": slack_thread_ts})
            except ValueError as exc:
                return f"Error: {exc}"

            if plan is None:
                return json.dumps({"error": "Plan not found"})

            items = plan.get("items", [])
            found = False
            for it in items:
                if it.get("item_id") == item_id:
                    it["status"] = status
                    if executed_ref:
                        it["executed_ref"] = executed_ref
                    it["updated_at"] = datetime.utcnow().isoformat()
                    found = True
                    break

            if not found:
                return json.dumps({"error": f"Item {item_id} not found in plan"})

            plan["items"] = items
            try:
                self._put_item(plan)
            except ValueError as exc:
                return f"Error: {exc}"

            return json.dumps({
                "status": "updated",
                "item_id": item_id,
                "new_status": status,
                "executed_ref": executed_ref,
            })

        update_tool = StructuredTool.from_function(
            name="meetbot_update_item_status",
            description=(
                "Update the status of a single action item in an existing plan. "
                "Use after approving, rejecting, or executing an item."
            ),
            args_schema=UpdateItemStatusInput,
            func=_update_item_status,
            return_direct=False,
            tags=["meetbot_update_item_status"],
        )

        self.status = "Action Plan Store tools created (store, get, update)"
        return [store_tool, get_tool, update_tool]
