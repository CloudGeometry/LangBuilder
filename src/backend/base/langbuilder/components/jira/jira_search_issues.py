"""Jira search issues component for ActionBridge."""

import json

import requests

from langbuilder.custom import Component
from langbuilder.io import DataInput, IntInput, MessageTextInput, MultilineInput, Output
from langbuilder.schema import Data


class JiraSearchIssues(Component):
    """Jira Search Issues Component.

    Searches for Jira issues using JQL (Jira Query Language).
    Returns a Data object containing search results with issue details.
    """

    display_name = "Jira Search Issues"
    description = "Search for Jira issues using JQL queries"
    documentation = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/"
    icon = "Jira"
    name = "JiraSearchIssues"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="Jira Auth",
            info="Authentication credentials from Jira Auth component",
            required=True,
        ),
        MultilineInput(
            name="jql_query",
            display_name="JQL Query",
            info='Jira Query Language query (e.g., "project = PROJ AND status = Open")',
            required=True,
            placeholder="project = PROJ AND assignee = currentUser() ORDER BY updated DESC",
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="Maximum number of issues to return (1-100)",
            value=50,
            required=False,
        ),
        MessageTextInput(
            name="fields",
            display_name="Fields to Return",
            info="Comma-separated list of fields (leave empty for all fields)",
            value="*all",
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Search Results",
            name="results",
            method="search_issues",
        ),
    ]

    def search_issues(self) -> Data:
        """Search for Jira issues using JQL.

        Returns:
            Data: Object containing search results with issues array
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

            # Validate max_results
            max_results = max(1, min(100, self.max_results))

            # Parse fields
            fields_list = ["*all"] if not self.fields or self.fields == "*all" else [f.strip() for f in self.fields.split(",")]

            # Prepare search payload
            payload = {
                "jql": self.jql_query,
                "maxResults": max_results,
                "fields": fields_list,
            }

            self.log(f"Searching Jira with JQL: {self.jql_query}")

            # Make API request using the current v3 search endpoint
            response = requests.post(
                f"{jira_url}/rest/api/3/search/jql",
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )

            # Check response
            response.raise_for_status()
            result_data = response.json()

            # Extract key information
            issues = result_data.get("issues", [])
            total = result_data.get("total", 0)

            # Simplify issue data for easier consumption
            simplified_issues = []
            for issue in issues:
                simplified_issue = {
                    "key": issue.get("key"),
                    "id": issue.get("id"),
                    "self": issue.get("self"),
                    "fields": issue.get("fields", {}),
                }
                simplified_issues.append(simplified_issue)

            search_results = {
                "total": total,
                "maxResults": result_data.get("maxResults", 0),
                "startAt": result_data.get("startAt", 0),
                "count": len(issues),
                "issues": simplified_issues,
                "jql": self.jql_query,
            }

            self.status = f"Found {total} issues (showing {len(issues)})"
            self.log(f"Successfully retrieved {len(issues)} issues from Jira")

            return Data(data=search_results)

        except requests.exceptions.HTTPError as e:
            error_msg = f"Jira API error: {e.response.status_code} - {e.response.text}"
            self.status = f"Search failed: {e.response.status_code}"
            self.log(error_msg)
            return Data(data={"error": error_msg, "issues": [], "total": 0})

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "issues": [], "total": 0})

        except Exception as e:
            error_msg = f"Search failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "issues": [], "total": 0})
