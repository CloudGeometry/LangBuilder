"""
Slack Notify Component

Post notification messages to Slack channels with optional user mentions.
Supports email-based user lookup, direct Slack ID mentions, and broadcast mentions (@here, @channel, @everyone).

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from langbuilder.base.langchain_utilities.model import LCToolComponent
from langbuilder.field_typing import Tool
from langbuilder.io import (
    DropdownInput,
    MessageTextInput,
    SecretStrInput,
    StrInput,
)
from langbuilder.schema.data import Data

if TYPE_CHECKING:
    pass


# Constants
MAX_MESSAGE_LENGTH = 4000
REQUEST_TIMEOUT = 10
MAX_RATE_LIMIT_WAIT = 60
DEFAULT_RATE_LIMIT_WAIT = 30

# Human-readable error messages
ERROR_MESSAGES = {
    "channel_not_found": "The specified channel was not found. Verify the channel ID exists and the bot has access.",
    "invalid_auth": "Authentication failed. The bot token is invalid or expired.",
    "not_in_channel": "The bot is not a member of this private channel. Invite the bot or use a public channel.",
    "rate_limited": "Rate limit exceeded after retry. Please try again later.",
    "user_not_found": "User not found for the provided email address.",
    "users_not_found": "User not found for the provided email address.",
    "missing_scope": "The bot is missing required OAuth scopes. Reinstall the app with chat:write and users:read scopes.",
    "is_archived": "Cannot post to an archived channel.",
    "timeout": "Request timed out after 10 seconds. Slack may be experiencing issues.",
    "connection_error": "Could not connect to Slack API. Check network connectivity.",
    "invalid_input": "Invalid input: message is required and cannot be empty.",
    "no_text": "Message content is required.",
}


class SlackNotifyComponent(LCToolComponent):
    """Post notification messages to Slack channels with optional user mentions."""

    display_name = "Slack Notify"
    description = "Post a notification message to a Slack channel with optional user mentions."
    icon = "Slack"
    name = "SlackNotify"

    inputs = [
        # Agent-passable inputs (tool_mode=True)
        MessageTextInput(
            name="message",
            display_name="Message",
            info="The message text to post to Slack",
            required=True,
            tool_mode=True,
        ),
        StrInput(
            name="channel",
            display_name="Channel Override",
            info="Optional channel ID to override the default (e.g., C0123456789)",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        StrInput(
            name="mention_user",
            display_name="Mention User",
            info="Email address or Slack user ID to mention in the message",
            required=False,
            tool_mode=True,
        ),
        DropdownInput(
            name="special_mention",
            display_name="Special Mention",
            info="Broadcast mention type (@here, @channel, @everyone)",
            options=["none", "here", "channel", "everyone"],
            value="none",
            required=False,
            tool_mode=True,
            advanced=True,
        ),
        # Configuration inputs (NO tool_mode - set once at component level)
        StrInput(
            name="default_channel",
            display_name="Default Channel",
            info="Default Slack channel ID (e.g., C0123456789)",
            required=True,
        ),
        SecretStrInput(
            name="slack_bot_token",
            display_name="Slack Bot Token",
            info="Leave empty to use environment variable SLACK_BOT_TOKEN",
            required=False,
        ),
    ]

    # Uses default LCToolComponent outputs

    def run_model(self) -> Data:
        """Execute the component's main logic - post message to Slack.

        Returns:
            Data: Contains success status, message_ts on success, or error details on failure.
        """
        # Runtime import for requests
        try:
            import requests
        except ImportError as e:
            msg = "requests is not installed. Install with: pip install requests"
            raise ImportError(msg) from e

        # Validate message input
        message = self.message if hasattr(self, "message") and self.message else ""
        if not message or not message.strip():
            self.status = "Error: invalid_input"
            return Data(
                data={
                    "success": False,
                    "message_ts": None,
                    "channel": None,
                    "error": ERROR_MESSAGES["invalid_input"],
                    "error_code": "invalid_input",
                    "mention_warning": None,
                }
            )

        # Get channel (use override if provided, else default)
        channel = self._get_channel()
        if not channel:
            self.status = "Error: No channel specified"
            return Data(
                data={
                    "success": False,
                    "message_ts": None,
                    "channel": None,
                    "error": "No channel specified. Provide a default_channel or channel override.",
                    "error_code": "invalid_input",
                    "mention_warning": None,
                }
            )

        # Get token
        try:
            token = self._get_slack_token()
        except ValueError as e:
            self.status = f"Error: {e}"
            return Data(
                data={
                    "success": False,
                    "message_ts": None,
                    "channel": None,
                    "error": str(e),
                    "error_code": "invalid_auth",
                    "mention_warning": None,
                }
            )

        # Process message: truncation, escaping, mentions
        mention_warning = None
        processed_message, mention_warning = self._build_message(message, token, requests)

        # Post to Slack
        result = self._post_message(channel, processed_message, token, requests)

        # Add mention warning if present
        if mention_warning:
            result["mention_warning"] = mention_warning

        return Data(data=result)

    def _get_channel(self) -> str:
        """Get the target channel (override or default)."""
        # Priority 1: Explicit channel override
        if hasattr(self, "channel") and self.channel and self.channel.strip():
            return self.channel.strip()

        # Priority 2: Default channel
        if hasattr(self, "default_channel") and self.default_channel:
            return self.default_channel.strip()

        return ""

    def _get_slack_token(self) -> str:
        """Get Slack bot token with flexible credential handling.

        Returns:
            str: The Slack bot token.

        Raises:
            ValueError: If no token is found.
        """
        import os

        if hasattr(self, "slack_bot_token") and self.slack_bot_token:
            self.log("Using provided Slack bot token")
            return self.slack_bot_token

        # Fall back to environment variable
        token = os.environ.get("SLACK_BOT_TOKEN")
        if token:
            self.log("Using SLACK_BOT_TOKEN from environment")
            return token

        raise ValueError("No Slack bot token provided and SLACK_BOT_TOKEN not set in environment")

    def _escape_message(self, text: str) -> str:
        """Escape special characters in message text per Slack API requirements.

        Escapes &, <, > but preserves valid Slack syntax like <@U123>, <!here>, <URL|text>.
        """
        # Find all valid Slack special syntax to preserve
        # Patterns: <@U...>, <#C...>, <!here>, <!channel>, <!everyone>, <!subteam^...>, <URL|text>
        preserved_patterns = []
        pattern = r"<[@#!][^>]+>|<https?://[^>]+>"

        # Find and store all matches
        for match in re.finditer(pattern, text):
            preserved_patterns.append((match.start(), match.end(), match.group()))

        # Process the text character by character, escaping outside preserved regions
        result = []
        i = 0
        preserved_idx = 0

        while i < len(text):
            # Check if we're at a preserved pattern
            if preserved_idx < len(preserved_patterns):
                start, end, preserved_text = preserved_patterns[preserved_idx]
                if i == start:
                    result.append(preserved_text)
                    i = end
                    preserved_idx += 1
                    continue

            # Escape special characters
            char = text[i]
            if char == "&":
                result.append("&amp;")
            elif char == "<":
                result.append("&lt;")
            elif char == ">":
                result.append("&gt;")
            else:
                result.append(char)
            i += 1

        return "".join(result)

    def _truncate_message(self, text: str) -> str:
        """Truncate message to MAX_MESSAGE_LENGTH and add [truncated] suffix if needed."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return text

        self.log(f"WARNING: Message truncated from {len(text)} to {MAX_MESSAGE_LENGTH} characters")
        truncated_suffix = " [truncated]"
        max_content_length = MAX_MESSAGE_LENGTH - len(truncated_suffix)
        return text[:max_content_length] + truncated_suffix

    def _resolve_user_id(self, mention_user: str, token: str, requests_module) -> tuple[str | None, str | None]:
        """Resolve a user mention to a Slack user ID.

        Args:
            mention_user: Email address or Slack user ID.
            token: Slack bot token.
            requests_module: The requests module (runtime imported).

        Returns:
            Tuple of (user_id or None, warning_message or None).
        """
        if not mention_user or not mention_user.strip():
            return None, None

        mention_user = mention_user.strip()

        # Check if it looks like an email
        if "@" in mention_user and not mention_user.startswith("U"):
            # Attempt email lookup
            user_id = self._lookup_user_by_email(mention_user, token, requests_module)
            if user_id:
                self.log(f"Resolved user email {mention_user} to {user_id}")
                return user_id, None

            # Email lookup failed - warn but don't fail
            warning = f"Could not resolve user: {mention_user}. Message posted without mention."
            self.log(f"WARNING: User mention failed for '{mention_user}': email lookup returned users_not_found")
            return None, warning

        # Treat as direct user ID (starts with U typically)
        # Validate format loosely - Slack IDs typically start with U
        if mention_user.startswith("U") or mention_user.startswith("W"):
            return mention_user, None

        # Unknown format - try to use as-is but warn
        warning = f"Could not resolve user: {mention_user}. Message posted without mention."
        self.log(f"WARNING: User mention '{mention_user}' has unknown format, skipping mention")
        return None, warning

    def _lookup_user_by_email(self, email: str, token: str, requests_module) -> str | None:
        """Look up a Slack user ID by email address.

        Args:
            email: User's email address.
            token: Slack bot token.
            requests_module: The requests module.

        Returns:
            User ID if found, None otherwise.
        """
        url = "https://slack.com/api/users.lookupByEmail"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        params = {"email": email}

        try:
            response = requests_module.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            data = response.json()

            if data.get("ok") and data.get("user", {}).get("id"):
                return data["user"]["id"]

            self.log(f"User lookup failed for {email}: {data.get('error', 'unknown error')}")
            return None

        except requests_module.exceptions.Timeout:
            self.log(f"User lookup timed out for {email}")
            return None
        except requests_module.exceptions.RequestException as e:
            self.log(f"User lookup request failed for {email}: {e}")
            return None

    def _build_message(self, message: str, token: str, requests_module) -> tuple[str, str | None]:
        """Build the complete message with mentions and escaping.

        Args:
            message: The original message text.
            token: Slack bot token.
            requests_module: The requests module.

        Returns:
            Tuple of (processed_message, mention_warning or None).
        """
        mention_warning = None
        prefix_parts = []

        # Handle special mention
        special_mention = getattr(self, "special_mention", "none") or "none"
        if special_mention in ("here", "channel", "everyone"):
            prefix_parts.append(f"<!{special_mention}>")

        # Handle user mention
        mention_user = getattr(self, "mention_user", "") or ""
        if mention_user:
            user_id, warning = self._resolve_user_id(mention_user, token, requests_module)
            if user_id:
                prefix_parts.append(f"<@{user_id}>")
            if warning:
                mention_warning = warning

        # Escape the message content
        escaped_message = self._escape_message(message)

        # Combine prefix with message
        if prefix_parts:
            full_message = " ".join(prefix_parts) + " " + escaped_message
        else:
            full_message = escaped_message

        # Truncate if needed
        full_message = self._truncate_message(full_message)

        return full_message, mention_warning

    def _post_message(
        self, channel: str, text: str, token: str, requests_module, retry_count: int = 0
    ) -> dict:
        """Post a message to Slack using chat.postMessage API.

        Args:
            channel: Channel ID to post to.
            text: Message text to post.
            token: Slack bot token.
            requests_module: The requests module.
            retry_count: Current retry attempt (for rate limiting).

        Returns:
            Result dictionary with success status and details.
        """
        import time

        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel,
            "text": text,
            "unfurl_links": False,
            "unfurl_media": False,
        }

        self.status = f"Posting to {channel}..."

        try:
            response = requests_module.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count >= 1:
                    # Max retries exceeded
                    self._log_error("Rate Limited", "rate_limited", channel, "rate_limited")
                    self.status = "Error: rate_limited"
                    return {
                        "success": False,
                        "message_ts": None,
                        "channel": channel,
                        "error": ERROR_MESSAGES["rate_limited"],
                        "error_code": "rate_limited",
                        "mention_warning": None,
                    }

                # Get retry-after header
                retry_after = response.headers.get("Retry-After", DEFAULT_RATE_LIMIT_WAIT)
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    retry_after = DEFAULT_RATE_LIMIT_WAIT

                # Cap at max wait time
                retry_after = min(retry_after, MAX_RATE_LIMIT_WAIT)

                self.log(f"Rate limited by Slack. Retrying in {retry_after}s (attempt 2/2)")
                time.sleep(retry_after)
                return self._post_message(channel, text, token, requests_module, retry_count + 1)

            # Parse response
            data = response.json()

            if data.get("ok"):
                message_ts = data.get("ts", "")
                response_channel = data.get("channel", channel)
                self.status = "Message posted successfully"
                self.log(f"Message posted to {response_channel}: {message_ts}")
                return {
                    "success": True,
                    "message_ts": message_ts,
                    "channel": response_channel,
                    "error": None,
                    "error_code": None,
                    "mention_warning": None,
                }

            # API error
            error_code = data.get("error", "unknown_error")
            error_message = ERROR_MESSAGES.get(error_code, f"Slack API error: {error_code}")
            self._log_error("API Error", error_message, channel, error_code)
            self.status = f"Error: {error_code}"
            return {
                "success": False,
                "message_ts": None,
                "channel": channel,
                "error": error_message,
                "error_code": error_code,
                "mention_warning": None,
            }

        except requests_module.exceptions.Timeout:
            self._log_error("Network Error", "Connection timed out", channel, "timeout")
            self.status = "Error: timeout"
            return {
                "success": False,
                "message_ts": None,
                "channel": channel,
                "error": ERROR_MESSAGES["timeout"],
                "error_code": "timeout",
                "mention_warning": None,
            }

        except requests_module.exceptions.ConnectionError as e:
            self._log_error("Network Error", str(e), channel, "connection_error")
            self.status = "Error: connection_error"
            return {
                "success": False,
                "message_ts": None,
                "channel": channel,
                "error": ERROR_MESSAGES["connection_error"],
                "error_code": "connection_error",
                "mention_warning": None,
            }

        except requests_module.exceptions.RequestException as e:
            self._log_error("Request Error", str(e), channel, "request_error")
            self.status = f"Error: {type(e).__name__}"
            return {
                "success": False,
                "message_ts": None,
                "channel": channel,
                "error": f"Request failed: {e}",
                "error_code": "request_error",
                "mention_warning": None,
            }

        except Exception as e:
            self._log_error("Unexpected Error", str(e), channel, "unknown_error")
            self.status = f"Error: {type(e).__name__}"
            return {
                "success": False,
                "message_ts": None,
                "channel": channel,
                "error": f"Unexpected error: {e}",
                "error_code": "unknown_error",
                "mention_warning": None,
            }

    def _log_error(self, error_type: str, error_message: str, channel: str, error_code: str) -> None:
        """Log an error with standardized format."""
        self.log(f"[SlackNotify] {error_type}: {error_message} | channel={channel} | error_code={error_code}")

    async def _get_tools(self):
        """Override to return the named tool from build_tool() instead of generic outputs."""
        tool = self.build_tool()
        # Ensure tool has tags for framework compatibility
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """Build LangChain tool for Agent use.

        Returns:
            Tool: StructuredTool that can be called by an Agent.
        """

        class SlackNotifyInput(BaseModel):
            """Input schema for slack_notify tool."""

            message: str = Field(description="The message text to post to Slack")
            channel: str = Field(default="", description="Optional channel ID override (e.g., C0123456789)")
            mention_user: str = Field(
                default="", description="Email address or Slack user ID to mention in the message"
            )
            special_mention: str = Field(
                default="none", description="Broadcast mention type: none, here, channel, or everyone"
            )

        def _send_notification(
            message: str,
            channel: str = "",
            mention_user: str = "",
            special_mention: str = "none",
        ) -> str:
            """Inner function that bridges tool call to component execution."""
            # Set component attributes from tool input
            self.message = message
            self.channel = channel if channel else ""
            self.mention_user = mention_user
            self.special_mention = special_mention

            # Call run_model to execute
            result = self.run_model()

            # Format response for Agent
            if result.data.get("success"):
                response = f"Message posted successfully to {result.data.get('channel', 'channel')}."
                if result.data.get("mention_warning"):
                    response += f" Warning: {result.data['mention_warning']}"
                return response
            else:
                error_msg = result.data.get("error", "Unknown error")
                return f"Failed to post message: {error_msg}"

        tool = StructuredTool.from_function(
            name="slack_notify",
            description=(
                "Post a notification message to a Slack channel. "
                "Use this tool when you need to notify team members or post updates to Slack. "
                "Supports optional user mentions via email or Slack ID, and broadcast mentions (@here, @channel, @everyone)."
            ),
            args_schema=SlackNotifyInput,
            func=_send_notification,
            return_direct=False,
            tags=["slack_notify"],
        )

        self.status = "Tool created"
        return tool
