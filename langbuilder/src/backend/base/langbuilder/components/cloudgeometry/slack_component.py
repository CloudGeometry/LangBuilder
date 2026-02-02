"""
Unified Slack Component

Single drag-and-drop node for all common Slack operations: send, update,
delete, read, search messages; manage reactions, users, channels; upload files.
Select an operation from the dropdown; inputs are labelled with [Operation]
prefixes so users know which fields apply to their selection.

In Agent mode, ``_get_tools()`` returns 12 focused StructuredTools so LLMs
pick the right action without navigating a monolithic interface.

The existing ``SlackNotifyComponent`` is untouched for backward compatibility.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import (
    BoolInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    MultilineInput,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.data import Data

from langbuilder.components.cloudgeometry.slack_base import (
    MAX_MESSAGE_LENGTH,
    SlackBaseMixin,
)

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Operations enum (matches dropdown values)
# ---------------------------------------------------------------------------
OP_SEND = "Send Message"
OP_UPDATE = "Update Message"
OP_DELETE = "Delete Message"
OP_READ = "Read Messages"
OP_SEARCH = "Search Messages"
OP_GET_USER = "Get User"
OP_LIST_CHANNELS = "List Channels"
OP_REACT = "React"
OP_UPLOAD = "Upload File"
OP_OPEN_MODAL = "Open Modal"
OP_UPDATE_MODAL = "Update Modal"
OP_PUSH_MODAL = "Push Modal"

ALL_OPERATIONS = [
    OP_SEND, OP_UPDATE, OP_DELETE, OP_READ, OP_SEARCH,
    OP_GET_USER, OP_LIST_CHANNELS, OP_REACT, OP_UPLOAD,
    OP_OPEN_MODAL, OP_UPDATE_MODAL, OP_PUSH_MODAL,
]


class SlackComponent(SlackBaseMixin, LCToolComponent):
    """Send, read, update, and search Slack messages.

    Manage reactions, users, channels, and file uploads.
    Configure inputs below based on your selected operation.
    """

    display_name = "Slack"
    description = (
        "Send, read, update, and search Slack messages. "
        "Manage reactions, users, channels, and file uploads. "
        "Select an operation and configure the relevant inputs."
    )
    icon = "Slack"
    name = "SlackComponent"

    # ------------------------------------------------------------------
    # Inputs -- ordered by frequency of use
    # Shared inputs first, then high-frequency, then advanced.
    # Bracket prefixes indicate which operation(s) use each input.
    # ------------------------------------------------------------------
    inputs = [
        # --- Shared / configuration inputs ---
        DropdownInput(
            name="operation",
            display_name="Operation",
            info="Select the Slack operation to perform.",
            options=ALL_OPERATIONS,
            value=OP_SEND,
            required=True,
            tool_mode=False,  # set at configuration time, not by Agent
        ),
        SecretStrInput(
            name="slack_bot_token",
            display_name="Slack Bot Token",
            info="Bot token (xoxb-...). Leave empty to use SLACK_BOT_TOKEN env var.",
            required=False,
        ),
        MessageTextInput(
            name="channel",
            display_name="Channel",
            info=(
                "Channel ID (C...), channel name (#general), "
                "user ID (U...) for DM, or email address for DM."
            ),
            required=False,
            tool_mode=True,
        ),
        # --- High-frequency operation inputs ---
        MessageTextInput(
            name="text",
            display_name="Text",
            info="[Send, Update] Message text. Also used as Block Kit fallback for notifications.",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="message_ts",
            display_name="Message Timestamp",
            info="[Update, Delete, React, Read thread] Timestamp of the message to target.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="blocks_json",
            display_name="Blocks JSON",
            info="[Send, Update] Raw Block Kit JSON array. Design at https://app.slack.com/block-kit-builder",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="thread_ts",
            display_name="Thread Timestamp",
            info="[Send, Read, Upload] Post as a threaded reply or read a specific thread.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="query",
            display_name="Search Query",
            info="[Search] Search query. Supports Slack modifiers: in:#channel from:@user before:date",
            required=False,
            tool_mode=True,
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            info="[Read, List, Search] Number of results to return.",
            required=False,
            value=20,
            tool_mode=True,
        ),
        # --- Medium-frequency inputs ---
        MessageTextInput(
            name="target_user_id",
            display_name="User ID",
            info="[Get User] Slack user ID (U...) to look up.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="email",
            display_name="Email",
            info="[Get User] Email address for user lookup.",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="emoji",
            display_name="Emoji",
            info="[React] Emoji name, e.g. thumbsup or :thumbsup: (colons stripped automatically).",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="filename",
            display_name="Filename",
            info="[Upload] Name for the uploaded file (e.g. report.txt).",
            required=False,
            tool_mode=True,
        ),
        MultilineInput(
            name="file_content",
            display_name="File Content",
            info="[Upload] Text or code content to upload as a file.",
            required=False,
            tool_mode=True,
        ),
        # --- Modal inputs ---
        MessageTextInput(
            name="trigger_id",
            display_name="Trigger ID",
            info="[Open Modal, Push Modal] Trigger ID from a Slack slash command or interactive payload. Expires in 3 seconds.",
            required=False,
            tool_mode=True,
        ),
        MultilineInput(
            name="view_json",
            display_name="View JSON",
            info="[Open Modal, Update Modal, Push Modal] Modal view definition as a JSON object. Design at https://app.slack.com/block-kit-builder",
            required=False,
            tool_mode=True,
        ),
        MessageTextInput(
            name="view_id",
            display_name="View ID",
            info="[Update Modal] The ID of the modal view to update (returned by views.open).",
            required=False,
            tool_mode=True,
        ),
        StrInput(
            name="view_hash",
            display_name="View Hash",
            info="[Update Modal] Hash of the current view for optimistic locking (optional).",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        # --- Advanced inputs ---
        BoolInput(
            name="reply_broadcast",
            display_name="Reply Broadcast",
            info="[Send] Also post threaded reply to the channel.",
            required=False,
            value=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="ephemeral_user",
            display_name="Ephemeral User",
            info="[Send] User ID to show an ephemeral (only-visible-to-them) message.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        BoolInput(
            name="unfurl_links",
            display_name="Unfurl Links",
            info="[Send] Enable link previews.",
            required=False,
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="unfurl_media",
            display_name="Unfurl Media",
            info="[Send] Enable media previews.",
            required=False,
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="reaction_action",
            display_name="Reaction Action",
            info="[React] Whether to add, remove, or get reactions.",
            options=["add", "remove", "get"],
            value="add",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="channel_types",
            display_name="Channel Types",
            info="[List Channels] Comma-separated: public_channel, private_channel, mpim, im",
            required=False,
            value="public_channel",
            tool_mode=True,
            advanced=True,
        ),
        BoolInput(
            name="exclude_archived",
            display_name="Exclude Archived",
            info="[List Channels] Hide archived channels.",
            required=False,
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="list_all",
            display_name="List All Users",
            info="[Get User] Return all workspace users instead of looking up one.",
            required=False,
            value=False,
            tool_mode=True,
            advanced=True,
        ),
        SecretStrInput(
            name="slack_user_token",
            display_name="Slack User Token",
            info=(
                "[Search] User token (xoxp-...) required for search. "
                "Find in your Slack app's OAuth settings under 'User OAuth Token'."
            ),
            required=False,
            advanced=True,
        ),
        DropdownInput(
            name="sort",
            display_name="Sort",
            info="[Search] Sort search results by relevance or time.",
            options=["score", "timestamp"],
            value="score",
            required=False,
            advanced=True,
        ),
        DropdownInput(
            name="sort_dir",
            display_name="Sort Direction",
            info="[Search] Sort direction.",
            options=["desc", "asc"],
            value="desc",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="oldest",
            display_name="Oldest",
            info="[Read] Unix timestamp -- only messages after this time.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="latest",
            display_name="Latest",
            info="[Read] Unix timestamp -- only messages before this time.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="file_path",
            display_name="File Path",
            info="[Upload] Local file path (alternative to content). Server-side only -- not available in Agent mode.",
            required=False,
            tool_mode=False,  # Security: Agents cannot read arbitrary paths
            advanced=True,
        ),
        StrInput(
            name="initial_comment",
            display_name="Initial Comment",
            info="[Upload] Message posted alongside the uploaded file.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="title",
            display_name="File Title",
            info="[Upload] Display title for the file in Slack.",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
    ]

    # Uses default LCToolComponent outputs: [api_run_model, api_build_tool]

    # ==================================================================
    # run_model -- canvas dispatcher
    # ==================================================================
    def run_model(self) -> Data:
        """Dispatch to the appropriate operation based on the dropdown selection."""
        try:
            token = self._get_slack_token()
        except ValueError as exc:
            self.status = f"Error: {exc}"
            return Data(data={
                "success": False,
                "error": str(exc),
                "error_code": "invalid_auth",
            })

        operation = getattr(self, "operation", OP_SEND)
        channel = self._resolve_channel_input(token)

        dispatch = {
            OP_SEND: lambda: self._run_send_message(
                channel=channel,
                text=getattr(self, "text", ""),
                blocks_json=getattr(self, "blocks_json", ""),
                thread_ts=getattr(self, "thread_ts", ""),
                reply_broadcast=getattr(self, "reply_broadcast", False),
                ephemeral_user=getattr(self, "ephemeral_user", ""),
                unfurl_links=getattr(self, "unfurl_links", False),
                unfurl_media=getattr(self, "unfurl_media", False),
                token=token,
            ),
            OP_UPDATE: lambda: self._run_update_message(
                channel=channel,
                message_ts=getattr(self, "message_ts", ""),
                text=getattr(self, "text", ""),
                blocks_json=getattr(self, "blocks_json", ""),
                token=token,
            ),
            OP_DELETE: lambda: self._run_delete_message(
                channel=channel,
                message_ts=getattr(self, "message_ts", ""),
                token=token,
            ),
            OP_READ: lambda: self._run_read_messages(
                channel=channel,
                limit=getattr(self, "limit", 20),
                thread_ts=getattr(self, "thread_ts", ""),
                oldest=getattr(self, "oldest", ""),
                latest=getattr(self, "latest", ""),
                token=token,
            ),
            OP_SEARCH: lambda: self._run_search_messages(
                query=getattr(self, "query", ""),
                sort=getattr(self, "sort", "score"),
                sort_dir=getattr(self, "sort_dir", "desc"),
                count=getattr(self, "limit", 20),
                token=token,
            ),
            OP_GET_USER: lambda: self._run_get_user(
                user_id=getattr(self, "target_user_id", ""),
                email=getattr(self, "email", ""),
                list_all=getattr(self, "list_all", False),
                limit=getattr(self, "limit", 20),
                token=token,
            ),
            OP_LIST_CHANNELS: lambda: self._run_list_channels(
                channel=channel,
                channel_types=getattr(self, "channel_types", "public_channel"),
                exclude_archived=getattr(self, "exclude_archived", True),
                limit=getattr(self, "limit", 20),
                token=token,
            ),
            OP_REACT: lambda: self._run_add_reaction(
                channel=channel,
                message_ts=getattr(self, "message_ts", ""),
                reaction_action=getattr(self, "reaction_action", "add"),
                emoji=getattr(self, "emoji", ""),
                token=token,
            ),
            OP_UPLOAD: lambda: self._run_upload_file(
                channel=channel,
                filename=getattr(self, "filename", ""),
                file_content=getattr(self, "file_content", ""),
                file_path=getattr(self, "file_path", ""),
                initial_comment=getattr(self, "initial_comment", ""),
                title=getattr(self, "title", ""),
                thread_ts=getattr(self, "thread_ts", ""),
                token=token,
            ),
            OP_OPEN_MODAL: lambda: self._run_open_modal(
                trigger_id=getattr(self, "trigger_id", ""),
                view_json=getattr(self, "view_json", ""),
                token=token,
            ),
            OP_UPDATE_MODAL: lambda: self._run_update_modal(
                view_id=getattr(self, "view_id", ""),
                view_json=getattr(self, "view_json", ""),
                view_hash=getattr(self, "view_hash", ""),
                token=token,
            ),
            OP_PUSH_MODAL: lambda: self._run_push_modal(
                trigger_id=getattr(self, "trigger_id", ""),
                view_json=getattr(self, "view_json", ""),
                token=token,
            ),
        }

        handler = dispatch.get(operation)
        if handler is None:
            return Data(data={
                "success": False,
                "error": f"Unknown operation: {operation}",
                "error_code": "invalid_input",
            })

        return handler()

    # ==================================================================
    # Channel resolution
    # ==================================================================
    def _resolve_channel_input(self, token: str) -> str:
        """Read the channel input and resolve names to IDs."""
        raw = getattr(self, "channel", "") or ""
        raw = raw.strip()
        if not raw:
            return ""
        return self._resolve_channel(raw, token)

    def _resolve_channel(self, channel: str, token: str) -> str:
        """Resolve a channel name (e.g. ``#general``) to a channel ID.

        If the value already looks like a channel ID (starts with C, D, G)
        it is returned as-is.  Otherwise we call ``conversations.list`` and
        match by ``name``.
        """
        if not channel:
            return ""

        # Already a channel ID
        if channel[0] in ("C", "D", "G"):
            return channel

        # Strip leading # if present
        name = channel.lstrip("#").lower()

        # Paginate through conversations.list to find a match
        cursor = None
        for _ in range(10):  # safety cap on pages
            params: dict = {"types": "public_channel,private_channel", "limit": 200}
            if cursor:
                params["cursor"] = cursor

            result = self._slack_api("GET", "conversations.list", token, params=params)
            if not result["ok"]:
                # Can't resolve -- return original and let Slack error
                self._slack_log(
                    "warning", "resolve_channel",
                    f"Could not list channels to resolve '{channel}': {result.get('error')}",
                )
                return channel

            channels = result["data"].get("channels", [])
            for ch in channels:
                if ch.get("name", "").lower() == name:
                    return ch["id"]

            # Check pagination
            meta = result["data"].get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break

        # Not found -- return original, Slack API will return channel_not_found
        self._slack_log(
            "warning", "resolve_channel",
            f"Channel name '{channel}' not found. Passing as-is to Slack API.",
        )
        return channel

    # ==================================================================
    # DM resolution helpers
    # ==================================================================
    def _open_dm_channel(self, user_id: str, token: str) -> dict:
        """Open (or find) a DM channel with a user.

        Returns the ``_slack_api`` result dict.  On success,
        ``result["data"]["channel"]["id"]`` contains the DM channel ID.
        """
        return self._slack_api(
            "POST", "conversations.open", token,
            json={"users": user_id},
        )

    def _resolve_dm_target(self, channel: str, token: str) -> tuple[str, str | None]:
        """If *channel* is a user ID or email, open a DM and return the DM channel ID.

        Returns:
            (resolved_channel, error_message_or_None)
        """
        if not channel:
            return channel, None

        # User ID (U... or W...)
        if channel[0] in ("U", "W") and "@" not in channel:
            dm = self._open_dm_channel(channel, token)
            if dm["ok"]:
                return dm["data"]["channel"]["id"], None
            return "", f"Could not open DM with user {channel}: {dm['error']}"

        # Email
        if "@" in channel and not channel.startswith("C"):
            # Resolve email -> user ID first
            lookup = self._slack_api(
                "GET", "users.lookupByEmail", token,
                params={"email": channel},
            )
            if not lookup["ok"]:
                return "", f"Could not resolve email {channel}: {lookup['error']}"
            uid = lookup["data"]["user"]["id"]
            dm = self._open_dm_channel(uid, token)
            if dm["ok"]:
                return dm["data"]["channel"]["id"], None
            return "", f"Could not open DM with {channel}: {dm['error']}"

        # Not a DM target
        return channel, None

    # ==================================================================
    # Text helpers (adapted from slack_notify.py)
    # ==================================================================
    @staticmethod
    def _escape_message(text: str) -> str:
        """Escape ``&``, ``<``, ``>`` while preserving valid Slack syntax."""
        preserved = []
        pattern = r"<[@#!][^>]+>|<https?://[^>]+>"
        for match in re.finditer(pattern, text):
            preserved.append((match.start(), match.end(), match.group()))

        result = []
        i = 0
        pidx = 0
        while i < len(text):
            if pidx < len(preserved):
                start, end, txt = preserved[pidx]
                if i == start:
                    result.append(txt)
                    i = end
                    pidx += 1
                    continue
            ch = text[i]
            if ch == "&":
                result.append("&amp;")
            elif ch == "<":
                result.append("&lt;")
            elif ch == ">":
                result.append("&gt;")
            else:
                result.append(ch)
            i += 1
        return "".join(result)

    @staticmethod
    def _truncate_message(text: str) -> str:
        """Truncate to ``MAX_MESSAGE_LENGTH`` with ``[truncated]`` suffix."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return text
        suffix = " [truncated]"
        return text[: MAX_MESSAGE_LENGTH - len(suffix)] + suffix

    @staticmethod
    def _validate_blocks_json(blocks_json: str) -> tuple[list | None, str | None]:
        """Parse and validate Block Kit JSON.

        Returns:
            (parsed_blocks_list, error_message)
        """
        if not blocks_json or not blocks_json.strip():
            return None, None
        try:
            parsed = json.loads(blocks_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return None, f"Invalid Block Kit JSON: {exc}"
        if not isinstance(parsed, list):
            return None, "Block Kit JSON must be a JSON array (list), not a single object."
        return parsed, None

    # ==================================================================
    # Operation implementations
    # ==================================================================

    # ---- Send Message (Task 4 + Task 13 DM) ----
    def _run_send_message(
        self,
        channel: str,
        text: str = "",
        blocks_json: str = "",
        thread_ts: str = "",
        reply_broadcast: bool = False,
        ephemeral_user: str = "",
        unfurl_links: bool = False,
        unfurl_media: bool = False,
        token: str = "",
    ) -> Data:
        if not channel:
            return Data(data={"success": False, "error": "Channel is required.", "error_code": "invalid_input"})

        # DM resolution (user ID or email in channel field)
        channel, dm_err = self._resolve_dm_target(channel, token)
        if dm_err:
            self.status = f"Error: {dm_err}"
            return Data(data={"success": False, "error": dm_err, "error_code": "dm_open_failed"})

        # Validate blocks
        blocks, blocks_err = self._validate_blocks_json(blocks_json)
        if blocks_err:
            self.status = f"Error: {blocks_err}"
            return Data(data={"success": False, "error": blocks_err, "error_code": "invalid_input"})

        # Require text or blocks
        if not text and not blocks:
            return Data(data={
                "success": False,
                "error": "Either text or blocks_json is required.",
                "error_code": "invalid_input",
            })

        # Process text
        if text and not blocks:
            text = self._escape_message(text)
        text = self._truncate_message(text) if text else ""

        # Default fallback text when only blocks are provided
        if blocks and not text:
            text = "Message with rich content"

        # Build payload
        payload: dict = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
            "unfurl_media": unfurl_media,
        }
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts
            if reply_broadcast:
                payload["reply_broadcast"] = True

        # Ephemeral vs normal
        if ephemeral_user:
            payload["user"] = ephemeral_user
            endpoint = "chat.postEphemeral"
        else:
            endpoint = "chat.postMessage"

        self.status = f"Posting to {channel}..."
        result = self._slack_api("POST", endpoint, token, json=payload)

        if result["ok"]:
            data = result["data"]
            self.status = "Message posted successfully"
            return Data(data={
                "success": True,
                "message_ts": data.get("ts"),
                "channel": data.get("channel", channel),
                "thread_ts": data.get("ts") if thread_ts else None,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "message_ts": None,
            "channel": channel,
            "thread_ts": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Update Message (Task 5) ----
    def _run_update_message(
        self,
        channel: str,
        message_ts: str = "",
        text: str = "",
        blocks_json: str = "",
        token: str = "",
    ) -> Data:
        if not channel or not message_ts:
            return Data(data={
                "success": False,
                "error": "Both channel and message_ts are required for Update.",
                "error_code": "invalid_input",
            })

        blocks, blocks_err = self._validate_blocks_json(blocks_json)
        if blocks_err:
            self.status = f"Error: {blocks_err}"
            return Data(data={"success": False, "error": blocks_err, "error_code": "invalid_input"})

        if not text and not blocks:
            return Data(data={
                "success": False,
                "error": "At least one of text or blocks_json is required for Update.",
                "error_code": "invalid_input",
            })

        payload: dict = {"channel": channel, "ts": message_ts}
        if text:
            payload["text"] = text
        if blocks:
            payload["blocks"] = blocks
            if not text:
                payload["text"] = "Message with rich content"

        self.status = f"Updating message in {channel}..."
        result = self._slack_api("POST", "chat.update", token, json=payload)

        if result["ok"]:
            self.status = "Message updated successfully"
            return Data(data={
                "success": True,
                "message_ts": result["data"].get("ts", message_ts),
                "channel": result["data"].get("channel", channel),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "message_ts": message_ts,
            "channel": channel,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Delete Message (Task 6) ----
    def _run_delete_message(
        self,
        channel: str,
        message_ts: str = "",
        token: str = "",
    ) -> Data:
        if not channel or not message_ts:
            return Data(data={
                "success": False,
                "error": "Both channel and message_ts are required for Delete.",
                "error_code": "invalid_input",
            })

        self.status = f"Deleting message in {channel}..."
        result = self._slack_api(
            "POST", "chat.delete", token,
            json={"channel": channel, "ts": message_ts},
        )

        if result["ok"]:
            self.status = "Message deleted successfully"
            return Data(data={
                "success": True,
                "channel": channel,
                "message_ts": message_ts,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "channel": channel,
            "message_ts": message_ts,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Read Messages (Task 7) ----
    def _run_read_messages(
        self,
        channel: str,
        limit: int = 20,
        thread_ts: str = "",
        oldest: str = "",
        latest: str = "",
        token: str = "",
    ) -> Data:
        if not channel:
            return Data(data={
                "success": False,
                "error": "Channel is required for Read.",
                "error_code": "invalid_input",
            })

        limit = min(max(1, limit), 200)

        if thread_ts:
            endpoint = "conversations.replies"
            params: dict = {"channel": channel, "ts": thread_ts, "limit": limit}
        else:
            endpoint = "conversations.history"
            params = {"channel": channel, "limit": limit}

        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest

        self.status = f"Reading messages from {channel}..."
        result = self._slack_api("GET", endpoint, token, params=params)

        if result["ok"]:
            raw_messages = result["data"].get("messages", [])
            messages = [
                {
                    "text": m.get("text", ""),
                    "user": m.get("user", ""),
                    "ts": m.get("ts", ""),
                    "thread_ts": m.get("thread_ts"),
                    "reply_count": m.get("reply_count"),
                    "reactions": m.get("reactions"),
                    "blocks": m.get("blocks"),
                }
                for m in raw_messages
            ]
            meta = result["data"].get("response_metadata", {})
            has_more = result["data"].get("has_more", False)
            self.status = f"Read {len(messages)} messages"
            return Data(data={
                "success": True,
                "messages": messages,
                "has_more": has_more,
                "next_cursor": meta.get("next_cursor"),
                "channel": channel,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "messages": [],
            "has_more": False,
            "next_cursor": None,
            "channel": channel,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Get User (Task 8) ----
    def _run_get_user(
        self,
        user_id: str = "",
        email: str = "",
        list_all: bool = False,
        limit: int = 20,
        token: str = "",
    ) -> Data:
        if user_id:
            return self._get_user_by_id(user_id, token)
        if email:
            return self._get_user_by_email(email, token)
        if list_all:
            return self._list_users(limit, token)

        return Data(data={
            "success": False,
            "error": "Provide user_id, email, or set list_all=True.",
            "error_code": "invalid_input",
        })

    def _get_user_by_id(self, user_id: str, token: str) -> Data:
        self.status = f"Looking up user {user_id}..."
        result = self._slack_api("GET", "users.info", token, params={"user": user_id})
        if result["ok"]:
            user = self._normalize_user(result["data"].get("user", {}))
            self.status = f"Found user: {user.get('real_name', user_id)}"
            return Data(data={"success": True, "user": user, "users": None, "error": None, "error_code": None})

        self.status = f"Error: {result['error_code']}"
        return Data(data={"success": False, "user": None, "users": None, "error": result["error"], "error_code": result["error_code"]})

    def _get_user_by_email(self, email: str, token: str) -> Data:
        self.status = f"Looking up user by email..."
        result = self._slack_api("GET", "users.lookupByEmail", token, params={"email": email})
        if result["ok"]:
            user = self._normalize_user(result["data"].get("user", {}))
            self.status = f"Found user: {user.get('real_name', email)}"
            return Data(data={"success": True, "user": user, "users": None, "error": None, "error_code": None})

        self.status = f"Error: {result['error_code']}"
        return Data(data={"success": False, "user": None, "users": None, "error": result["error"], "error_code": result["error_code"]})

    def _list_users(self, limit: int, token: str) -> Data:
        self.status = "Listing workspace users..."
        result = self._slack_api("GET", "users.list", token, params={"limit": min(limit, 200)})
        if result["ok"]:
            raw = result["data"].get("members", [])
            users = [self._normalize_user(u) for u in raw]
            meta = result["data"].get("response_metadata", {})
            self.status = f"Found {len(users)} users"
            return Data(data={
                "success": True,
                "user": None,
                "users": users,
                "has_more": bool(meta.get("next_cursor")),
                "next_cursor": meta.get("next_cursor"),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={"success": False, "user": None, "users": None, "error": result["error"], "error_code": result["error_code"]})

    @staticmethod
    def _normalize_user(raw: dict) -> dict:
        """Flatten Slack's nested user object."""
        profile = raw.get("profile", {})
        return {
            "id": raw.get("id", ""),
            "name": raw.get("name", ""),
            "real_name": raw.get("real_name", profile.get("real_name", "")),
            "display_name": profile.get("display_name", ""),
            "email": profile.get("email", ""),
            "status_text": profile.get("status_text", ""),
            "status_emoji": profile.get("status_emoji", ""),
            "is_bot": raw.get("is_bot", False),
            "is_admin": raw.get("is_admin", False),
            "team_id": raw.get("team_id", ""),
        }

    # ---- List Channels (Task 9) ----
    def _run_list_channels(
        self,
        channel: str = "",
        channel_types: str = "public_channel",
        exclude_archived: bool = True,
        limit: int = 20,
        token: str = "",
    ) -> Data:
        # If a specific channel is provided, get info for it
        if channel:
            self.status = f"Getting info for channel {channel}..."
            result = self._slack_api("GET", "conversations.info", token, params={"channel": channel})
            if result["ok"]:
                ch = self._normalize_channel(result["data"].get("channel", {}))
                self.status = f"Channel: {ch.get('name', channel)}"
                return Data(data={
                    "success": True,
                    "channel": ch,
                    "channels": None,
                    "has_more": False,
                    "next_cursor": None,
                    "error": None,
                    "error_code": None,
                })
            self.status = f"Error: {result['error_code']}"
            return Data(data={"success": False, "channel": None, "channels": None, "error": result["error"], "error_code": result["error_code"]})

        # List channels
        self.status = "Listing channels..."
        params: dict = {
            "types": channel_types,
            "exclude_archived": exclude_archived,
            "limit": min(limit, 200),
        }
        result = self._slack_api("GET", "conversations.list", token, params=params)

        if result["ok"]:
            raw = result["data"].get("channels", [])
            channels = [self._normalize_channel(c) for c in raw]
            meta = result["data"].get("response_metadata", {})
            self.status = f"Found {len(channels)} channels"
            return Data(data={
                "success": True,
                "channel": None,
                "channels": channels,
                "has_more": bool(meta.get("next_cursor")),
                "next_cursor": meta.get("next_cursor"),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={"success": False, "channel": None, "channels": None, "error": result["error"], "error_code": result["error_code"]})

    @staticmethod
    def _normalize_channel(raw: dict) -> dict:
        """Flatten Slack's channel object."""
        topic = raw.get("topic", {})
        purpose = raw.get("purpose", {})
        return {
            "id": raw.get("id", ""),
            "name": raw.get("name", ""),
            "topic": topic.get("value", "") if isinstance(topic, dict) else "",
            "purpose": purpose.get("value", "") if isinstance(purpose, dict) else "",
            "num_members": raw.get("num_members", 0),
            "is_private": raw.get("is_private", False),
            "is_archived": raw.get("is_archived", False),
            "is_member": raw.get("is_member", False),
        }

    # ---- Search Messages (Task 10) ----
    def _run_search_messages(
        self,
        query: str = "",
        sort: str = "score",
        sort_dir: str = "desc",
        count: int = 20,
        token: str = "",
    ) -> Data:
        if not query:
            return Data(data={
                "success": False,
                "error": "Search query is required.",
                "error_code": "invalid_input",
            })

        # Prefer user token for search
        search_token = getattr(self, "slack_user_token", None)
        if search_token:
            search_token = str(search_token)
        else:
            search_token = token

        # Validate token type
        if search_token.startswith("xoxb-"):
            return Data(data={
                "success": False,
                "error": (
                    "Search Messages requires a user token (xoxp-...), not a bot token. "
                    "Configure the 'Slack User Token' input with your user OAuth token."
                ),
                "error_code": "invalid_auth",
            })

        count = min(max(1, count), 100)

        self.status = f"Searching: {query[:50]}..."
        result = self._slack_api(
            "GET", "search.messages", search_token,
            params={"query": query, "sort": sort, "sort_dir": sort_dir, "count": count},
        )

        if result["ok"]:
            messages_data = result["data"].get("messages", {})
            matches = messages_data.get("matches", [])
            total = messages_data.get("total", 0)
            paging = messages_data.get("paging", {})
            has_more = paging.get("pages", 1) > paging.get("page", 1)

            messages = [
                {
                    "text": m.get("text", ""),
                    "user": m.get("user", m.get("username", "")),
                    "ts": m.get("ts", ""),
                    "channel": {"id": m.get("channel", {}).get("id", ""), "name": m.get("channel", {}).get("name", "")},
                    "permalink": m.get("permalink", ""),
                }
                for m in matches
            ]
            self.status = f"Found {total} results"
            return Data(data={
                "success": True,
                "messages": messages,
                "total": total,
                "has_more": has_more,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "messages": [],
            "total": 0,
            "has_more": False,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- React (Task 11) ----
    def _run_add_reaction(
        self,
        channel: str = "",
        message_ts: str = "",
        reaction_action: str = "add",
        emoji: str = "",
        token: str = "",
    ) -> Data:
        if not channel or not message_ts:
            return Data(data={
                "success": False,
                "error": "Channel and message_ts are required for reactions.",
                "error_code": "invalid_input",
            })

        # Strip colons from emoji name
        clean_emoji = emoji.strip(": ") if emoji else ""

        if reaction_action == "get":
            return self._get_reactions(channel, message_ts, token)

        if not clean_emoji:
            return Data(data={
                "success": False,
                "error": "Emoji name is required for add/remove reactions.",
                "error_code": "invalid_input",
            })

        if reaction_action == "add":
            endpoint = "reactions.add"
        elif reaction_action == "remove":
            endpoint = "reactions.remove"
        else:
            return Data(data={
                "success": False,
                "error": f"Unknown reaction action: {reaction_action}. Use add, remove, or get.",
                "error_code": "invalid_input",
            })

        self.status = f"{'Adding' if reaction_action == 'add' else 'Removing'} :{clean_emoji}: reaction..."
        result = self._slack_api(
            "POST", endpoint, token,
            json={"channel": channel, "timestamp": message_ts, "name": clean_emoji},
        )

        if result["ok"]:
            self.status = f"Reaction :{clean_emoji}: {'added' if reaction_action == 'add' else 'removed'}"
            return Data(data={
                "success": True,
                "action": reaction_action,
                "emoji": clean_emoji,
                "reactions": None,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "action": reaction_action,
            "emoji": clean_emoji,
            "reactions": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    def _get_reactions(self, channel: str, message_ts: str, token: str) -> Data:
        self.status = "Getting reactions..."
        result = self._slack_api(
            "GET", "reactions.get", token,
            params={"channel": channel, "timestamp": message_ts},
        )

        if result["ok"]:
            msg = result["data"].get("message", {})
            reactions = [
                {"name": r.get("name", ""), "count": r.get("count", 0), "users": r.get("users", [])}
                for r in msg.get("reactions", [])
            ]
            self.status = f"Found {len(reactions)} reactions"
            return Data(data={
                "success": True,
                "action": "get",
                "emoji": None,
                "reactions": reactions,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "action": "get",
            "emoji": None,
            "reactions": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Upload File (Task 12) ----
    def _run_upload_file(
        self,
        channel: str = "",
        filename: str = "",
        file_content: str = "",
        file_path: str = "",
        initial_comment: str = "",
        title: str = "",
        thread_ts: str = "",
        token: str = "",
    ) -> Data:
        import requests as req_lib

        if not channel:
            return Data(data={"success": False, "error": "Channel is required for Upload.", "error_code": "invalid_input"})

        if not filename:
            return Data(data={"success": False, "error": "Filename is required for Upload.", "error_code": "invalid_input"})

        # Resolve file bytes
        if file_content:
            file_bytes = file_content.encode("utf-8")
        elif file_path:
            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
            except FileNotFoundError:
                return Data(data={"success": False, "error": f"File not found: {file_path}", "error_code": "file_not_found"})
            except OSError as exc:
                return Data(data={"success": False, "error": f"Cannot read file: {exc}", "error_code": "invalid_input"})
        else:
            return Data(data={
                "success": False,
                "error": "Either file_content or file_path is required for Upload.",
                "error_code": "invalid_input",
            })

        length = len(file_bytes)

        # Step 1: Get upload URL
        self.status = f"Requesting upload URL for {filename}..."
        step1 = self._slack_api(
            "GET", "files.getUploadURLExternal", token,
            params={"filename": filename, "length": length},
        )
        if not step1["ok"]:
            self.status = f"Error: {step1['error_code']}"
            return Data(data={"success": False, "error": step1["error"], "error_code": step1["error_code"]})

        upload_url = step1["data"].get("upload_url")
        file_id = step1["data"].get("file_id")

        # Step 2: PUT file bytes to upload URL (direct HTTP, not Slack API)
        self.status = f"Uploading {filename} ({length} bytes)..."
        try:
            put_response = req_lib.put(upload_url, data=file_bytes, timeout=60)
            if put_response.status_code not in (200, 201):
                return Data(data={
                    "success": False,
                    "error": f"File upload PUT failed with HTTP {put_response.status_code}",
                    "error_code": "request_error",
                })
        except req_lib.exceptions.RequestException as exc:
            return Data(data={"success": False, "error": f"File upload failed: {exc}", "error_code": "request_error"})

        # Step 3: Complete upload and share to channel
        self.status = f"Completing upload to {channel}..."
        complete_payload: dict = {
            "files": [{"id": file_id, "title": title or filename}],
            "channel_id": channel,
        }
        if initial_comment:
            complete_payload["initial_comment"] = initial_comment
        if thread_ts:
            complete_payload["thread_ts"] = thread_ts

        step3 = self._slack_api("POST", "files.completeUploadExternal", token, json=complete_payload)

        if step3["ok"]:
            self.status = f"File {filename} uploaded successfully"
            return Data(data={
                "success": True,
                "file_id": file_id,
                "channel": channel,
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {step3['error_code']}"
        return Data(data={
            "success": False,
            "file_id": file_id,
            "channel": channel,
            "error": step3["error"],
            "error_code": step3["error_code"],
        })

    # ---- Modal helpers ----
    @staticmethod
    def _validate_view_json(view_json: str) -> tuple[dict | None, str | None]:
        """Parse and validate a modal view JSON object.

        Returns:
            (parsed_view_dict, error_message)
        """
        if not view_json or not view_json.strip():
            return None, "view_json is required."
        try:
            parsed = json.loads(view_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return None, f"Invalid view JSON: {exc}"
        if not isinstance(parsed, dict):
            return None, "View JSON must be a JSON object (dict), not an array."
        return parsed, None

    # ---- Open Modal (Task 11) ----
    def _run_open_modal(
        self,
        trigger_id: str = "",
        view_json: str = "",
        token: str = "",
    ) -> Data:
        if not trigger_id:
            return Data(data={
                "success": False,
                "error": "trigger_id is required. It comes from the Slack slash command or interactive payload.",
                "error_code": "invalid_input",
            })

        view, view_err = self._validate_view_json(view_json)
        if view_err:
            self.status = f"Error: {view_err}"
            return Data(data={"success": False, "error": view_err, "error_code": "invalid_input"})

        self.status = "Opening modal..."
        result = self._slack_api(
            "POST", "views.open", token,
            json={"trigger_id": trigger_id, "view": view},
        )

        if result["ok"]:
            view_data = result["data"].get("view", {})
            self.status = "Modal opened successfully"
            return Data(data={
                "success": True,
                "view_id": view_data.get("id"),
                "external_id": view_data.get("external_id"),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "view_id": None,
            "external_id": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Update Modal (Task 11) ----
    def _run_update_modal(
        self,
        view_id: str = "",
        view_json: str = "",
        view_hash: str = "",
        token: str = "",
    ) -> Data:
        if not view_id:
            return Data(data={
                "success": False,
                "error": "view_id is required (returned by views.open).",
                "error_code": "invalid_input",
            })

        view, view_err = self._validate_view_json(view_json)
        if view_err:
            self.status = f"Error: {view_err}"
            return Data(data={"success": False, "error": view_err, "error_code": "invalid_input"})

        payload: dict = {"view_id": view_id, "view": view}
        if view_hash:
            payload["hash"] = view_hash

        self.status = f"Updating modal {view_id}..."
        result = self._slack_api("POST", "views.update", token, json=payload)

        if result["ok"]:
            view_data = result["data"].get("view", {})
            self.status = "Modal updated successfully"
            return Data(data={
                "success": True,
                "view_id": view_data.get("id", view_id),
                "hash": view_data.get("hash"),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "view_id": view_id,
            "hash": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ---- Push Modal (Task 11) ----
    def _run_push_modal(
        self,
        trigger_id: str = "",
        view_json: str = "",
        token: str = "",
    ) -> Data:
        if not trigger_id:
            return Data(data={
                "success": False,
                "error": "trigger_id is required for pushing a modal view.",
                "error_code": "invalid_input",
            })

        view, view_err = self._validate_view_json(view_json)
        if view_err:
            self.status = f"Error: {view_err}"
            return Data(data={"success": False, "error": view_err, "error_code": "invalid_input"})

        self.status = "Pushing modal view..."
        result = self._slack_api(
            "POST", "views.push", token,
            json={"trigger_id": trigger_id, "view": view},
        )

        if result["ok"]:
            view_data = result["data"].get("view", {})
            self.status = "Modal view pushed successfully"
            return Data(data={
                "success": True,
                "view_id": view_data.get("id"),
                "external_id": view_data.get("external_id"),
                "error": None,
                "error_code": None,
            })

        self.status = f"Error: {result['error_code']}"
        return Data(data={
            "success": False,
            "view_id": None,
            "external_id": None,
            "error": result["error"],
            "error_code": result["error_code"],
        })

    # ==================================================================
    # Agent tool interface (Task 14)
    # ==================================================================

    def build_tool(self) -> Tool | list[Tool]:
        """Build 12 focused StructuredTools for Agent use.

        Each tool has a unique name, description, and Pydantic input schema.
        Inner functions pass arguments directly to ``_run_*`` methods --
        they do NOT mutate ``self`` to avoid race conditions with concurrent
        Agent tool calls.
        """
        try:
            token = self._get_slack_token()
        except ValueError:
            token = ""  # Tools will fail with auth error at call time

        # -- Pydantic schemas ------------------------------------------------

        class SlackSendMessageInput(BaseModel):
            """Input for slack_send_message."""
            channel: str = Field(description="Channel ID (C...), channel name (#general), user ID (U...) for DM, or email for DM")
            text: str = Field(default="", description="Message text (also Block Kit fallback for notifications)")
            blocks_json: str = Field(default="", description="Raw Block Kit JSON array")
            thread_ts: str = Field(default="", description="Thread timestamp to reply to")
            reply_broadcast: bool = Field(default=False, description="Also post threaded reply to the channel")

        class SlackUpdateMessageInput(BaseModel):
            """Input for slack_update_message."""
            channel: str = Field(description="Channel ID where the message is")
            message_ts: str = Field(description="Timestamp of the message to update")
            text: str = Field(default="", description="New message text")
            blocks_json: str = Field(default="", description="New Block Kit JSON array")

        class SlackDeleteMessageInput(BaseModel):
            """Input for slack_delete_message."""
            channel: str = Field(description="Channel ID where the message is")
            message_ts: str = Field(description="Timestamp of the message to delete")

        class SlackReadHistoryInput(BaseModel):
            """Input for slack_read_history."""
            channel: str = Field(description="Channel ID to read from")
            limit: int = Field(default=20, description="Number of messages (max 200)")
            thread_ts: str = Field(default="", description="Thread timestamp to read replies from")
            oldest: str = Field(default="", description="Unix timestamp -- only messages after this")
            latest: str = Field(default="", description="Unix timestamp -- only messages before this")

        class SlackSearchMessagesInput(BaseModel):
            """Input for slack_search_messages."""
            query: str = Field(description="Search query. Supports in:#channel from:@user before:date")
            count: int = Field(default=20, description="Results per page (max 100)")

        class SlackGetUserInput(BaseModel):
            """Input for slack_get_user."""
            user_id: str = Field(default="", description="Slack user ID (U...)")
            email: str = Field(default="", description="Email address for lookup")
            list_all: bool = Field(default=False, description="List all workspace users")
            limit: int = Field(default=20, description="Max users to return when list_all=True")

        class SlackListChannelsInput(BaseModel):
            """Input for slack_list_channels."""
            channel: str = Field(default="", description="Specific channel ID for info, or empty to list")
            channel_types: str = Field(default="public_channel", description="Comma-separated: public_channel,private_channel,mpim,im")
            limit: int = Field(default=20, description="Max channels to return")

        class SlackAddReactionInput(BaseModel):
            """Input for slack_add_reaction."""
            channel: str = Field(description="Channel ID where the message is")
            message_ts: str = Field(description="Timestamp of the message to react to")
            emoji: str = Field(default="", description="Emoji name (e.g. thumbsup). Not needed for action=get")
            reaction_action: str = Field(default="add", description="add, remove, or get")

        class SlackUploadFileInput(BaseModel):
            """Input for slack_upload_file."""
            channel: str = Field(description="Channel to share the file in")
            filename: str = Field(description="Filename (e.g. report.txt)")
            file_content: str = Field(default="", description="Text/code content to upload as a file")
            initial_comment: str = Field(default="", description="Message alongside the file")
            title: str = Field(default="", description="Display title in Slack")
            thread_ts: str = Field(default="", description="Thread to upload into")

        class SlackOpenModalInput(BaseModel):
            """Input for slack_open_modal."""
            trigger_id: str = Field(description="Trigger ID from a Slack slash command or interactive payload. Expires in 3 seconds — call immediately.")
            view_json: str = Field(description="Modal view definition as a JSON object string")

        class SlackUpdateModalInput(BaseModel):
            """Input for slack_update_modal."""
            view_id: str = Field(description="The ID of the modal view to update (returned by views.open)")
            view_json: str = Field(description="Updated modal view definition as a JSON object string")
            view_hash: str = Field(default="", description="Hash of the current view for optimistic locking (optional)")

        class SlackPushModalInput(BaseModel):
            """Input for slack_push_modal."""
            trigger_id: str = Field(description="Trigger ID from a Slack interactive payload. Expires in 3 seconds — call immediately.")
            view_json: str = Field(description="Modal view definition to push onto the stack as a JSON object string")

        # -- Tool inner functions --------------------------------------------
        # CRITICAL: These pass args directly to _run_* methods.
        # They do NOT set self.attribute = value (race condition prevention).

        def _send(channel: str, text: str = "", blocks_json: str = "", thread_ts: str = "", reply_broadcast: bool = False) -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            ch, dm_err = self._resolve_dm_target(ch, t)
            if dm_err:
                return f"Error: {dm_err}"
            r = self._run_send_message(channel=ch, text=text, blocks_json=blocks_json, thread_ts=thread_ts, reply_broadcast=reply_broadcast, token=t)
            return self._tool_response(r)

        def _update(channel: str, message_ts: str, text: str = "", blocks_json: str = "") -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            r = self._run_update_message(channel=ch, message_ts=message_ts, text=text, blocks_json=blocks_json, token=t)
            return self._tool_response(r)

        def _delete(channel: str, message_ts: str) -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            r = self._run_delete_message(channel=ch, message_ts=message_ts, token=t)
            return self._tool_response(r)

        def _read(channel: str, limit: int = 20, thread_ts: str = "", oldest: str = "", latest: str = "") -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            r = self._run_read_messages(channel=ch, limit=limit, thread_ts=thread_ts, oldest=oldest, latest=latest, token=t)
            return self._tool_response(r)

        def _search(query: str, count: int = 20) -> str:
            t = self._get_slack_token()
            r = self._run_search_messages(query=query, count=count, token=t)
            return self._tool_response(r)

        def _get_user(user_id: str = "", email: str = "", list_all: bool = False, limit: int = 20) -> str:
            t = self._get_slack_token()
            r = self._run_get_user(user_id=user_id, email=email, list_all=list_all, limit=limit, token=t)
            return self._tool_response(r)

        def _list_channels(channel: str = "", channel_types: str = "public_channel", limit: int = 20) -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t) if channel else ""
            r = self._run_list_channels(channel=ch, channel_types=channel_types, limit=limit, token=t)
            return self._tool_response(r)

        def _react(channel: str, message_ts: str, emoji: str = "", reaction_action: str = "add") -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            r = self._run_add_reaction(channel=ch, message_ts=message_ts, reaction_action=reaction_action, emoji=emoji, token=t)
            return self._tool_response(r)

        def _upload(channel: str, filename: str, file_content: str = "", initial_comment: str = "", title: str = "", thread_ts: str = "") -> str:
            t = self._get_slack_token()
            ch = self._resolve_channel(channel, t)
            r = self._run_upload_file(channel=ch, filename=filename, file_content=file_content, initial_comment=initial_comment, title=title, thread_ts=thread_ts, token=t)
            return self._tool_response(r)

        def _open_modal(trigger_id: str, view_json: str) -> str:
            t = self._get_slack_token()
            r = self._run_open_modal(trigger_id=trigger_id, view_json=view_json, token=t)
            return self._tool_response(r)

        def _update_modal(view_id: str, view_json: str, view_hash: str = "") -> str:
            t = self._get_slack_token()
            r = self._run_update_modal(view_id=view_id, view_json=view_json, view_hash=view_hash, token=t)
            return self._tool_response(r)

        def _push_modal(trigger_id: str, view_json: str) -> str:
            t = self._get_slack_token()
            r = self._run_push_modal(trigger_id=trigger_id, view_json=view_json, token=t)
            return self._tool_response(r)

        # -- Build tools list ------------------------------------------------
        tools = [
            StructuredTool.from_function(
                name="slack_send_message",
                description=(
                    "Send a message to a Slack channel, thread, or DM. Supports Block Kit JSON for rich formatting. "
                    "The channel field accepts channel IDs (C...), names (#general), user IDs (U...) for DMs, or email addresses for DMs."
                ),
                func=_send,
                args_schema=SlackSendMessageInput,
                return_direct=False,
                tags=["slack_send_message"],
            ),
            StructuredTool.from_function(
                name="slack_update_message",
                description="Update an existing Slack message in-place. Requires channel and message_ts (timestamp of the original message).",
                func=_update,
                args_schema=SlackUpdateMessageInput,
                return_direct=False,
                tags=["slack_update_message"],
            ),
            StructuredTool.from_function(
                name="slack_delete_message",
                description="Delete a Slack message. Requires channel and message_ts.",
                func=_delete,
                args_schema=SlackDeleteMessageInput,
                return_direct=False,
                tags=["slack_delete_message"],
            ),
            StructuredTool.from_function(
                name="slack_read_history",
                description=(
                    "Read message history from a Slack channel or thread replies. "
                    "Returns messages with text, user, timestamp, reactions, and blocks."
                ),
                func=_read,
                args_schema=SlackReadHistoryInput,
                return_direct=False,
                tags=["slack_read_history"],
            ),
            StructuredTool.from_function(
                name="slack_search_messages",
                description=(
                    "Search Slack messages across the workspace. Requires a user token (xoxp-). "
                    "Supports Slack search modifiers: in:#channel from:@user before:2024-01-01"
                ),
                func=_search,
                args_schema=SlackSearchMessagesInput,
                return_direct=False,
                tags=["slack_search_messages"],
            ),
            StructuredTool.from_function(
                name="slack_get_user",
                description="Look up a Slack user by ID, email, or list all workspace users. Returns profile info including name, email, and status.",
                func=_get_user,
                args_schema=SlackGetUserInput,
                return_direct=False,
                tags=["slack_get_user"],
            ),
            StructuredTool.from_function(
                name="slack_list_channels",
                description="List Slack channels or get info about a specific channel. Returns channel name, topic, purpose, and member count.",
                func=_list_channels,
                args_schema=SlackListChannelsInput,
                return_direct=False,
                tags=["slack_list_channels"],
            ),
            StructuredTool.from_function(
                name="slack_add_reaction",
                description="Add, remove, or get emoji reactions on a Slack message. Emoji name without colons (e.g. 'thumbsup', not ':thumbsup:').",
                func=_react,
                args_schema=SlackAddReactionInput,
                return_direct=False,
                tags=["slack_add_reaction"],
            ),
            StructuredTool.from_function(
                name="slack_upload_file",
                description="Upload text/code content as a file to a Slack channel. Provide filename and file_content.",
                func=_upload,
                args_schema=SlackUploadFileInput,
                return_direct=False,
                tags=["slack_upload_file"],
            ),
            StructuredTool.from_function(
                name="slack_open_modal",
                description=(
                    "Open a Slack modal dialog. Requires a trigger_id from a slash command or interactive payload "
                    "(expires in 3 seconds — call IMMEDIATELY after receiving the event). "
                    "view_json is the modal definition as a JSON object string."
                ),
                func=_open_modal,
                args_schema=SlackOpenModalInput,
                return_direct=False,
                tags=["slack_open_modal"],
            ),
            StructuredTool.from_function(
                name="slack_update_modal",
                description=(
                    "Update an existing open Slack modal. Requires view_id (returned by views.open) "
                    "and the new view_json. Optionally pass view_hash for optimistic locking."
                ),
                func=_update_modal,
                args_schema=SlackUpdateModalInput,
                return_direct=False,
                tags=["slack_update_modal"],
            ),
            StructuredTool.from_function(
                name="slack_push_modal",
                description=(
                    "Push a new view onto an existing Slack modal stack. Requires trigger_id from an interactive payload "
                    "within the current modal (expires in 3 seconds). Creates a multi-step modal flow."
                ),
                func=_push_modal,
                args_schema=SlackPushModalInput,
                return_direct=False,
                tags=["slack_push_modal"],
            ),
        ]

        self.status = f"12 tools created"
        return tools

    async def _get_tools(self):
        """Return the 12 focused tools for Agent use.

        Following the AtlassianMCPComponent pattern: delegate to build_tool(),
        ensure tags are set on each tool.
        """
        tools = self.build_tool()
        if isinstance(tools, list):
            for tool in tools:
                if tool and not tool.tags:
                    tool.tags = [tool.name]
            return tools
        if tools and not tools.tags:
            tools.tags = [tools.name]
        return [tools] if tools else []

    @staticmethod
    def _tool_response(result: Data) -> str:
        """Format a Data result as a string for Agent tool output."""
        data = result.data if hasattr(result, "data") else {}
        return json.dumps(data, default=str, indent=2)
