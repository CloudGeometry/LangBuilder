"""
Slack Modal Trigger Component for MeetBot

Opens Slack modals via views.open API. Used in the onboarding flow
(/meetbot setup) and the edit item flow. Must execute within 3 seconds
of a user action or Slack rejects the trigger_id.
"""

from __future__ import annotations

import json
import os

from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data

REQUEST_TIMEOUT = 5  # Tight timeout — trigger_id expires in 3s


class SlackModalTriggerComponent(Component):
    """
    Open a Slack modal via ``views.open``.

    Accepts a ``trigger_id`` from a slash command or button click and a
    view definition JSON. The trigger_id expires in 3 seconds, so this
    component must execute immediately after receiving it.
    """

    display_name = "Slack Modal Trigger"
    description = (
        "Open a Slack modal via views.open. Must execute within 3 seconds "
        "of receiving the trigger_id."
    )
    icon = "Slack"
    name = "SlackModalTrigger"

    inputs = [
        SecretStrInput(
            name="slack_bot_token",
            display_name="Slack Bot Token",
            info="Bot token (xoxb-...). Falls back to SLACK_BOT_TOKEN env var.",
            required=False,
        ),
        StrInput(
            name="trigger_id",
            display_name="Trigger ID",
            info="Trigger ID from Slack slash command or button click (expires in 3s)",
            required=True,
        ),
        StrInput(
            name="view_json",
            display_name="View JSON",
            info="Slack modal view definition as JSON string",
            required=True,
        ),
        StrInput(
            name="private_metadata",
            display_name="Private Metadata",
            info="Optional metadata passed through modal submission (e.g., 'edit|item-001|thread-ts')",
            required=False,
        ),
    ]

    outputs = [
        Output(name="modal_result", display_name="Modal Result", method="open_modal"),
    ]

    def _get_slack_token(self) -> str:
        if hasattr(self, "slack_bot_token") and self.slack_bot_token:
            return self.slack_bot_token
        token = os.environ.get("SLACK_BOT_TOKEN")
        if token:
            return token
        raise ValueError("No Slack bot token provided and SLACK_BOT_TOKEN not set")

    def open_modal(self) -> Data:
        """Open a Slack modal using views.open API."""
        import requests as req

        token = self._get_slack_token()

        # Parse view JSON
        try:
            view = json.loads(self.view_json)
        except json.JSONDecodeError:
            return Data(data={"success": False, "error": "view_json must be valid JSON"})

        # Inject private_metadata if provided
        if self.private_metadata:
            view["private_metadata"] = self.private_metadata

        url = "https://slack.com/api/views.open"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "trigger_id": self.trigger_id,
            "view": view,
        }

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            data = resp.json()
        except req.exceptions.Timeout:
            return Data(data={
                "success": False,
                "error": "Request timed out — trigger_id may have expired (3s limit)",
            })
        except req.exceptions.RequestException as exc:
            return Data(data={"success": False, "error": f"Request failed: {exc}"})

        if data.get("ok"):
            return Data(data={
                "success": True,
                "view_id": data.get("view", {}).get("id", ""),
                "error": None,
            })

        error = data.get("error", "unknown_error")
        detail = ""
        if error == "expired_trigger_id":
            detail = " — The trigger_id expired (3s limit). Ensure this component runs first in the flow."
        return Data(data={
            "success": False,
            "view_id": None,
            "error": f"{error}{detail}",
        })

    @staticmethod
    def onboarding_view_json() -> str:
        """Return the standard MeetBot onboarding modal view JSON."""
        return json.dumps({
            "type": "modal",
            "title": {"type": "plain_text", "text": "MeetBot Setup"},
            "submit": {"type": "plain_text", "text": "Continue"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "atlassian_token",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "token_input",
                        "placeholder": {"type": "plain_text", "text": "Paste your Atlassian API token"},
                    },
                    "label": {"type": "plain_text", "text": "Atlassian API Token"},
                },
                {
                    "type": "input",
                    "block_id": "atlassian_email",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "email_input",
                        "placeholder": {"type": "plain_text", "text": "you@company.com"},
                    },
                    "label": {"type": "plain_text", "text": "Atlassian Email"},
                },
                {
                    "type": "input",
                    "block_id": "jira_project",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "project_input",
                        "placeholder": {"type": "plain_text", "text": "e.g., PROJ"},
                    },
                    "label": {"type": "plain_text", "text": "Default JIRA Project Key"},
                },
            ],
        })

    @staticmethod
    def edit_item_view_json(item: dict) -> str:
        """Return a pre-filled edit modal view JSON for an action item."""
        return json.dumps({
            "type": "modal",
            "title": {"type": "plain_text", "text": "Edit Action Item"},
            "submit": {"type": "plain_text", "text": "Save & Execute"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "title",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "title_input",
                        "initial_value": item.get("title", ""),
                    },
                    "label": {"type": "plain_text", "text": "Title"},
                },
                {
                    "type": "input",
                    "block_id": "description",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "desc_input",
                        "multiline": True,
                        "initial_value": item.get("description", ""),
                    },
                    "label": {"type": "plain_text", "text": "Description"},
                },
                {
                    "type": "input",
                    "block_id": "priority",
                    "element": {
                        "type": "static_select",
                        "action_id": "priority_input",
                        "initial_option": {
                            "text": {"type": "plain_text", "text": item.get("priority", "Medium")},
                            "value": item.get("priority", "Medium"),
                        },
                        "options": [
                            {"text": {"type": "plain_text", "text": p}, "value": p}
                            for p in ["Critical", "High", "Medium", "Low"]
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Priority"},
                },
            ],
        })
