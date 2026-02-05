"""Tests for the JiraReaderWriterComponent."""

import json
from unittest.mock import Mock, patch

import pytest
from langbuilder.components.cloudgeometry.jira_reader_writer import JiraReaderWriterComponent
from langbuilder.schema import Data
from langbuilder.schema.message import Message

from tests.base import ComponentTestBaseWithoutClient


class TestJiraReaderWriterComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        """Return the component class to test."""
        return JiraReaderWriterComponent

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
            "action": "Search Issues",
            "project_key_input": None,
            "project_key": "TEST",
            "issue_key": "",
            "issue_status": "",
            "assignee_filter": "",
            "jql": "",
            "max_results": 50,
            "summary": "",
            "description": "",
            "issue_type": "Task",
            "priority": "",
            "assignee": "",
            "due_date": "",
            "transition_to": "",
            "comment": "",
            "labels": "",
            "components": "",
            "user_query": "",
            "timeout": 30,
        }

    @pytest.fixture
    def file_names_mapping(self):
        """Return an empty list since this component doesn't have version-specific files."""
        return []

    @pytest.fixture
    async def component(self, component_class, default_kwargs):
        """Return a component instance."""
        return component_class(**default_kwargs)

    async def test_get_auth_data_manual_credentials(self, component):
        """Test getting auth data from manual credentials."""
        auth_data = component._get_auth_data()

        assert auth_data["jira_url"] == "https://test.atlassian.net"
        assert auth_data["email"] == "test@example.com"
        assert auth_data["authenticated"] is True
        assert "Authorization" in auth_data["headers"]

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

    async def test_get_email_from_input(self, component):
        """Test getting email from component input."""
        mock_input = Data(data={"email": "db@example.com"})
        component.email_input = mock_input

        email = component._get_email_from_input()
        assert email == "db@example.com"

    async def test_get_project_key_manual(self, component):
        """Test getting project key from manual input."""
        project_key = component._get_project_key()
        assert project_key == "TEST"

    async def test_get_project_key_override(self, component):
        """Test project key override from tool call."""
        project_key = component._get_project_key("OVERRIDE")
        assert project_key == "OVERRIDE"

    async def test_get_project_key_from_component(self, component):
        """Test getting project key from connected component."""
        mock_input = Data(data={"project_key": "FROMDB"})
        component.project_key_input = mock_input
        component.project_key = ""

        project_key = component._get_project_key()
        assert project_key == "FROMDB"

    async def test_parse_due_date_yyyy_mm_dd(self, component):
        """Test parsing YYYY-MM-DD format."""
        result = component._parse_due_date("2025-03-15")
        assert result == "2025-03-15"

    async def test_parse_due_date_tomorrow(self, component):
        """Test parsing 'tomorrow'."""
        result = component._parse_due_date("tomorrow")
        assert result is not None
        # Should be a valid date string
        assert len(result) == 10
        assert result[4] == "-"

    async def test_parse_due_date_friday(self, component):
        """Test parsing 'friday'."""
        result = component._parse_due_date("friday")
        assert result is not None
        assert len(result) == 10

    async def test_build_adf_content_simple(self, component):
        """Test building ADF content from simple text."""
        result = component._build_adf_content("Hello world")

        assert result["type"] == "doc"
        assert result["version"] == 1
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "paragraph"

    async def test_build_adf_content_multiline(self, component):
        """Test building ADF content with line breaks."""
        result = component._build_adf_content("Line 1\nLine 2")

        assert result["type"] == "doc"
        content = result["content"][0]["content"]
        assert any(item.get("type") == "hardBreak" for item in content)

    @patch("httpx.Client")
    async def test_get_issue_success(self, mock_client_class, component):
        """Test getting an issue successfully."""
        component.action = "Get Issue"
        component.issue_key = "TEST-1"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "TEST-1",
            "fields": {
                "summary": "Test issue",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "John Doe", "accountId": "123"},
                "priority": {"name": "High"},
                "duedate": "2025-03-15",
                "description": None,
                "issuetype": {"name": "Task"},
                "labels": ["backend"],
            },
        }
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["key"] == "TEST-1"
        assert result_data["summary"] == "Test issue"

    @patch("httpx.Client")
    async def test_search_issues_success(self, mock_client_class, component):
        """Test searching issues successfully."""
        component.action = "Search Issues"
        component.project_key = "TEST"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 2,
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Issue 1",
                        "status": {"name": "To Do"},
                        "assignee": None,
                        "priority": None,
                        "duedate": None,
                        "description": None,
                        "issuetype": {"name": "Task"},
                        "labels": [],
                    },
                },
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Issue 2",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Jane", "accountId": "456"},
                        "priority": {"name": "Medium"},
                        "duedate": "2025-03-20",
                        "description": None,
                        "issuetype": {"name": "Bug"},
                        "labels": ["urgent"],
                    },
                },
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["total"] == 2
        assert len(result_data["issues"]) == 2

    @patch("httpx.Client")
    async def test_create_issue_success(self, mock_client_class, component):
        """Test creating an issue successfully."""
        component.action = "Create Issue"
        component.project_key = "TEST"
        component.summary = "New test issue"
        component.issue_type = "Task"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"key": "TEST-10", "id": "10010"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["key"] == "TEST-10"

    @patch("httpx.Client")
    async def test_transition_issue_success(self, mock_client_class, component):
        """Test transitioning an issue successfully."""
        component.action = "Transition Issue"
        component.issue_key = "TEST-1"
        component.transition_to = "In Progress"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        # Mock get transitions
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "transitions": [
                {"id": "21", "name": "In Progress"},
                {"id": "31", "name": "Done"},
            ]
        }
        mock_get_response.raise_for_status = Mock()

        # Mock post transition
        mock_post_response = Mock()
        mock_post_response.status_code = 204
        mock_post_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_get_response
        mock_client.post.return_value = mock_post_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["new_status"] == "In Progress"

    @patch("httpx.Client")
    async def test_add_comment_success(self, mock_client_class, component):
        """Test adding a comment successfully."""
        component.action = "Add Comment"
        component.issue_key = "TEST-1"
        component.comment = "This is a test comment"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "12345"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["comment_id"] == "12345"

    @patch("httpx.Client")
    async def test_search_users_success(self, mock_client_class, component):
        """Test searching users successfully."""
        component.action = "Search Users"
        component.user_query = "John"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "accountId": "123abc",
                "displayName": "John Doe",
                "emailAddress": "john@example.com",
                "active": True,
            },
            {
                "accountId": "456def",
                "displayName": "John Smith",
                "emailAddress": "johns@example.com",
                "active": True,
            },
        ]
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["count"] == 2
        assert len(result_data["users"]) == 2
        assert result_data["users"][0]["display_name"] == "John Doe"

    @patch("httpx.Client")
    async def test_assign_issue_success(self, mock_client_class, component):
        """Test assigning an issue successfully."""
        component.action = "Assign Issue"
        component.issue_key = "TEST-1"
        component.assignee = "John"

        mock_client = Mock()
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        # Mock user search
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = [
            {"accountId": "123abc", "displayName": "John Doe"}
        ]
        mock_search_response.raise_for_status = Mock()

        # Mock assign
        mock_assign_response = Mock()
        mock_assign_response.status_code = 204
        mock_assign_response.raise_for_status = Mock()

        mock_client.get.return_value = mock_search_response
        mock_client.put.return_value = mock_assign_response

        result = component.execute_action()

        assert isinstance(result, Message)
        result_data = json.loads(result.text)
        assert result_data["success"] is True
        assert result_data["assigned_to"] == "John Doe"

    async def test_create_issue_no_project_key(self, component):
        """Test create issue fails without project key."""
        component.action = "Create Issue"
        component.project_key = ""
        component.project_key_input = None
        component.summary = "Test"

        # Need to mock the client to avoid auth issues
        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = Mock(return_value=False)

            result = component.execute_action()

        result_data = json.loads(result.text)
        assert result_data["success"] is False
        assert "Project key is required" in result_data["error"]

    async def test_create_issue_no_summary(self, component):
        """Test create issue fails without summary."""
        component.action = "Create Issue"
        component.project_key = "TEST"
        component.summary = ""

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = Mock(return_value=False)

            result = component.execute_action()

        result_data = json.loads(result.text)
        assert result_data["success"] is False
        assert "Summary is required" in result_data["error"]
