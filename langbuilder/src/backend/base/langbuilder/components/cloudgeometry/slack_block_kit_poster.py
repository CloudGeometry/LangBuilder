"""
Slack Block Kit Poster Component for MeetBot

Posts interactive Block Kit messages with Approve/Edit/Reject buttons
to individual Slack users via DM. Used by the Flow 1 Agent to deliver
action items to each meeting participant.
"""

from __future__ import annotations

import json
import os
import time

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import MessageTextInput, Output, SecretStrInput, StrInput
from langbuilder.schema.data import Data

REQUEST_TIMEOUT = 10
MAX_RATE_LIMIT_WAIT = 60


class SlackBlockKitPosterComponent(LCToolComponent):
    """
    Post Slack Block Kit interactive messages to users via DM.

    Opens a DM channel with the target user and posts a Block Kit message
    containing interactive buttons (Approve / Edit / Reject). Each button
    payload encodes the action type, item ID, and thread timestamp so
    Flow 2 can route the interaction.
    """

    display_name = "Slack Block Kit Poster"
    description = (
        "Post interactive Block Kit messages with buttons to a Slack user's DM. "
        "Used to deliver action items with Approve/Edit/Reject controls."
    )
    icon = "Slack"
    name = "SlackBlockKitPoster"

    inputs = [
        SecretStrInput(
            name="slack_bot_token",
            display_name="Slack Bot Token",
            info="Bot token (xoxb-...). Falls back to SLACK_BOT_TOKEN env var.",
            required=False,
        ),
        StrInput(
            name="user_email",
            display_name="User Email",
            info="Target user's email for DM delivery (used in pipeline mode)",
            required=False,
        ),
        MessageTextInput(
            name="user_message",
            display_name="User Message",
            info="Context message from the agent",
            required=False,
            tool_mode=True,
        ),
    ]

    # ------------------------------------------------------------------ #
    #  Slack helpers
    # ------------------------------------------------------------------ #

    def _get_slack_token(self) -> str:
        if hasattr(self, "slack_bot_token") and self.slack_bot_token:
            return self.slack_bot_token
        token = os.environ.get("SLACK_BOT_TOKEN")
        if token:
            return token
        raise ValueError("No Slack bot token provided and SLACK_BOT_TOKEN not set in environment")

    def _slack_api(self, method: str, endpoint: str, token: str, **kwargs) -> dict:
        """Make an authenticated Slack API call with rate-limit retry."""
        import requests as req

        url = f"https://slack.com/api/{endpoint}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        for attempt in range(2):
            if method == "GET":
                resp = req.get(url, headers=headers, params=kwargs.get("params"), timeout=REQUEST_TIMEOUT)
            else:
                resp = req.post(url, headers=headers, json=kwargs.get("json_data"), timeout=REQUEST_TIMEOUT)

            if resp.status_code == 429:
                retry_after = min(int(resp.headers.get("Retry-After", 5)), MAX_RATE_LIMIT_WAIT)
                self.log(f"Rate limited, retrying in {retry_after}s")
                time.sleep(retry_after)
                continue
            return resp.json()

        return {"ok": False, "error": "rate_limited"}

    def _lookup_user_by_email(self, email: str, token: str) -> str | None:
        data = self._slack_api("GET", "users.lookupByEmail", token, params={"email": email})
        if data.get("ok") and data.get("user", {}).get("id"):
            return data["user"]["id"]
        self.log(f"User lookup failed for {email}: {data.get('error', 'unknown')}")
        return None

    def _open_dm_channel(self, user_id: str, token: str) -> str | None:
        data = self._slack_api("POST", "conversations.open", token, json_data={"users": user_id})
        if data.get("ok") and data.get("channel", {}).get("id"):
            return data["channel"]["id"]
        self.log(f"DM open failed for {user_id}: {data.get('error', 'unknown')}")
        return None

    def _post_blocks(self, channel: str, blocks: list, text: str, token: str) -> dict:
        payload = {
            "channel": channel,
            "blocks": blocks,
            "text": text,
            "unfurl_links": False,
            "unfurl_media": False,
        }
        data = self._slack_api("POST", "chat.postMessage", token, json_data=payload)
        if data.get("ok"):
            return {
                "success": True,
                "message_ts": data.get("ts", ""),
                "channel": data.get("channel", channel),
                "error": None,
            }
        return {
            "success": False,
            "message_ts": None,
            "channel": channel,
            "error": data.get("error", "unknown_error"),
        }

    # ------------------------------------------------------------------ #
    #  run_model — pipeline execution path
    # ------------------------------------------------------------------ #

    def run_model(self) -> Data:
        """Pipeline execution: post blocks from structured_data input."""
        return Data(data={"error": "Use build_tool() for Agent mode or call the tool directly"})

    # ------------------------------------------------------------------ #
    #  build_tool — Agent execution path
    # ------------------------------------------------------------------ #

    def build_tool(self) -> Tool | list[Tool]:
        """Return Agent tools for posting Block Kit messages."""

        class PostActionItemsInput(BaseModel):
            user_email: str = Field(
                description="Email address of the Slack user to DM"
            )
            meeting_title: str = Field(
                description="Title of the meeting (shown in the message header)"
            )
            slack_thread_ts: str = Field(
                description="Thread timestamp for encoding in button payloads"
            )
            items_json: str = Field(
                description=(
                    "JSON array of action items to post. Each item: "
                    "{\"item_id\": \"item-001\", \"title\": \"Fix login\", "
                    "\"description\": \"...\", \"type\": \"jira_create\", "
                    "\"priority\": \"High\", \"jira_project\": \"PROJ\"}"
                )
            )

        def _post_action_items(
            user_email: str,
            meeting_title: str,
            slack_thread_ts: str,
            items_json: str,
        ) -> str:
            try:
                items = json.loads(items_json)
            except json.JSONDecodeError:
                return json.dumps({"success": False, "error": "items_json must be valid JSON array"})

            token = self._get_slack_token()

            # Resolve email → user ID → DM channel
            user_id = self._lookup_user_by_email(user_email, token)
            if not user_id:
                return json.dumps({"success": False, "error": f"Could not find Slack user for {user_email}"})

            channel = self._open_dm_channel(user_id, token)
            if not channel:
                return json.dumps({"success": False, "error": f"Could not open DM with user {user_id}"})

            # Build Block Kit blocks
            blocks = _build_action_item_blocks(meeting_title, slack_thread_ts, items)
            fallback = f"Action items from '{meeting_title}' — {len(items)} item(s)"

            result = self._post_blocks(channel, blocks, fallback, token)
            result["user_email"] = user_email
            result["item_count"] = len(items)
            return json.dumps(result)

        def _build_action_item_blocks(title: str, thread_ts: str, items: list) -> list:
            """Build Block Kit JSON for action items with buttons."""
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"Action items from '{title}'", "emoji": True},
                },
            ]

            for item in items:
                item_id = item.get("item_id", "unknown")
                item_title = item.get("title", "Untitled")
                item_desc = item.get("description", "")
                item_type = item.get("type", "todo")
                priority = item.get("priority", "Medium")
                project = item.get("jira_project", "")

                type_label = {
                    "jira_create": "JIRA Create",
                    "jira_update": "JIRA Update",
                    "confluence_create": "Confluence Create",
                    "confluence_update": "Confluence Update",
                    "todo": "To-Do",
                }.get(item_type, item_type)

                meta_parts = [f"*{type_label}*"]
                if priority:
                    meta_parts.append(f"Priority: {priority}")
                if project:
                    meta_parts.append(f"Project: {project}")
                meta_line = " | ".join(meta_parts)

                desc_preview = (item_desc[:150] + "...") if len(item_desc) > 150 else item_desc

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{item_title}*\n{meta_line}\n{desc_preview}",
                    },
                    "accessory": {
                        "type": "overflow",
                        "action_id": f"item_action_{item_id}",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Approve"},
                                "value": f"approve|{item_id}|{thread_ts}",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Edit"},
                                "value": f"edit|{item_id}|{thread_ts}",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Reject"},
                                "value": f"reject|{item_id}|{thread_ts}",
                            },
                        ],
                    },
                })
                blocks.append({"type": "divider"})

            # Approve All button at the bottom
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve All"},
                        "style": "primary",
                        "action_id": "approve_all",
                        "value": thread_ts,
                    },
                ],
            })

            return blocks

        post_tool = StructuredTool.from_function(
            name="meetbot_post_action_items",
            description=(
                "Post action items to a Slack user's DM as an interactive Block Kit message "
                "with Approve/Edit/Reject buttons for each item. Call once per meeting participant."
            ),
            args_schema=PostActionItemsInput,
            func=_post_action_items,
            return_direct=False,
            tags=["meetbot_post_action_items"],
        )

        # --- Dashboard poster tool ---
        class PostDashboardInput(BaseModel):
            organizer_email: str = Field(
                description="Email of the meeting organizer to receive the dashboard"
            )
            meeting_title: str = Field(
                description="Title of the meeting"
            )
            slack_thread_ts: str = Field(
                description="Thread timestamp for encoding in button payloads"
            )
            items_json: str = Field(
                description=(
                    "JSON array of ALL action items across all participants. "
                    "Each item needs: item_id, title, assignee_email, status, type"
                )
            )

        def _post_dashboard(
            organizer_email: str,
            meeting_title: str,
            slack_thread_ts: str,
            items_json: str,
        ) -> str:
            try:
                items = json.loads(items_json)
            except json.JSONDecodeError:
                return json.dumps({"success": False, "error": "items_json must be valid JSON array"})

            token = self._get_slack_token()

            user_id = self._lookup_user_by_email(organizer_email, token)
            if not user_id:
                return json.dumps({"success": False, "error": f"Could not find Slack user for {organizer_email}"})

            channel = self._open_dm_channel(user_id, token)
            if not channel:
                return json.dumps({"success": False, "error": f"Could not open DM with organizer {user_id}"})

            blocks = _build_dashboard_blocks(meeting_title, slack_thread_ts, items)
            fallback = f"Dashboard: {meeting_title} — {len(items)} item(s)"

            result = self._post_blocks(channel, blocks, fallback, token)
            result["organizer_email"] = organizer_email
            result["item_count"] = len(items)
            return json.dumps(result)

        def _build_dashboard_blocks(title: str, thread_ts: str, items: list) -> list:
            """Build Block Kit JSON for the organizer dashboard."""
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
                title_text = item.get("title", "Untitled")
                status = item.get("status", "pending").replace("_", " ").title()
                ref = item.get("executed_ref", "")
                ref_text = f" -> {ref}" if ref else ""
                lines.append(f":{icon}: *{title_text}* — {assignee} — {status}{ref_text}")

            summary = "\n".join(lines) if lines else "_No items_"

            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{title} — Action Items", "emoji": True},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": summary},
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Force Execute All Pending"},
                            "style": "danger",
                            "action_id": "force_execute_all",
                            "value": thread_ts,
                        },
                    ],
                },
            ]
            return blocks

        dashboard_tool = StructuredTool.from_function(
            name="meetbot_post_dashboard",
            description=(
                "Post the organizer dashboard — a single Slack DM showing the status of all "
                "action items across all participants. Call once per meeting after posting "
                "individual items. Returns the message_ts needed to update the dashboard later."
            ),
            args_schema=PostDashboardInput,
            func=_post_dashboard,
            return_direct=False,
            tags=["meetbot_post_dashboard"],
        )

        self.status = "Slack Block Kit Poster tools created (post items, post dashboard)"
        return [post_tool, dashboard_tool]
