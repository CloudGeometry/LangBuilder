"""Jira get issue component for ActionBridge."""


import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class JiraGetIssue(Component):
    """Jira Get Issue Component.

    Retrieves details of a single Jira issue by its key or ID.
    Returns a Data object containing issue details and fields.
    """

    display_name = "Jira Get Issue"
    description = "Retrieve details of a single Jira issue"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-get"
    icon = "Jira"
    name = "JiraGetIssue"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Authentication credentials from Jira Auth component",
            required=True,
        ),
        StrInput(
            name="issue_key",
            display_name="Issue Key",
            info="The key or ID of the issue to retrieve (e.g., PROJ-123)",
            required=True,
            placeholder="PROJ-123",
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (leave empty for all fields)",
            value="*all",
            required=False,
        ),
        MessageTextInput(
            name="expand",
            display_name="Expand",
            info="Comma-separated list of parameters to expand (e.g., changelog, renderedFields)",
            required=False,
            placeholder="changelog,renderedFields",
        ),
    ]

    outputs = [
        Output(
            display_name="Issue Details",
            name="issue",
            method="get_issue",
        ),
    ]

    def get_issue(self) -> Data:
        """Retrieve a single Jira issue by key or ID.

        Returns:
            Data: Object containing issue details
        """
        try:
            # Extract auth data
            auth_data = self.auth_credentials.data if hasattr(self.auth_credentials, "data") else self.auth_credentials

            if not isinstance(auth_data, dict):
                raise ValueError("Invalid authentication data. Please connect a Jira Auth component.")

            if not auth_data.get("authenticated", False):
                error = auth_data.get("error", "Authentication not established")
                raise ValueError(f"Authentication failed: {error}")

            jira_url = auth_data["jira_url"]
            headers = auth_data["headers"]

            # Build query parameters
            params = {}

            # Parse fields
            if self.fields and self.fields != "*all":
                fields_list = [f.strip() for f in self.fields.split(",")]
                params["fields"] = ",".join(fields_list)

            # Parse expand
            if self.expand:
                expand_list = [e.strip() for e in self.expand.split(",")]
                params["expand"] = ",".join(expand_list)

            self.log(f"Retrieving Jira issue {self.issue_key}")

            # Make API request
            response = requests.get(
                f"{jira_url}/rest/api/3/issue/{self.issue_key}",
                headers=headers,
                params=params,
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            issue_data = response.json()

            # Extract key information
            fields = issue_data.get("fields", {})

            # Build simplified issue object
            issue_info = {
                "key": issue_data.get("key"),
                "id": issue_data.get("id"),
                "self": issue_data.get("self"),
                "url": f"{jira_url}/browse/{issue_data.get('key')}",
                # Common fields
                "summary": fields.get("summary"),
                "description": self._extract_description(fields.get("description")),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "project": {
                    "key": fields.get("project", {}).get("key"),
                    "name": fields.get("project", {}).get("name"),
                },
                "assignee": self._extract_user(fields.get("assignee")),
                "reporter": self._extract_user(fields.get("reporter")),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "labels": fields.get("labels", []),
                # Full fields for advanced use
                "all_fields": fields,
            }

            # Add expanded data if requested
            if self.expand:
                if "changelog" in self.expand and "changelog" in issue_data:
                    issue_info["changelog"] = issue_data["changelog"]
                if "renderedFields" in self.expand and "renderedFields" in issue_data:
                    issue_info["renderedFields"] = issue_data["renderedFields"]

            self.status = f"Retrieved issue {self.issue_key}"
            self.log(f"Successfully retrieved Jira issue {self.issue_key}")

            return Data(data=issue_info)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Retrieval failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "issue_key": self.issue_key})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "issue_key": self.issue_key})

        except Exception as e:
            error_msg = f"Retrieval failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "issue_key": self.issue_key})

    def _extract_description(self, description_obj: dict | None) -> str | None:
        """Extract plain text from Jira's Atlassian Document Format (ADF).

        Args:
            description_obj: ADF description object

        Returns:
            Plain text description or None
        """
        if not description_obj:
            return None

        try:
            content = description_obj.get("content", [])
            text_parts = []

            for block in content:
                if block.get("type") == "paragraph":
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))

            return " ".join(text_parts) if text_parts else None
        except Exception:
            return str(description_obj)

    def _extract_user(self, user_obj: dict | None) -> dict | None:
        """Extract user information from Jira user object.

        Args:
            user_obj: Jira user object

        Returns:
            Simplified user dict or None
        """
        if not user_obj:
            return None

        return {
            "account_id": user_obj.get("accountId"),
            "display_name": user_obj.get("displayName"),
            "email": user_obj.get("emailAddress"),
            "active": user_obj.get("active"),
        }
