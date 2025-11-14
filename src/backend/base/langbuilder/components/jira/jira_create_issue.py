"""Jira create issue component for ActionBridge."""

import json

import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, DropdownInput, MessageTextInput, MultilineInput, Output, StrInput
from langbuilder.schema import Data


class JiraCreateIssue(Component):
    """Jira Create Issue Component.

    Creates a new issue in Jira with specified fields.
    Returns a Data object containing the created issue details.
    """

    display_name = "Jira Create Issue"
    description = "Create a new issue in Jira"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-post"
    icon = "Jira"
    name = "JiraCreateIssue"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Authentication credentials from Jira Auth component",
            required=True,
        ),
        StrInput(
            name="project_key",
            display_name="Project Key",
            info="The key of the project (e.g., PROJ, DEV, TEST)",
            required=True,
            placeholder="PROJ",
        ),
        MessageTextInput(
            name="summary",
            display_name="Summary",
            info="Issue summary/title",
            required=True,
            placeholder="Brief description of the issue",
        ),
        MultilineInput(
            name="description",
            display_name="Description",
            info="Detailed description of the issue",
            required=False,
            placeholder="Detailed description...",
        ),
        DropdownInput(
            name="issue_type",
            display_name="Issue Type",
            options=["Task", "Story", "Bug", "Epic", "Subtask"],
            value="Task",
            info="Type of issue to create",
        ),
        StrInput(
            name="priority",
            display_name="Priority",
            info="Issue priority (e.g., High, Medium, Low, Highest, Lowest)",
            value="Medium",
            required=False,
        ),
        StrInput(
            name="assignee",
            display_name="Assignee",
            info="Account ID or email of assignee (leave empty for unassigned)",
            required=False,
        ),
        MessageTextInput(
            name="labels",
            display_name="Labels",
            info="Comma-separated list of labels",
            required=False,
            placeholder="backend, urgent, customer-request",
        ),
    ]

    outputs = [
        Output(
            display_name="Created Issue",
            name="issue",
            method="create_issue",
        ),
    ]

    def create_issue(self) -> Data:
        """Create a new Jira issue.

        Returns:
            Data: Object containing created issue details
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

            # Build issue fields
            fields = {
                "project": {"key": self.project_key},
                "summary": self.summary,
                "issuetype": {"name": self.issue_type},
            }

            # Add description if provided
            if self.description:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": self.description}],
                        }
                    ],
                }

            # Add priority if provided
            if self.priority:
                fields["priority"] = {"name": self.priority}

            # Add assignee if provided
            if self.assignee:
                fields["assignee"] = {"id": self.assignee} if "@" not in self.assignee else {"emailAddress": self.assignee}

            # Add labels if provided
            if self.labels:
                labels_list = [label.strip() for label in self.labels.split(",")]
                fields["labels"] = labels_list

            # Prepare payload
            payload = {"fields": fields}

            self.log(f"Creating Jira issue in project {self.project_key}")

            # Make API request
            response = requests.post(
                f"{jira_url}/rest/api/3/issue",
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            result_data = response.json()

            # Extract key information
            issue_key = result_data.get("key")
            issue_id = result_data.get("id")
            issue_self = result_data.get("self")

            issue_info = {
                "key": issue_key,
                "id": issue_id,
                "self": issue_self,
                "project": self.project_key,
                "summary": self.summary,
                "issue_type": self.issue_type,
                "url": f"{jira_url}/browse/{issue_key}",
                "created": True,
            }

            self.status = f"Created issue {issue_key}"
            self.log(f"Successfully created Jira issue {issue_key}")

            return Data(data=issue_info)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Creation failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})

        except Exception as e:
            error_msg = f"Issue creation failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "created": False})
