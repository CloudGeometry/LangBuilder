"""AWS Lambda Invoke Component

Invoke AWS Lambda functions from LangBuilder flows.
Supports both synchronous and asynchronous invocation.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langflow.custom import Component
from langflow.io import (
    DropdownInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from langflow.schema.data import Data

if TYPE_CHECKING:
    pass


class AWSLambdaInvokeComponent(Component):
    """Invoke AWS Lambda functions from LangBuilder flows.

    Calls Lambda functions using boto3, supports both synchronous
    (RequestResponse) and asynchronous (Event) invocation types.

    **Authentication:** Uses AWS credentials from inputs or falls back
    to IAM role/environment variables.
    """

    display_name = "AWS Lambda Invoke"
    description = (
        "Invoke AWS Lambda functions with JSON payloads. Supports sync "
        "and async invocation."
    )
    documentation = (
        "https://boto3.amazonaws.com/v1/documentation/api/latest/"
        "reference/services/lambda.html#Lambda.Client.invoke"
    )
    icon = "AWS"
    name = "AWSLambdaInvoke"

    inputs = [
        StrInput(
            name="function_name",
            display_name="Function Name",
            info="Lambda function name or ARN (e.g. pm-buddy-beta-schedule-manager).",
            required=True,
            placeholder="my-function-name",
        ),
        MessageTextInput(
            name="payload_json",
            display_name="Payload (JSON)",
            info="JSON payload to send to the Lambda function. Can be connected from upstream.",
            required=False,
            tool_mode=True,
        ),
        DropdownInput(
            name="invocation_type",
            display_name="Invocation Type",
            options=["Event", "RequestResponse"],
            value="Event",
            info="Event = async (fire-and-forget), RequestResponse = sync (wait for response).",
        ),
        StrInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region (e.g. us-west-2). Leave empty to use default.",
            value="us-west-2",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            info="Leave empty to use IAM role or environment credentials.",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            info="Leave empty to use IAM role or environment credentials.",
            required=False,
            advanced=True,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name="AWS Session Token",
            info="For temporary credentials (optional).",
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name="Response",
            name="response",
            method="invoke_lambda",
        ),
    ]

    def invoke_lambda(self) -> Data:
        """Invoke the Lambda function.

        Returns:
            Data: Object containing status_code, payload (if sync), and metadata
        """
        try:
            import boto3
            import os

            # Get function name
            function_name = self.function_name
            if not function_name or not function_name.strip():
                return Data(data={
                    "error": "function_name is required",
                    "status_code": 400,
                    "success": False
                })

            # Get payload
            payload_data = self.payload_json
            if hasattr(payload_data, "text"):
                payload_str = payload_data.text
            elif hasattr(payload_data, "data"):
                payload_str = json.dumps(payload_data.data)
            elif isinstance(payload_data, dict):
                payload_str = json.dumps(payload_data)
            elif isinstance(payload_data, str):
                payload_str = payload_data if payload_data.strip() else "{}"
            else:
                payload_str = "{}"

            # Validate JSON
            try:
                json.loads(payload_str)
            except json.JSONDecodeError as e:
                return Data(data={
                    "error": f"Invalid JSON payload: {e}",
                    "status_code": 400,
                    "success": False
                })

            # Create boto3 client with credentials
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs = {
                    "region_name": self.region_name or "us-west-2",
                    "aws_access_key_id": self.aws_access_key_id,
                    "aws_secret_access_key": self.aws_secret_access_key,
                }
                if self.aws_session_token:
                    client_kwargs["aws_session_token"] = self.aws_session_token
                    self.log("Using temporary session credentials")
                else:
                    self.log("Using provided AWS credentials")
                lambda_client = boto3.client('lambda', **client_kwargs)
            else:
                # Fall back to IAM role or environment variables
                self.log("Using IAM role or environment credentials")
                lambda_client = boto3.client('lambda', region_name=self.region_name or "us-west-2")

            # Invoke Lambda
            self.log(f"Invoking Lambda: {function_name} ({self.invocation_type})")

            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=self.invocation_type,
                Payload=payload_str.encode('utf-8')
            )

            status_code = response.get('StatusCode', 0)

            # For async (Event), there's no response payload
            if self.invocation_type == "Event":
                self.status = f"Lambda invoked (async): {function_name}"
                self.log(f"Async invocation complete: {function_name} (status {status_code})")
                return Data(data={
                    "status_code": status_code,
                    "function_name": function_name,
                    "invocation_type": "Event",
                    "success": status_code == 202,
                    "message": "Lambda invoked asynchronously"
                })

            # For sync (RequestResponse), parse response payload
            response_payload = response.get('Payload')
            if response_payload:
                response_data = json.loads(response_payload.read().decode('utf-8'))
            else:
                response_data = {}

            self.status = f"Lambda invoked: {function_name}"
            self.log(f"Sync invocation complete: {function_name} (status {status_code})")

            return Data(data={
                "status_code": status_code,
                "function_name": function_name,
                "invocation_type": "RequestResponse",
                "success": status_code == 200,
                "response_payload": response_data
            })

        except Exception as e:
            error_msg = f"Lambda invocation failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={
                "error": error_msg,
                "status_code": 500,
                "success": False
            })
