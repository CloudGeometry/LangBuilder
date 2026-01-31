# Atlassian MCP — User Tutorial

## What You Can Do

The Atlassian MCP component lets you talk to Jira and Confluence from inside a LangBuilder flow. Connect it to an Agent, and the Agent can:

- **Search Jira issues** — "Find all open bugs in project EXC"
- **Get issue details** — "Show me EXC-914"
- **Create issues** — "Create a Task in EXC called 'Fix login page'"
- **Update issues** — "Change the description of EXC-914"
- **Transition issues** — "Move EXC-914 to In Progress"
- **Search Confluence** — "Find pages about onboarding in the HR space"
- **Read Confluence pages** — "Get the content of page 12345"
- **Create Confluence pages** — "Create a page in the ENG space called 'Release Notes'"
- **Update Confluence pages** — "Update page 12345 with the new content"

You ask in plain English. The Agent translates your request into the right Jira/Confluence query and returns the results.

---

## Quick Start

### Step 1: Get Your Atlassian API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a label (e.g., "LangBuilder")
4. Copy the token — you won't see it again

### Step 2: Build a Flow

Open LangBuilder and create a new flow with these 3 nodes:

```
Chat Input  →  Agent  →  Chat Output
                 │
                 └── Atlassian MCP (tool)
```

1. Drag a **Chat Input** node onto the canvas
2. Drag an **Agent** node and connect Chat Input to it
3. Drag a **Chat Output** node and connect the Agent to it
4. In the sidebar under **Cloud Geometry**, find **Atlassian MCP** and drag it onto the canvas
5. Connect the Atlassian MCP node's tool output to the Agent's **Tools** input

### Step 3: Configure the Atlassian MCP Node

Click on the Atlassian MCP node and fill in:

| Field | What to Enter |
|-------|---------------|
| **MCP Server URL** | Leave the default (pre-configured to Cloud Geometry's server) |
| **Atlassian Email** | Your Atlassian account email (e.g., `you@cloudgeometry.com`) |
| **Atlassian API Token** | The token you created in Step 1 |

That's it. The other fields are optional.

### Step 4: Configure the Agent Node

Click on the Agent node:
- Set the **Model** (e.g., `gpt-4o-mini`)
- Paste your **OpenAI API Key** (or select another LLM provider)

### Step 5: Test It

Click the **Playground** button (bottom right) and try:

```
Show me the 5 most recent issues in project EXC
```

The Agent will call the Jira search tool and return formatted results.

---

## Example Prompts

### Jira

| What you say | What happens |
|--------------|-------------|
| "Find all open bugs in project EXC" | Searches with JQL: `project = EXC AND type = Bug AND status != Done` |
| "Show me EXC-914" | Fetches full details for that issue |
| "What issues are assigned to me?" | Searches with `assignee = currentUser()` (requires Slack email — see below) |
| "Create a Task in EXC called 'Update docs'" | Creates a new Jira issue |
| "Find critical issues updated this week" | Searches: `priority = Critical AND updated >= -7d` |
| "Change the description of EXC-914 to 'Updated scope'" | Updates the issue's description field |
| "Move EXC-914 to In Progress" | Transitions the issue to a new status |
| "Assign EXC-914 to alice@company.com" | Updates the assignee field |

### Confluence

| What you say | What happens |
|--------------|-------------|
| "Search for pages about 'release process'" | CQL search across all spaces |
| "Find pages in the ENG space" | CQL: `space = ENG AND type = page` |
| "Get the content of page 12345" | Fetches full page content by ID |
| "Create a page in ENG called 'Sprint 42 Retro'" | Creates a new Confluence page in the ENG space |
| "Update page 12345 with the new meeting notes" | Updates an existing page's content |

---

## "My Tickets" — Personalized Queries

When someone says "my tickets" or "assigned to me", the Agent needs to know who "me" is. There are two ways this works:

### Option A: Slack Integration (Automatic)

If you're chatting through a Slack bot connected to LangBuilder, your email is passed automatically. The Agent knows who you are and "my tickets" just works.

### Option B: Manual Setup

If you're using the LangBuilder UI directly, fill in the **Slack User Email** field (under Advanced settings) with your Atlassian email. This tells the Agent your identity.

Once configured, you can say:
- "Show me my open tickets"
- "What bugs did I create this month?"
- "Find issues I'm watching in project EXC"

The component replaces `currentUser()`, `{me}`, and `{user_email}` in queries with your actual email address.

---

## Advanced: Using Tweaks via API

If you're calling the flow via the LangBuilder API (not the UI), pass credentials as tweaks:

```bash
curl -u langbuilder:langbuilder \
  "http://localhost:4101/api/v1/run/YOUR_FLOW_ID?stream=false" \
  -H "Content-Type: application/json" \
  -d '{
    "input_value": "Show me my tickets in EXC",
    "output_type": "chat",
    "input_type": "chat",
    "tweaks": {
      "AtlassianMCP-XXXXX": {
        "atlassian_email": "you@company.com",
        "atlassian_api_token": "ATATT3x...",
        "slack_user_email": "you@company.com"
      },
      "Agent-XXXXX": {
        "api_key": "sk-proj-..."
      }
    }
  }'
```

Replace `AtlassianMCP-XXXXX` and `Agent-XXXXX` with the actual node IDs from your flow. You can find them by opening the flow in the UI and clicking on each node.

---

## Configuration Reference

### Required Fields

| Field | Description |
|-------|-------------|
| **MCP Server URL** | URL of the Atlassian MCP server. Default is pre-configured. |
| **Atlassian Email** | Your Atlassian account email address |
| **Atlassian API Token** | Your personal API token from https://id.atlassian.com/manage-profile/security/api-tokens |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Atlassian URL** | Your Atlassian instance URL (e.g., `https://yourcompany.atlassian.net`). Only needed if the server doesn't have it pre-configured. |
| **Slack User Email** | Your email for personalized "my tickets" queries. Filled automatically when using Slack integration. |
| **Slack User ID** | Your Slack user ID. Filled automatically by Slack bridge. |
| **Slack Team ID** | Your Slack workspace ID. Filled automatically by Slack bridge. |
| **Max Results** | Maximum search results to return (default: 50) |
| **Timeout** | Request timeout in seconds (default: 30) |
| **Transport** | MCP transport type. Leave as default. |

---

## Available Tools

The component gives the Agent these 9 tools:

### Jira Tools

#### 1. Jira Search (`atlassian_jira_search`)

Search for issues using JQL (Jira Query Language). The Agent writes the JQL for you based on your natural language request.

**Common JQL patterns the Agent uses:**
- `project = KEY` — Issues in a project
- `assignee = "email"` — Issues assigned to someone
- `reporter = "email"` — Issues created by someone
- `status = "In Progress"` — Issues by status
- `type = Bug` — Issues by type
- `priority = Critical` — Issues by priority
- `created >= -7d` — Recent issues
- `labels = "frontend"` — Issues with a label

#### 2. Jira Get Issue (`atlassian_jira_get_issue`)

Get full details of a single issue by its key (e.g., `EXC-914`). Returns summary, description, status, assignee, comments, and more.

#### 3. Jira Create Issue (`atlassian_jira_create_issue`)

Create a new issue. You need to specify at minimum:
- **Project** (e.g., EXC)
- **Summary** (the title)
- **Type** (Task, Bug, Story — defaults to Task)

Example: "Create a Bug in EXC called 'Login button not working' with description 'The login button on the landing page returns a 500 error'"

#### 4. Jira Update Issue (`atlassian_jira_update_issue`)

Update fields on an existing issue. The Agent sends a JSON object with the fields to change — only the specified fields are updated, everything else stays the same.

**Fields you can update:**
- `summary` — The issue title
- `description` — The issue description
- `assignee` — Email address of the new assignee
- `priority` — Priority name (e.g., "Critical", "Major", "Minor")
- Any other standard or custom Jira field

Example: "Change the priority of EXC-914 to Critical and update the description"

#### 5. Jira Transition Issue (`atlassian_jira_transition_issue`)

Move an issue to a different status (e.g., "To Do" to "In Progress" to "Done"). The Agent uses the issue's available transitions — these depend on your Jira workflow configuration.

The Agent will first check the issue to see which transitions are available, then apply the right one. You can also add a comment during the transition.

Example: "Move EXC-914 to Done with a comment 'Completed in sprint 42'"

### Confluence Tools

#### 6. Confluence Search (`atlassian_confluence_search`)

Search Confluence pages using CQL (Confluence Query Language).

**Common CQL patterns:**
- `space = KEY` — Pages in a space
- `type = page` — Only pages (not blog posts)
- `title ~ "keyword"` — Title contains a word
- `text ~ "keyword"` — Content contains a word
- `creator = "email"` — Pages by author

#### 7. Confluence Get Page (`atlassian_confluence_get_page`)

Get the full content of a Confluence page by its page ID.

#### 8. Confluence Create Page (`atlassian_confluence_create_page`)

Create a new page in a Confluence space. You specify:
- **Space** — The space key (e.g., ENG, DEV)
- **Title** — The page title
- **Content** — Page content in markdown (default), wiki markup, or Confluence storage format

You can optionally create it as a child of an existing page by providing a parent page ID.

Example: "Create a page in the ENG space called 'Sprint 42 Retro' with a summary of action items"

#### 9. Confluence Update Page (`atlassian_confluence_update_page`)

Update the content of an existing Confluence page. You provide:
- **Page ID** — The numeric ID of the page to update
- **Title** — The page title (required even if unchanged)
- **Content** — The new page content in markdown (default) or other format

You can optionally add a version comment and mark it as a minor edit.

Example: "Update page 12345 with the new release notes and add a version comment 'Added v2.1 notes'"

---

## Troubleshooting

### "Authentication error" or "401 Unauthorized"

- Double-check your **Atlassian Email** matches your Atlassian account exactly
- Regenerate your **API Token** — they can expire or get revoked
- Make sure you're using an API token, not your Atlassian password

### "MCP initialization failed" or timeout errors

- The MCP server may be down. Check with your team.
- Try increasing the **Timeout** setting (e.g., 60 seconds)

### Agent doesn't call the right tool

- Be specific in your prompt. Instead of "check Jira", say "Search Jira for open bugs in project EXC"
- The Agent has access to Jira and Confluence tools — specify which one you mean

### "My tickets" returns nothing or wrong results

- Make sure **Slack User Email** is set (under Advanced) to your Atlassian email
- Or be explicit: "Find EXC issues assigned to you@company.com"

### Created issue is missing fields

- The create tool supports: project, summary, type, and description
- For other fields (priority, labels, sprint), use the update tool: "Set the priority of EXC-123 to Critical"

### Transition fails or says "invalid transition"

- Available transitions depend on your Jira workflow and the issue's current status
- The Agent will check available transitions automatically — just say what status you want (e.g., "Move to Done")
- If the transition still fails, the issue may be in a status that doesn't allow that move in your workflow

### Confluence page creation fails with permission error

- You may not have create permission in the target space
- Try a different space, or ask your Confluence admin to grant you the right permissions
- Personal spaces (e.g., your own space) typically allow page creation

---

## Security Notes

- Your API token is sent directly from your browser/client to the MCP server. It is **not stored** on the server.
- Each request includes your credentials. The server processes them and forgets them.
- Never share your API token. If compromised, revoke it immediately at https://id.atlassian.com/manage-profile/security/api-tokens and create a new one.
- The MCP server only has access to what your Atlassian account can access. It cannot see projects or pages you don't have permission for.
