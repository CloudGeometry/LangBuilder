# Slack Component Tutorial

The Slack component is a unified node for all common Slack operations. Drag one node onto your canvas and select the operation you need — no need for separate nodes for sending, reading, searching, etc.

This tutorial covers setup, every operation, and how to use the component in Agent (Tool) mode.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Setup and Authentication](#2-setup-and-authentication)
3. [Operations Overview](#3-operations-overview)
4. [Send Message](#4-send-message)
5. [Update Message](#5-update-message)
6. [Delete Message](#6-delete-message)
7. [Read Messages](#7-read-messages)
8. [Search Messages](#8-search-messages)
9. [Get User](#9-get-user)
10. [List Channels](#10-list-channels)
11. [React](#11-react)
12. [Upload File](#12-upload-file)
13. [Modals (Open, Update, Push)](#13-modals-open-update-push)
14. [Agent / Tool Mode](#14-agent--tool-mode)
15. [Channel Resolution](#15-channel-resolution)
16. [Output Format](#16-output-format)
17. [Error Handling](#17-error-handling)
18. [Common Recipes](#18-common-recipes)

---

## 1. Prerequisites

Before using the Slack component, you need a **Slack App** with a **Bot Token**.

### Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** > **From scratch**
3. Name your app and select your workspace
4. Go to **OAuth & Permissions** in the sidebar

### Required Bot Token Scopes

Add these scopes under **Bot Token Scopes** based on the operations you need:

| Operation | Required Scopes |
|-----------|----------------|
| Send Message | `chat:write` (public channels also need `chat:write.public`) |
| Update Message | `chat:write` |
| Delete Message | `chat:write` |
| Read Messages | `channels:history`, `groups:history` (private) |
| Search Messages | Requires a **User Token** (`xoxp-`) with `search:read` |
| Get User | `users:read`, `users:read.email` |
| List Channels | `channels:read`, `groups:read` (private) |
| React | `reactions:write`, `reactions:read` |
| Upload File | `files:write` |
| Direct Messages | `im:write`, `im:read`, `users:read.email` (for email lookup) |
| Modals | `commands` (for slash commands), no additional scope for views API |

After adding scopes, click **Install to Workspace** and copy the **Bot User OAuth Token** (`xoxb-...`).

---

## 2. Setup and Authentication

### Option A: Enter the Token Directly

In the component's **Slack Bot Token** field, paste your `xoxb-...` token. Use the lock icon to keep it hidden.

### Option B: Use an Environment Variable

Leave the **Slack Bot Token** field empty. Set the environment variable on your server:

```bash
export SLACK_BOT_TOKEN=xoxb-your-token-here
```

The component checks the input field first, then falls back to the environment variable.

---

## 3. Operations Overview

Select an operation from the **Operation** dropdown. Only the inputs relevant to your chosen operation need to be filled in — each input label indicates which operation(s) it belongs to (e.g., `[Send, Update]`).

| Operation | What It Does |
|-----------|-------------|
| **Send Message** | Post a new message to a channel, thread, or DM |
| **Update Message** | Edit an existing message in-place |
| **Delete Message** | Remove a message |
| **Read Messages** | Fetch message history from a channel or thread |
| **Search Messages** | Full-text search across the workspace (requires user token) |
| **Get User** | Look up a user by ID, email, or list all users |
| **List Channels** | List workspace channels or get info on a specific one |
| **React** | Add, remove, or get emoji reactions on a message |
| **Upload File** | Upload text/code content as a file to a channel |
| **Open Modal** | Open a modal dialog (from a slash command or interaction) |
| **Update Modal** | Update the content of an open modal |
| **Push Modal** | Push a new view onto a modal stack (multi-step flows) |

---

## 4. Send Message

The most common operation. Posts a message to a channel, thread, or direct message.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Where to send. See [Channel Resolution](#15-channel-resolution) |
| **Text** | Yes* | Message text. Required unless Blocks JSON is provided |
| **Blocks JSON** | No | Rich formatting via [Block Kit](https://app.slack.com/block-kit-builder). Must be a JSON array |
| **Thread Timestamp** | No | Reply to a specific thread instead of posting to the channel |
| **Reply Broadcast** | No | When replying in a thread, also post to the main channel (Advanced) |
| **Ephemeral User** | No | Show the message only to this user ID (Advanced) |
| **Unfurl Links / Media** | No | Enable link and media previews (Advanced) |

### Example: Simple Text Message

- **Operation**: Send Message
- **Channel**: `#general` or `C0123456789`
- **Text**: `Hello from LangBuilder!`

### Example: Threaded Reply

- **Operation**: Send Message
- **Channel**: `C0123456789`
- **Text**: `This is a reply`
- **Thread Timestamp**: `1234567890.123456` (from a previous message's output)

### Example: Rich Block Kit Message

- **Operation**: Send Message
- **Channel**: `#updates`
- **Text**: `Weekly report` (fallback for notifications)
- **Blocks JSON**:
```json
[
  {
    "type": "header",
    "text": { "type": "plain_text", "text": "Weekly Report" }
  },
  {
    "type": "section",
    "text": { "type": "mrkdwn", "text": "*Status:* All systems operational" }
  }
]
```

### Example: Direct Message

- **Channel**: `U0123456789` (user ID) or `user@company.com` (email)
- **Text**: `Hi, this is a DM from LangBuilder`

The component automatically opens a DM conversation when you pass a user ID or email in the Channel field.

---

## 5. Update Message

Edit an existing message. You need the channel and the message's timestamp (returned when the message was originally sent).

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Channel where the message lives |
| **Message Timestamp** | Yes | The `ts` value of the message to update |
| **Text** | Yes* | New text. Required unless Blocks JSON is provided |
| **Blocks JSON** | No | New Block Kit content |

### Example

- **Operation**: Update Message
- **Channel**: `C0123456789`
- **Message Timestamp**: `1234567890.123456`
- **Text**: `Updated: task complete`

---

## 6. Delete Message

Remove a message. Requires the channel and message timestamp.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Channel where the message lives |
| **Message Timestamp** | Yes | The `ts` value of the message to delete |

---

## 7. Read Messages

Fetch recent messages from a channel, or read replies in a thread.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Channel to read from |
| **Limit** | No | Number of messages to return (1-200, default 20) |
| **Thread Timestamp** | No | If provided, reads thread replies instead of channel history |
| **Oldest** | No | Unix timestamp — only messages after this time (Advanced) |
| **Latest** | No | Unix timestamp — only messages before this time (Advanced) |

### Output

Returns an array of messages, each containing:
- `text` — message content
- `user` — user ID of the sender
- `ts` — message timestamp
- `thread_ts` — parent thread timestamp (if in a thread)
- `reply_count` — number of replies (if it's a thread parent)
- `reactions` — emoji reactions on the message
- `blocks` — Block Kit content (if any)

---

## 8. Search Messages

Full-text search across the workspace. **This operation requires a User Token** (`xoxp-...`), not a bot token. Bot tokens do not have access to the `search.messages` API.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Search Query** | Yes | The search query |
| **Slack User Token** | Yes | User token (`xoxp-...`) in the Advanced section |
| **Limit** | No | Results per page (1-100, default 20) |
| **Sort** | No | `score` (relevance) or `timestamp` (Advanced) |
| **Sort Direction** | No | `desc` or `asc` (Advanced) |

### Search Query Modifiers

Slack supports these search modifiers:

| Modifier | Example | Description |
|----------|---------|-------------|
| `in:` | `in:#general` | Search in a specific channel |
| `from:` | `from:@alice` | Messages from a specific user |
| `before:` | `before:2024-01-01` | Messages before a date |
| `after:` | `after:2024-06-01` | Messages after a date |
| `has:` | `has:link` | Messages containing links, reactions, etc. |

### Example

- **Operation**: Search Messages
- **Search Query**: `deployment error in:#engineering after:2024-01-01`
- **Slack User Token**: `xoxp-your-user-token`

---

## 9. Get User

Look up user profiles by ID, email, or list all workspace users.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **User ID** | No* | Slack user ID (`U0123456789`) |
| **Email** | No* | User's email address |
| **List All Users** | No* | Set to `True` to return all workspace users (Advanced) |
| **Limit** | No | Max users when listing all (default 20, max 200) |

*Provide at least one of User ID, Email, or List All Users.

### Output

Returns normalized user profile:
- `id`, `name`, `real_name`, `display_name`
- `email`, `status_text`, `status_emoji`
- `is_bot`, `is_admin`, `team_id`

---

## 10. List Channels

List workspace channels or get detailed info on a specific channel.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | No | Specific channel ID to get info for. Leave empty to list all |
| **Channel Types** | No | Comma-separated: `public_channel`, `private_channel`, `mpim`, `im` (Advanced) |
| **Exclude Archived** | No | Hide archived channels, default `True` (Advanced) |
| **Limit** | No | Max channels to return (default 20, max 200) |

### Output

Returns per channel:
- `id`, `name`, `topic`, `purpose`
- `num_members`, `is_private`, `is_archived`, `is_member`

---

## 11. React

Add, remove, or get emoji reactions on a message.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Channel where the message is |
| **Message Timestamp** | Yes | The `ts` of the message |
| **Emoji** | Yes* | Emoji name without colons (e.g., `thumbsup`, not `:thumbsup:`) |
| **Reaction Action** | No | `add` (default), `remove`, or `get` (Advanced) |

*Emoji is required for `add` and `remove`. Not needed for `get`.

### Example: Add a Reaction

- **Operation**: React
- **Channel**: `C0123456789`
- **Message Timestamp**: `1234567890.123456`
- **Emoji**: `white_check_mark`

### Example: Get All Reactions

- **Operation**: React
- **Reaction Action**: `get`
- **Channel**: `C0123456789`
- **Message Timestamp**: `1234567890.123456`

---

## 12. Upload File

Upload text or code content as a file to a Slack channel.

### Inputs

| Input | Required | Description |
|-------|----------|-------------|
| **Channel** | Yes | Channel to share the file in |
| **Filename** | Yes | Name for the file (e.g., `report.csv`, `script.py`) |
| **File Content** | Yes* | Text content to upload |
| **File Path** | No | Local file path as an alternative to content (canvas mode only, not available in Agent mode) |
| **Initial Comment** | No | Message posted alongside the file (Advanced) |
| **File Title** | No | Display title in Slack (Advanced) |
| **Thread Timestamp** | No | Upload into a specific thread (Advanced) |

*Either File Content or File Path is required.

### Example

- **Operation**: Upload File
- **Channel**: `C0123456789`
- **Filename**: `daily-report.csv`
- **File Content**: `name,status\nAlice,done\nBob,in progress`
- **Initial Comment**: `Here's today's report`

---

## 13. Modals (Open, Update, Push)

Modals are dialog windows triggered by slash commands or interactive elements. These three operations let you create multi-step modal flows.

> **Important:** The `trigger_id` expires in **3 seconds**. The modal must be opened immediately after receiving the Slack event.

### Open Modal

Opens a new modal dialog.

| Input | Required | Description |
|-------|----------|-------------|
| **Trigger ID** | Yes | From a slash command or interactive payload |
| **View JSON** | Yes | Modal definition as a JSON object |

### Update Modal

Updates the content of an already-open modal.

| Input | Required | Description |
|-------|----------|-------------|
| **View ID** | Yes | Returned by the Open Modal operation |
| **View JSON** | Yes | New modal definition |
| **View Hash** | No | For optimistic locking (prevents race conditions) |

### Push Modal

Pushes an additional view onto the modal stack, creating a multi-step wizard.

| Input | Required | Description |
|-------|----------|-------------|
| **Trigger ID** | Yes | From an interactive payload within the current modal |
| **View JSON** | Yes | The new view to push onto the stack |

### Example: Open a Simple Modal

- **Operation**: Open Modal
- **Trigger ID**: (from your slash command handler)
- **View JSON**:
```json
{
  "type": "modal",
  "title": { "type": "plain_text", "text": "Feedback" },
  "submit": { "type": "plain_text", "text": "Submit" },
  "blocks": [
    {
      "type": "input",
      "element": {
        "type": "plain_text_input",
        "action_id": "feedback_input"
      },
      "label": { "type": "plain_text", "text": "Your feedback" }
    }
  ]
}
```

Design modals visually at [Block Kit Builder](https://app.slack.com/block-kit-builder).

---

## 14. Agent / Tool Mode

When you toggle **Tool Mode** on, the Slack component exposes **12 individual tools** that an LLM Agent can call autonomously:

| Tool Name | Description |
|-----------|-------------|
| `slack_send_message` | Send a message to a channel, thread, or DM |
| `slack_update_message` | Edit an existing message |
| `slack_delete_message` | Delete a message |
| `slack_read_history` | Read channel or thread history |
| `slack_search_messages` | Search messages across the workspace |
| `slack_get_user` | Look up user by ID, email, or list all |
| `slack_list_channels` | List channels or get channel info |
| `slack_add_reaction` | Add, remove, or get reactions |
| `slack_upload_file` | Upload content as a file |
| `slack_open_modal` | Open a modal dialog |
| `slack_update_modal` | Update an open modal |
| `slack_push_modal` | Push a view onto the modal stack |

### How to Use

1. Drag the Slack component onto the canvas
2. Configure the **Slack Bot Token** (the Agent won't set this)
3. Toggle **Tool Mode** on in the component header
4. Connect the Tool output to an Agent node's Tool input

The Agent will see all 12 tools with their descriptions and input schemas, and will pick the right one based on the user's request.

### Note on Agent Safety

- The **Operation** dropdown is not exposed to the Agent (`tool_mode=False`). It's only used in canvas mode.
- The **File Path** input is not exposed to the Agent for security reasons — Agents cannot read arbitrary file paths.
- Each tool passes arguments directly to the operation handler to avoid race conditions with concurrent calls.

---

## 15. Channel Resolution

The **Channel** field is flexible. You can pass any of these formats and the component resolves it automatically:

| Format | Example | What Happens |
|--------|---------|-------------|
| Channel ID | `C0123456789` | Used directly |
| Channel name | `#general` or `general` | Resolved to channel ID via `conversations.list` |
| User ID | `U0123456789` | Opens a DM conversation |
| Email | `alice@company.com` | Looks up user by email, then opens a DM |
| DM ID | `D0123456789` | Used directly |
| Group ID | `G0123456789` | Used directly |

---

## 16. Output Format

Every operation returns a `Data` object with a consistent structure:

```json
{
  "success": true,
  "error": null,
  "error_code": null,
  ...operation-specific fields...
}
```

On failure:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "slack_error_code"
}
```

### Key Output Fields by Operation

| Operation | Key Fields |
|-----------|-----------|
| Send Message | `message_ts`, `channel`, `thread_ts` |
| Update Message | `message_ts`, `channel` |
| Delete Message | `message_ts`, `channel` |
| Read Messages | `messages[]`, `has_more`, `next_cursor` |
| Search Messages | `messages[]`, `total`, `has_more` |
| Get User | `user` (single) or `users[]` (list) |
| List Channels | `channel` (single) or `channels[]` (list) |
| React | `action`, `emoji`, `reactions[]` (for get) |
| Upload File | `file_id`, `channel` |
| Open/Push Modal | `view_id`, `external_id` |
| Update Modal | `view_id`, `hash` |

---

## 17. Error Handling

The component provides clear, human-readable error messages. Common errors:

| Error Code | Meaning | Fix |
|-----------|---------|-----|
| `invalid_auth` | Token is invalid or expired | Check your bot token |
| `channel_not_found` | Channel doesn't exist or bot can't access it | Verify channel ID, invite bot to private channels |
| `not_in_channel` | Bot isn't a member of the channel | Invite the bot or use `chat:write.public` for public channels |
| `missing_scope` | Token lacks required OAuth scopes | Add scopes in your Slack app settings and reinstall |
| `message_not_found` | The target message doesn't exist | Verify the `message_ts` value |
| `rate_limited` | Too many API calls | The component auto-retries once; try again later |
| `expired_trigger_id` | Modal trigger expired (3-second limit) | Open the modal immediately after receiving the event |
| `invalid_input` | Missing required fields | Check required inputs for the selected operation |

### Rate Limiting

The component automatically retries once when rate-limited (HTTP 429). It reads the `Retry-After` header from Slack and waits accordingly, capped at 60 seconds. If still rate-limited after the retry, it returns an error.

### Message Truncation

Messages longer than 4,000 characters are automatically truncated with a `[truncated]` suffix. This matches Slack's message length limit.

---

## 18. Common Recipes

### Post a Status Update, Then React to It

1. **Slack node 1**: Send Message to `#status` with your update text
2. Capture `message_ts` from the output
3. **Slack node 2**: React on that `message_ts` with emoji `white_check_mark`

### Read Messages and Forward a Summary

1. **Slack node 1**: Read Messages from `#support` (limit: 50)
2. Pass the `messages` output to an LLM to summarize
3. **Slack node 2**: Send Message to `#support-digest` with the summary

### Look Up a User by Email and DM Them

1. **Slack node 1**: Get User with **Email** = `alice@company.com`
2. Capture the `user.id` from the output
3. **Slack node 2**: Send Message with **Channel** = the user ID

### Upload a Generated Report

1. Generate CSV or text content in a previous node
2. **Slack node**: Upload File with **Filename** = `report.csv`, **File Content** = generated content, **Initial Comment** = `Here's the latest report`

### Agent-Powered Slack Bot

1. Add an Agent node to your flow
2. Drag the Slack component, set the bot token, toggle **Tool Mode** on
3. Connect Slack's Tool output to the Agent's Tool input
4. The Agent can now autonomously send messages, read history, search, react, and more based on user prompts
