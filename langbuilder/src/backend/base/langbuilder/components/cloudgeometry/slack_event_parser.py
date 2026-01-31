"""
Slack Event Parser Component for MeetBot

Parses Slack interactive payloads (button clicks and modal submissions)
into structured data for routing in Flow 2 (approval/edit/reject).

This is the first node in Flow 2 — it normalizes all Slack interaction
types into a consistent format that downstream components can route on.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class SlackEventParserComponent(Component):
    """
    Parse Slack interactive payloads into structured routing data.

    Handles ``block_actions`` (button clicks, overflow menus) and
    ``view_submission`` (modal form submissions). Extracts action type,
    item ID, thread timestamp, user ID, and trigger ID into a flat
    Data object for downstream routing.
    """

    display_name = "Slack Event Parser"
    description = (
        "Parse Slack interactive payloads (button clicks, modal submissions) "
        "into structured data for routing."
    )
    icon = "Slack"
    name = "SlackEventParser"

    inputs = [
        StrInput(
            name="raw_payload",
            display_name="Raw Payload",
            info=(
                "The raw Slack interactive payload JSON. "
                "Slack sends this as a 'payload' field in application/x-www-form-urlencoded body."
            ),
            required=True,
            is_list=False,
        ),
        SecretStrInput(
            name="signing_secret",
            display_name="Slack Signing Secret",
            info="Slack signing secret for request verification (optional for demo)",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="request_timestamp",
            display_name="Request Timestamp",
            info="X-Slack-Request-Timestamp header value (for signature verification)",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="request_signature",
            display_name="Request Signature",
            info="X-Slack-Signature header value (for signature verification)",
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="parsed_event", display_name="Parsed Event", method="parse_event"),
    ]

    def _verify_signature(self, body: str) -> bool:
        """Verify Slack request signature. Returns True if valid or if verification is skipped."""
        if not self.signing_secret or not self.request_timestamp or not self.request_signature:
            return True  # Skip verification if not configured

        # Check timestamp freshness (5 minute window)
        try:
            ts = int(self.request_timestamp)
            if abs(time.time() - ts) > 300:
                self.log("Request timestamp too old (>5 min)")
                return False
        except (ValueError, TypeError):
            return False

        sig_basestring = f"v0:{self.request_timestamp}:{body}"
        computed = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, self.request_signature)

    def parse_event(self) -> Data:
        """Parse a Slack interactive payload into structured routing data."""
        raw = self.raw_payload
        if not raw or not raw.strip():
            return Data(data={"error": "Empty payload", "action_type": "error"})

        # Parse JSON
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return Data(data={"error": "Invalid JSON payload", "action_type": "error"})

        # Optional signature verification
        if not self._verify_signature(raw):
            return Data(data={"error": "Invalid request signature", "action_type": "error"})

        payload_type = payload.get("type", "")
        user = payload.get("user", {})
        user_slack_id = user.get("id", "") if isinstance(user, dict) else ""
        trigger_id = payload.get("trigger_id", "")

        # --- block_actions: button click or overflow menu selection ---
        if payload_type == "block_actions":
            actions = payload.get("actions", [])
            if not actions:
                return Data(data={
                    "error": "No actions in block_actions payload",
                    "action_type": "error",
                    "user_slack_id": user_slack_id,
                })

            action = actions[0]
            action_id = action.get("action_id", "")

            # "Approve All" or "Force Execute All" buttons
            if action_id in ("approve_all", "force_execute_all"):
                thread_ts = action.get("value", "")
                return Data(data={
                    "action_type": action_id,
                    "item_id": "",
                    "slack_thread_ts": thread_ts,
                    "user_slack_id": user_slack_id,
                    "trigger_id": trigger_id,
                    "payload_type": "block_actions",
                })

            # Overflow menu selection (per-item approve/edit/reject)
            selected = action.get("selected_option", {})
            value = selected.get("value", "") if selected else action.get("value", "")

            if "|" in value:
                parts = value.split("|", 2)
                action_type = parts[0] if len(parts) > 0 else "unknown"
                item_id = parts[1] if len(parts) > 1 else ""
                thread_ts = parts[2] if len(parts) > 2 else ""
            else:
                action_type = action_id
                item_id = ""
                thread_ts = value

            return Data(data={
                "action_type": action_type,
                "item_id": item_id,
                "slack_thread_ts": thread_ts,
                "user_slack_id": user_slack_id,
                "trigger_id": trigger_id,
                "payload_type": "block_actions",
            })

        # --- view_submission: modal form submission ---
        if payload_type == "view_submission":
            view = payload.get("view", {})
            private_metadata = view.get("private_metadata", "")
            state_values = view.get("state", {}).get("values", {})

            # Parse private_metadata (format: "action|item_id|thread_ts")
            if "|" in private_metadata:
                parts = private_metadata.split("|", 2)
                action_type = parts[0] if len(parts) > 0 else "modal_submit"
                item_id = parts[1] if len(parts) > 1 else ""
                thread_ts = parts[2] if len(parts) > 2 else ""
            else:
                action_type = "modal_submit"
                item_id = ""
                thread_ts = private_metadata

            # Flatten form field values
            submission_data = {}
            for block_id, block_vals in state_values.items():
                for action_id, action_val in block_vals.items():
                    field_type = action_val.get("type", "")
                    if field_type == "plain_text_input":
                        submission_data[block_id] = action_val.get("value", "")
                    elif field_type == "static_select":
                        selected = action_val.get("selected_option", {})
                        submission_data[block_id] = selected.get("value", "") if selected else ""
                    else:
                        submission_data[block_id] = action_val.get("value", "")

            return Data(data={
                "action_type": action_type,
                "item_id": item_id,
                "slack_thread_ts": thread_ts,
                "user_slack_id": user_slack_id,
                "trigger_id": trigger_id,
                "payload_type": "view_submission",
                "submission_data": submission_data,
            })

        # --- slash_command: /meetbot setup or /meetbot test ---
        if payload.get("command"):
            command = payload.get("command", "")
            text = payload.get("text", "").strip()
            return Data(data={
                "action_type": f"slash_command_{text}" if text else "slash_command",
                "item_id": "",
                "slack_thread_ts": "",
                "user_slack_id": payload.get("user_id", ""),
                "trigger_id": trigger_id,
                "payload_type": "slash_command",
                "command": command,
                "command_text": text,
            })

        # Unknown payload type
        return Data(data={
            "error": f"Unrecognized payload type: {payload_type}",
            "action_type": "error",
            "payload_type": payload_type,
            "user_slack_id": user_slack_id,
        })
