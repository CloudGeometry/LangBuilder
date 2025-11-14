"""Jira update issue component for ActionBridge."""

import json

import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, MultilineInput, Output, StrInput
from langbuilder.schema import Data


class JiraUpdateIssue(Component):
    """Jira Update Issue Component.

    Updates an existing Jira issue with new field values.
    Returns a Data object containing the update status.
    """

    display_name = "Jira Update Issue"
    description = "Update an existing Jira issue"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-put"
    icon = "Jira"
    name = "JiraUpdateIssue"

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
            info="The key or ID of the issue to update (e.g., PROJ-123)",
            required=True,
            placeholder="PROJ-123",
        ),
        MessageTextInput(
            name="summary",
            display_name="Summary",
            info="New summary/title (leave empty to keep current)",
            required=False,
        ),
        MultilineInput(
            name="description",
            display_name="Description",
            info="New description (leave empty to keep current)",
            required=False,
        ),
        StrInput(
            name="status",
            display_name="Status",
            info="New status (e.g., In Progress, Done, To Do)",
            required=False,
        ),
        StrInput(
            name="priority",
            display_name="Priority",
            info="New priority (e.g., High, Medium, Low)",
            required=False,
        ),
        StrInput(
            name="assignee",
            display_name="Assignee",
            info="Account ID or email of new assignee",
            required=False,
        ),
        MessageTextInput(
            name="labels",
            display_name="Labels",
            info="Comma-separated list of labels (replaces existing)",
            required=False,
        ),
        MultilineInput(
            name="comment",
            display_name="Comment",
            info="Add a comment to the issue",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Update Result",
            name="result",
            method="update_issue",
        ),
    ]

    def update_issue(self) -> Data:
        """Update an existing Jira issue.

        Returns:
            Data: Object containing update status and issue details
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

            # Build update fields
            fields = {}

            if self.summary:
                fields["summary"] = self.summary

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

            if self.priority:
                fields["priority"] = {"name": self.priority}

            if self.assignee:
                fields["assignee"] = {"id": self.assignee} if "@" not in self.assignee else {"emailAddress": self.assignee}

            if self.labels:
                labels_list = [label.strip() for label in self.labels.split(",")]
                fields["labels"] = labels_list

            updates_made = []

            # Update fields if any are provided
            if fields:
                payload = {"fields": fields}

                self.log(f"Updating Jira issue {self.issue_key}")

                response = requests.put(
                    f"{jira_url}/rest/api/3/issue/{self.issue_key}",
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=30,
                )

                response.raise_for_status()
                updates_made.extend(fields.keys())

            # Handle status transition separately if provided
            if self.status:
                # Get available transitions
                transitions_response = requests.get(
                    f"{jira_url}/rest/api/3/issue/{self.issue_key}/transitions",
                    headers=headers,
                    timeout=30,
                )
                transitions_response.raise_for_status()
                transitions = transitions_response.json().get("transitions", [])

                # Find matching transition
                transition_id = None
                for transition in transitions:
                    if transition["name"].lower() == self.status.lower():
                        transition_id = transition["id"]
                        break

                if transition_id:
                    transition_payload = {"transition": {"id": transition_id}}

                    transition_response = requests.post(
                        f"{jira_url}/rest/api/3/issue/{self.issue_key}/transitions",
                        headers=headers,
                        data=json.dumps(transition_payload),
                        timeout=30,
                    )
                    transition_response.raise_for_status()
                    updates_made.append("status")
                    self.log(f"Transitioned issue to {self.status}")
                else:
                    self.log(f"Warning: Status '{self.status}' not available for this issue")

            # Add comment if provided
            if self.comment:
                comment_payload = {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": self.comment}],
                            }
                        ],
                    }
                }

                comment_response = requests.post(
                    f"{jira_url}/rest/api/3/issue/{self.issue_key}/comment",
                    headers=headers,
                    data=json.dumps(comment_payload),
                    timeout=30,
                )
                comment_response.raise_for_status()
                updates_made.append("comment")
                self.log("Added comment to issue")

            result = {
                "issue_key": self.issue_key,
                "updated": True,
                "fields_updated": updates_made,
                "url": f"{jira_url}/browse/{self.issue_key}",
            }

            self.status = f"Updated issue {self.issue_key}"
            self.log(f"Successfully updated Jira issue {self.issue_key}")

            return Data(data=result)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Update failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "updated": False, "issue_key": self.issue_key})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "updated": False, "issue_key": self.issue_key})

        except Exception as e:
            error_msg = f"Update failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "updated": False, "issue_key": self.issue_key})
