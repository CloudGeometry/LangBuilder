"""Tests for the JiraWriterTools component."""

import json
from unittest.mock import Mock, patch

import pytest
import requests
from langbuilder.components.cloudgeometry.jira_writer_tools import JiraWriterToolsComponent
from langbuilder.schema import Data

from tests.base import ComponentTestBaseWithoutClient


class TestJiraWriterToolsComponent(ComponentTestBaseWithoutClient):
    @pytest.fixture
    def component_class(self):
        """Return the component class to test."""
        return JiraWriterToolsComponent

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
        """Test project key override from agent tool call."""
        project_key = component._get_project_key("OVERRIDE")
        assert project_key == "OVERRIDE"

    async def test_get_project_key_from_component(self, component):
        """Test getting project key from connected component."""
        mock_input = Data(data={"project_key": "FROMDB"})
        component.project_key_input = mock_input
        component.project_key = ""

        project_key = component._get_project_key()
        assert project_key == "FROMDB"

    async def test_get_project_key_priority(self, component):
        """Test project key priority: override > component > manual."""
        mock_input = Data(data={"project_key": "FROMDB"})
        component.project_key_input = mock_input
        component.project_key = "MANUAL"

        # Override takes priority
        assert component._get_project_key("OVERRIDE") == "OVERRIDE"
        # Component input takes priority over manual when no override
        assert component._get_project_key() == "FROMDB"

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
        # Should have hard breaks for line breaks within paragraph
        content = result["content"][0]["content"]
        assert any(item.get("type") == "hardBreak" for item in content)

    async def test_build_adf_content_paragraphs(self, component):
        """Test building ADF content with multiple paragraphs."""
        result = component._build_adf_content("Paragraph 1\n\nParagraph 2")

        assert result["type"] == "doc"
        assert len(result["content"]) == 2

    @patch("requests.post")
    async def test_create_issue_success(self, mock_post, component):
        """Test creating an issue successfully using default project."""
        mock_response = Mock()
        mock_response.json.return_value = {"key": "TEST-1", "id": "10001"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # No project_key provided - uses default from component
        result = component._create_issue(
            summary="Test issue",
            issue_type="Task",
            description="Test description",
            priority="High",
        )

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["issue_key"] == "TEST-1"
        assert result_data["action"] == "create_issue"

        # Verify default project key was used
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["fields"]["project"]["key"] == "TEST"

    @patch("requests.post")
    async def test_create_issue_with_override_project(self, mock_post, component):
        """Test creating an issue with overridden project key."""
        mock_response = Mock()
        mock_response.json.return_value = {"key": "OTHER-1", "id": "10002"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = component._create_issue(
            summary="Test issue",
            project_key="OTHER",  # Override the default
        )

        result_data = json.loads(result)
        assert result_data["success"] is True

        # Verify overridden project key was used
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["fields"]["project"]["key"] == "OTHER"

    @patch("requests.post")
    async def test_create_issue_with_all_fields(self, mock_post, component):
        """Test creating an issue with all optional fields."""
        mock_response = Mock()
        mock_response.json.return_value = {"key": "TEST-2", "id": "10002"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = component._create_issue(
            summary="Full issue",
            project_key="TEST",
            issue_type="Story",
            description="Detailed description",
            priority="Medium",
            assignee="user@example.com",
            labels="backend,urgent",
            due_date="2025-03-15",
            components="API,Backend",
        )

        result_data = json.loads(result)
        assert result_data["success"] is True

        # Verify the payload
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["fields"]["summary"] == "Full issue"
        assert payload["fields"]["labels"] == ["backend", "urgent"]
        assert payload["fields"]["duedate"] == "2025-03-15"

    @patch("requests.put")
    async def test_update_issue_success(self, mock_put, component):
        """Test updating an issue successfully."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        result = component._update_issue(
            issue_key="TEST-1",
            summary="Updated summary",
            priority="High",
        )

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["issue_key"] == "TEST-1"
        assert "summary" in result_data["fields_updated"]
        assert "priority" in result_data["fields_updated"]

    async def test_update_issue_no_fields(self, component):
        """Test update with no fields returns error."""
        result = component._update_issue(issue_key="TEST-1")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "No fields to update" in result_data["error"]

    @patch("requests.post")
    async def test_add_comment_success(self, mock_post, component):
        """Test adding a comment successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "12345"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = component._add_comment(
            issue_key="TEST-1",
            comment="This is a test comment",
        )

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["action"] == "add_comment"
        assert result_data["comment_id"] == "12345"

    @patch("requests.get")
    @patch("requests.post")
    async def test_transition_issue_success(self, mock_post, mock_get, component):
        """Test transitioning an issue successfully."""
        # Mock get transitions
        mock_get_response = Mock()
        mock_get_response.json.return_value = {
            "transitions": [
                {"id": "21", "name": "In Progress"},
                {"id": "31", "name": "Done"},
            ]
        }
        mock_get_response.raise_for_status = Mock()
        mock_get.return_value = mock_get_response

        # Mock post transition
        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        result = component._transition_issue(
            issue_key="TEST-1",
            transition_name="In Progress",
        )

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["new_status"] == "In Progress"

    @patch("requests.get")
    async def test_transition_issue_invalid_status(self, mock_get, component):
        """Test transitioning to an invalid status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "transitions": [
                {"id": "21", "name": "In Progress"},
                {"id": "31", "name": "Done"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = component._transition_issue(
            issue_key="TEST-1",
            transition_name="Invalid Status",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "not available" in result_data["error"]
        assert "available_transitions" in result_data

    @patch("requests.post")
    async def test_create_issue_api_error(self, mock_post, component):
        """Test handling API errors on create."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response

        result = component._create_issue(
            project_key="TEST",
            summary="Test issue",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    async def test_run_model(self, component):
        """Test run_model returns tool info."""
        result = component.run_model()

        assert isinstance(result, Data)
        assert result.data["status"] == "ready"
        assert "jira_search_users" in result.data["available_tools"]
        assert "jira_create_issue" in result.data["available_tools"]
        assert "jira_update_issue" in result.data["available_tools"]

    async def test_build_tool_returns_tools(self, component):
        """Test build_tool returns list of tools."""
        tools = component.build_tool()

        assert isinstance(tools, list)
        assert len(tools) == 5

        tool_names = [t.name for t in tools]
        assert "jira_search_users" in tool_names
        assert "jira_create_issue" in tool_names
        assert "jira_update_issue" in tool_names
        assert "jira_add_comment" in tool_names
        assert "jira_transition_issue" in tool_names

    @patch("requests.get")
    async def test_search_users_success(self, mock_get, component):
        """Test searching for users successfully."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "accountId": "5b10ac8d82e05b22cc7d4ef5",
                "displayName": "Joaquin Garcia",
                "emailAddress": "joaquin@example.com",
                "active": True,
            },
            {
                "accountId": "6c21bd9e93f16c33dd8e5fg6",
                "displayName": "Joaquin Rodriguez",
                "emailAddress": "joaquin.r@example.com",
                "active": True,
            },
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = component._search_users(query="Joaquin")

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["action"] == "search_users"
        assert result_data["count"] == 2
        assert len(result_data["users"]) == 2
        assert result_data["users"][0]["account_id"] == "5b10ac8d82e05b22cc7d4ef5"
        assert result_data["users"][0]["display_name"] == "Joaquin Garcia"

    @patch("requests.get")
    async def test_search_users_with_project_key(self, mock_get, component):
        """Test searching for users with project key filter."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "accountId": "5b10ac8d82e05b22cc7d4ef5",
                "displayName": "Joaquin Garcia",
                "active": True,
            },
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = component._search_users(query="Joaquin", project_key="LAN")

        result_data = json.loads(result)
        assert result_data["success"] is True

        # Verify the correct endpoint was called
        call_args = mock_get.call_args
        assert "/user/assignable/search" in call_args[0][0]
        assert call_args[1]["params"]["project"] == "LAN"

    @patch("requests.get")
    async def test_search_users_no_results(self, mock_get, component):
        """Test searching for users with no matches."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = component._search_users(query="NonexistentUser")

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["count"] == 0
        assert result_data["users"] == []
