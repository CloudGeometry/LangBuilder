"""Tests for the JiraStateFetcher component."""

import json
from unittest.mock import Mock, patch

import pytest
import requests
from langbuilder.components.cloudgeometry.jira_state_fetcher import JiraStateFetcherComponent
from langbuilder.schema import Data
from langbuilder.schema.message import Message

from tests.base import ComponentTestBaseWithoutClient


class TestJiraStateFetcherComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        """Return the component class to test."""
        return JiraStateFetcherComponent

    @pytest.fixture
    def default_kwargs(self):
        """Return the default kwargs for the component."""
        return {
            "auth_credentials": None,
            "jira_url": "https://test.atlassian.net",
            "email_input": None,
            "email": "test@example.com",
            "api_token": "test-token",
            "auth_type": "basic",
            "project_key_input": None,
            "project_key": "TEST",
            "jql_filter": "",
            "max_tickets": 100,
            "fetch_details": False,
            "include_description": True,
            "include_comments": False,
            "max_comments": 5,
            "fields": "*all",
            "timeout": 60,
        }

    @pytest.fixture
    def file_names_mapping(self):
        """Return an empty list since this component doesn't have version-specific files."""
        return []

    @pytest.fixture
    async def component(self, component_class, default_kwargs):
        """Return a component instance."""
        return component_class(**default_kwargs)

    @pytest.fixture
    def mock_jira_response(self):
        """Return a mock Jira search response."""
        return {
            "total": 2,
            "maxResults": 100,
            "startAt": 0,
            "issues": [
                {
                    "key": "TEST-1",
                    "id": "10001",
                    "fields": {
                        "summary": "Test Issue 1",
                        "status": {"name": "In Progress", "statusCategory": {"name": "In Progress"}},
                        "issuetype": {"name": "Task"},
                        "priority": {"name": "High"},
                        "assignee": {"displayName": "John Doe"},
                        "reporter": {"displayName": "Jane Smith"},
                        "created": "2025-01-01T10:00:00.000+0000",
                        "updated": "2025-01-02T15:00:00.000+0000",
                        "duedate": "2025-01-15",
                        "labels": ["backend", "urgent"],
                        "components": [{"name": "API"}],
                        "resolution": None,
                        "description": {
                            "type": "doc",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Test description"}],
                                }
                            ],
                        },
                    },
                },
                {
                    "key": "TEST-2",
                    "id": "10002",
                    "fields": {
                        "summary": "Test Issue 2",
                        "status": {"name": "Done", "statusCategory": {"name": "Done"}},
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "Medium"},
                        "assignee": None,
                        "reporter": {"displayName": "Bob Wilson"},
                        "created": "2025-01-03T09:00:00.000+0000",
                        "updated": "2025-01-04T11:00:00.000+0000",
                        "duedate": None,
                        "labels": [],
                        "components": [],
                        "resolution": {"name": "Fixed"},
                        "description": "Plain text description",
                    },
                },
            ],
        }

    async def test_get_auth_data_manual_credentials(self, component):
        """Test getting auth data from manual credentials."""
        auth_data = component._get_auth_data()

        assert auth_data["jira_url"] == "https://test.atlassian.net"
        assert auth_data["email"] == "test@example.com"
        assert auth_data["auth_type"] == "basic"
        assert auth_data["authenticated"] is True
        assert "Authorization" in auth_data["headers"]
        assert auth_data["headers"]["Authorization"].startswith("Basic ")

    async def test_get_auth_data_from_component(self, component):
        """Test getting auth data from connected JiraAuth component."""
        mock_auth_data = Data(
            data={
                "jira_url": "https://connected.atlassian.net",
                "email": "connected@example.com",
                "headers": {"Authorization": "Basic xxx"},
                "auth_type": "basic",
                "authenticated": True,
            }
        )
        component.auth_credentials = mock_auth_data

        auth_data = component._get_auth_data()

        assert auth_data["jira_url"] == "https://connected.atlassian.net"
        assert auth_data["email"] == "connected@example.com"

    async def test_get_auth_data_missing_credentials(self, component):
        """Test error when credentials are missing."""
        component.jira_url = ""
        component.email = ""
        component.email_input = None
        component.api_token = ""
        component.auth_credentials = None

        with pytest.raises(ValueError, match="Missing Jira credentials"):
            component._get_auth_data()

    async def test_get_email_from_input_dict(self, component):
        """Test getting email from component input with dict data."""
        mock_input = Data(data={"email": "db@example.com", "user_id": "123"})
        component.email_input = mock_input

        email = component._get_email_from_input()
        assert email == "db@example.com"

    async def test_get_email_from_input_user_email_field(self, component):
        """Test getting email from component input with user_email field."""
        mock_input = Data(data={"user_email": "user@example.com"})
        component.email_input = mock_input

        email = component._get_email_from_input()
        assert email == "user@example.com"

    async def test_get_email_from_input_string(self, component):
        """Test getting email from component input as string."""
        component.email_input = "string@example.com"

        email = component._get_email_from_input()
        assert email == "string@example.com"

    async def test_get_email_from_input_none(self, component):
        """Test getting email when no input is connected."""
        component.email_input = None

        email = component._get_email_from_input()
        assert email is None

    async def test_get_auth_data_email_from_component(self, component):
        """Test getting auth data with email from connected component."""
        mock_email_input = Data(data={"email": "fromdb@example.com"})
        component.email_input = mock_email_input
        component.email = ""  # Clear manual email

        auth_data = component._get_auth_data()

        assert auth_data["email"] == "fromdb@example.com"
        assert auth_data["authenticated"] is True

    async def test_get_auth_data_email_priority(self, component):
        """Test email priority: component input > manual > env var."""
        # Email from component should take priority over manual
        mock_email_input = Data(data={"email": "priority@example.com"})
        component.email_input = mock_email_input
        component.email = "manual@example.com"

        auth_data = component._get_auth_data()

        assert auth_data["email"] == "priority@example.com"

    async def test_get_project_key_manual(self, component):
        """Test getting project key from manual input."""
        project_key = component._get_project_key()
        assert project_key == "TEST"

    async def test_get_project_key_from_component(self, component):
        """Test getting project key from connected component."""
        mock_input = Data(data={"project_key": "CONNECTED"})
        component.project_key_input = mock_input
        component.project_key = ""

        project_key = component._get_project_key()
        assert project_key == "CONNECTED"

    async def test_get_project_key_missing(self, component):
        """Test error when project key is missing."""
        component.project_key = ""
        component.project_key_input = None

        with pytest.raises(ValueError, match="Project key is required"):
            component._get_project_key()

    async def test_extract_adf_text(self, component):
        """Test extracting plain text from Atlassian Document Format."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "World"},
                    ],
                }
            ],
        }

        result = component._extract_adf_text(adf)
        assert result == "Hello World"

    async def test_extract_adf_text_plain_string(self, component):
        """Test handling plain text string in description."""
        result = component._extract_adf_text("Plain text")
        assert result == "Plain text"

    async def test_extract_adf_text_none(self, component):
        """Test handling None description."""
        result = component._extract_adf_text(None)
        assert result == ""

    async def test_extract_user(self, component):
        """Test extracting user display name."""
        assert component._extract_user({"displayName": "John Doe"}) == "John Doe"
        assert component._extract_user({"name": "johndoe"}) == "johndoe"
        assert component._extract_user(None) == "Unassigned"
        assert component._extract_user("Jane Doe") == "Jane Doe"

    async def test_extract_nested_value(self, component):
        """Test extracting nested values."""
        assert component._extract_nested_value({"name": "Test"}, "name") == "Test"
        assert component._extract_nested_value(None, "name") == ""
        assert component._extract_nested_value("Plain", "name") == "Plain"

    async def test_normalize_ticket_data(self, component, mock_jira_response):
        """Test normalizing ticket data from Jira response."""
        issue = mock_jira_response["issues"][0]
        ticket = component._normalize_ticket_data(issue)

        assert ticket["key"] == "TEST-1"
        assert ticket["summary"] == "Test Issue 1"
        assert ticket["status"] == "In Progress"
        assert ticket["issue_type"] == "Task"
        assert ticket["priority"] == "High"
        assert ticket["assignee"] == "John Doe"
        assert ticket["labels"] == ["backend", "urgent"]
        assert ticket["description"] == "Test description"

    async def test_normalize_ticket_data_unassigned(self, component, mock_jira_response):
        """Test normalizing ticket with no assignee."""
        issue = mock_jira_response["issues"][1]
        ticket = component._normalize_ticket_data(issue)

        assert ticket["assignee"] == "Unassigned"
        assert ticket["resolution"] == "Fixed"

    @patch("requests.post")
    async def test_search_issues(self, mock_post, component, mock_jira_response):
        """Test searching for issues via Jira API."""
        mock_response = Mock()
        mock_response.json.return_value = mock_jira_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        auth_data = component._get_auth_data()
        issues = component._search_issues(auth_data, "project = TEST", 100)

        assert len(issues) == 2
        assert issues[0]["key"] == "TEST-1"
        mock_post.assert_called_once()

    @patch("requests.post")
    async def test_fetch_jira_state_success(self, mock_post, component, mock_jira_response):
        """Test fetching Jira state successfully."""
        mock_response = Mock()
        mock_response.json.return_value = mock_jira_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = component.fetch_jira_state()

        assert isinstance(result, Message)
        data = json.loads(result.text)
        assert data["project"] == "TEST"
        assert data["total_tickets"] == 2
        assert len(data["tickets"]) == 2

    @patch("requests.post")
    async def test_fetch_jira_state_with_jql_filter(self, mock_post, component, mock_jira_response):
        """Test fetching Jira state with additional JQL filter."""
        mock_response = Mock()
        mock_response.json.return_value = mock_jira_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        component.jql_filter = "status != Done"
        result = component.fetch_jira_state()

        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        assert "status != Done" in payload["jql"]

    @patch("requests.post")
    async def test_fetch_jira_state_api_error(self, mock_post, component):
        """Test handling Jira API errors."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response

        result = component.fetch_jira_state()

        assert isinstance(result, Message)
        data = json.loads(result.text)
        assert "error" in data
        assert data["total_tickets"] == 0

    @patch("requests.post")
    async def test_fetch_jira_state_network_error(self, mock_post, component):
        """Test handling network errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        result = component.fetch_jira_state()

        assert isinstance(result, Message)
        data = json.loads(result.text)
        assert "error" in data
        assert "Network error" in data["error"]

    async def test_format_output(self, component, mock_jira_response):
        """Test formatting output for enrichment module."""
        jira_data = {
            "project_key": "TEST",
            "total_tickets": 2,
            "jql_query": "project = TEST",
            "tickets": [
                component._normalize_ticket_data(issue)
                for issue in mock_jira_response["issues"]
            ],
        }

        output = component._format_output(jira_data)

        assert output["project"] == "TEST"
        assert output["total_tickets"] == 2
        assert "fetched_at" in output
        assert len(output["tickets"]) == 2
        assert output["tickets"][0]["key"] == "TEST-1"

    async def test_bearer_auth(self, component):
        """Test bearer token authentication."""
        component.auth_type = "bearer"
        auth_data = component._get_auth_data()

        assert auth_data["headers"]["Authorization"].startswith("Bearer ")
