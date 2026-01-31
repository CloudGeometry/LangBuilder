"""
Slack Dashboard Updater Component for MeetBot

Updates an existing Slack message in place via chat.update, used to keep
the organizer dashboard current as participants respond to action items.
"""

from __future__ import annotations

import json
import os
import time

from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data

REQUEST_TIMEOUT = 10
MAX_RATE_LIMIT_WAIT = 60


class SlackDashboardUpdaterComponent(Component):
    """
    Update an existing Slack message in place via ``chat.update``.

    Rebuilds the organizer dashboard Block Kit message to reflect the
    latest item statuses after each approve / edit / reject action.
    """

    display_name = "Slack Dashboard Updater"
    description = (
        "Update an existing Slack message in place (chat.update). "
        "Used to refresh the organizer dashboard as item statuses change."
    )
    icon = "Slack"
    name = "SlackDashboardUpdater"

    inputs = [
        SecretStrInput(
            name="slack_bot_token",
            display_name="Slack Bot Token",
            info="Bot token (xoxb-...). Falls back to SLACK_BOT_TOKEN env var.",
            required=False,
        ),
        StrInput(
            name="channel",
            display_name="Channel",
            info="Slack channel ID where the dashboard message lives",
            required=True,
        ),
        StrInput(
            name="message_ts",
            display_name="Message Timestamp",
            info="Timestamp of the dashboard message to update",
            required=True,
        ),
        StrInput(
            name="meeting_title",
            display_name="Meeting Title",
            info="Title of the meeting for the dashboard header",
            required=True,
        ),
        StrInput(
            name="items_json",
            display_name="Items JSON",
            info="JSON array of all action items with current statuses",
            required=True,
        ),
        StrInput(
            name="slack_thread_ts",
            display_name="Thread Timestamp",
            info="Thread timestamp for Force Execute button payload",
            required=True,
        ),
    ]

    outputs = [
        Output(name="update_result", display_name="Update Result", method="update_dashboard"),
    ]

    def _get_slack_token(self) -> str:
        if hasattr(self, "slack_bot_token") and self.slack_bot_token:
            return self.slack_bot_token
        token = os.environ.get("SLACK_BOT_TOKEN")
        if token:
            return token
        raise ValueError("No Slack bot token provided and SLACK_BOT_TOKEN not set")

    def update_dashboard(self) -> Data:
        """Rebuild and update the organizer dashboard message."""
        import requests as req

        try:
            items = json.loads(self.items_json)
        except json.JSONDecodeError:
            return Data(data={"success": False, "error": "items_json must be valid JSON"})

        token = self._get_slack_token()
        blocks = self._build_dashboard_blocks(self.meeting_title, self.slack_thread_ts, items)
        fallback = f"Dashboard: {self.meeting_title} — {len(items)} item(s)"

        url = "https://slack.com/api/chat.update"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "channel": self.channel,
            "ts": self.message_ts,
            "blocks": blocks,
            "text": fallback,
        }

        for attempt in range(2):
            resp = req.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                retry_after = min(int(resp.headers.get("Retry-After", 5)), MAX_RATE_LIMIT_WAIT)
                time.sleep(retry_after)
                continue
            break

        data = resp.json()
        if data.get("ok"):
            return Data(data={
                "success": True,
                "updated_ts": data.get("ts", ""),
                "channel": data.get("channel", self.channel),
                "error": None,
            })
        return Data(data={
            "success": False,
            "updated_ts": None,
            "channel": self.channel,
            "error": data.get("error", "unknown_error"),
        })

    @staticmethod
    def _build_dashboard_blocks(title: str, thread_ts: str, items: list) -> list:
        status_icons = {
            "pending": "hourglass_flowing_sand",
            "approved": "white_check_mark",
            "executed": "white_check_mark",
            "rejected": "x",
            "timeout_reassigned": "warning",
        }
        lines = []
        for item in items:
            icon = status_icons.get(item.get("status", "pending"), "question")
            assignee = item.get("assignee_email", "unassigned")
            item_title = item.get("title", "Untitled")
            status = item.get("status", "pending").replace("_", " ").title()
            ref = item.get("executed_ref", "")
            ref_text = f" -> {ref}" if ref else ""
            lines.append(f":{icon}: *{item_title}* — {assignee} — {status}{ref_text}")

        summary = "\n".join(lines) if lines else "_No items_"
        return [
            {"type": "header", "text": {"type": "plain_text", "text": f"{title} — Action Items", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
            {"type": "divider"},
            {"type": "actions", "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Force Execute All Pending"},
                "style": "danger",
                "action_id": "force_execute_all",
                "value": thread_ts,
            }]},
        ]
