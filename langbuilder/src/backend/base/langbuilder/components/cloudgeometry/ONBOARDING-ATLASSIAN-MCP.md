# AtlassianMCP Component — Engineer Onboarding

> **TEMPORARY — AWS Fargate MCP Server**
>
> The component default URL points to our AWS deployment:
> ```
> http://mcp-atlassian-alb-1010564853.us-west-2.elb.amazonaws.com
> ```
> - AWS Profile: `ai-entourage`
> - CDK Stack: `McpAtlassianStack` (us-west-2)
> - ECS Cluster: `mcp-atlassian-cluster`
> - Service: `mcp-atlassian` (Fargate, 0.25 vCPU / 512 MB)
> - Service Discovery (VPC-internal): `atlassian.mcp.internal:9000`
>
> This URL will change once we move to a permanent domain.

## What This Is

The AtlassianMCP component connects LangBuilder flows to Jira and Confluence via the [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) MCP server. It exposes 9 tools that an Agent can call: Jira search, get issue, create issue, update issue, transition issue, Confluence search, get page, create page, and update page.

**Key design decision:** The component holds NO shared Atlassian credentials. Each user provides their own email + API token, which are sent per-request as `Authorization: Basic` headers to the MCP server. This is the **per-user auth** model.

## Architecture

```
User (Slack / UI)
    │
    │  tweaks: { slack_user_email, atlassian_email, atlassian_api_token }
    ▼
┌─────────────────────────────────────────────────────┐
│  LangBuilder Flow                                   │
│                                                     │
│  ChatInput → Agent (LLM) → ChatOutput               │
│                  │                                   │
│                  │ calls tools                       │
│                  ▼                                   │
│  ┌─────────────────────────────────┐                │
│  │  AtlassianMCPComponent          │                │
│  │                                 │                │
│  │  1. Receives tool call from LLM │                │
│  │  2. Substitutes email in JQL    │                │
│  │  3. Builds Basic Auth header    │                │
│  │  4. Sends JSON-RPC to MCP       │                │
│  │  5. Returns result to Agent     │                │
│  └──────────────┬──────────────────┘                │
│                 │                                    │
└─────────────────┼────────────────────────────────────┘
                  │  HTTP POST /mcp
                  │  Authorization: Basic <email:token>
                  │  Content-Type: application/json
                  ▼
┌─────────────────────────────────────────────────────┐
│  mcp-atlassian server (ECS Fargate or local Docker) │
│  Port 9000, transport: streamable-http              │
│  Env: ATLASSIAN_OAUTH_ENABLE=true                   │
│       JIRA_URL=https://company.atlassian.net        │
│       CONFLUENCE_URL=https://company.atlassian.net/wiki │
│                                                     │
│  Parses Basic Auth → creates per-user fetcher       │
│  Calls Atlassian REST API with user's credentials   │
└─────────────────────────────────────────────────────┘
```

## Component Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `mcp_endpoint` | str | Yes | MCP server URL. Default `http://localhost:9000`. Production: ALB URL or service discovery endpoint |
| `transport` | dropdown | No | `sse` or `http`. Advanced setting, default `sse` |
| `atlassian_url` | str | No | Base Atlassian URL (e.g., `https://company.atlassian.net`). Sent as `X-Atlassian-Jira-Url` header |
| `atlassian_email` | str | No | User's Atlassian email. Used for Basic Auth |
| `atlassian_api_token` | secret | No | User's API token. Generate at https://id.atlassian.com/manage-profile/security/api-tokens |
| `slack_user_email` | str | No | User's email from Slack bridge. Enables query personalization |
| `slack_user_id` | str | No | Slack user ID. Passed through for downstream context |
| `slack_team_id` | str | No | Slack workspace ID. Passed through for downstream context |
| `tool_name` | dropdown | Yes | Which MCP tool to execute (used in non-Agent mode) |
| `tool_arguments` | str | No | JSON arguments for the tool (used in non-Agent mode) |
| `max_results` | int | No | Default limit for searches. Default 50 |
| `timeout` | int | No | HTTP timeout in seconds. Default 30 |

## Tools Exposed to Agents

When connected to an Agent node, the component exposes 9 LangChain `StructuredTool` instances:

| Tool Name | MCP Tool | Parameters | Description |
|-----------|----------|------------|-------------|
| `atlassian_jira_search` | `jira_search` | `jql` (str), `max_results` (int) | Search Jira issues using JQL |
| `atlassian_jira_get_issue` | `jira_get_issue` | `issue_key` (str) | Get a single issue by key (e.g., EXC-123) |
| `atlassian_jira_create_issue` | `jira_create_issue` | `project_key`, `summary`, `issue_type`, `description` | Create a new Jira issue |
| `atlassian_jira_update_issue` | `jira_update_issue` | `issue_key` (str), `fields` (JSON str) | Update fields on an existing issue |
| `atlassian_jira_transition_issue` | `jira_transition_issue` | `issue_key` (str), `transition_id` (str), `comment` (optional str) | Transition an issue to a new status |
| `atlassian_confluence_search` | `confluence_search` | `cql` (str), `max_results` (int) | Search Confluence using CQL |
| `atlassian_confluence_get_page` | `confluence_get_page` | `page_id` (str) | Get a Confluence page by ID |
| `atlassian_confluence_create_page` | `confluence_create_page` | `space_key`, `title`, `content`, `parent_id` (optional), `content_format` (default "markdown") | Create a new Confluence page |
| `atlassian_confluence_update_page` | `confluence_update_page` | `page_id`, `title`, `content`, `content_format` (default "markdown"), `version_comment` (optional), `is_minor_edit` (bool) | Update an existing Confluence page |

**Tool naming convention:** All tool names are prefixed with `atlassian_` to avoid collisions with other components in the same Agent.

## Per-User Authentication Flow

```
Component                          MCP Server                    Atlassian API
   │                                   │                              │
   │ 1. Build headers:                 │                              │
   │    Authorization: Basic            │                              │
   │    base64(email:token)             │                              │
   │    X-Atlassian-Jira-Url           │                              │
   │                                   │                              │
   │──── POST /mcp (initialize) ──────>│                              │
   │<─── 200 + Mcp-Session-Id ────────│                              │
   │                                   │                              │
   │──── POST /mcp (tools/call) ──────>│                              │
   │     + Mcp-Session-Id              │  2. Parse Basic Auth         │
   │     + Authorization: Basic        │     Extract email + token    │
   │                                   │                              │
   │                                   │──── GET /rest/api/2/search ─>│
   │                                   │     Auth: email:token        │
   │                                   │<─── 200 JSON ───────────────│
   │                                   │                              │
   │<─── 200 SSE: {result} ──────────│                              │
```

The `_get_auth_headers()` method (line 175) builds the per-request headers. If `atlassian_email` and `atlassian_api_token` are empty, it returns an empty dict, falling back to server-side auth (backward compatible with env-var credentials on the server).

## Slack User Context & Email Substitution

The component supports three Slack context fields passed via **tweaks** from a Slack bridge integration (e.g., OpenWebUI Slack bot). These are NOT Slack API credentials — they are identity context.

### How it works

1. **Agent-level context injection** (`build_tool()`, line 583): When `slack_user_email` is set, the tool descriptions include an `IMPORTANT:` block telling the LLM the user's email. This helps the Agent formulate personalized JQL like `assignee = "user@company.com"`.

2. **Component-level substitution** (`_substitute_user_email()`, line 470): Before sending JQL/CQL to the MCP server, the component replaces these placeholders with the actual email:

   | Placeholder | Example |
   |-------------|---------|
   | `{user_email}` | `assignee = {user_email}` → `assignee = "user@company.com"` |
   | `{me}` | `reporter = {me}` → `reporter = "user@company.com"` |
   | `currentUser()` | `assignee = currentUser()` → `assignee = "user@company.com"` |

   This is critical for **service account** deployments where `currentUser()` would resolve to the service account, not the actual user.

3. **Result metadata** (`run_model()`, line 505): Every result includes a `user_context` dict with the Slack IDs for downstream consumers.

### When substitution matters

| Auth Mode | `currentUser()` resolves to | Substitution needed? |
|-----------|----------------------------|---------------------|
| Per-user Basic Auth | The user themselves | No (but doesn't hurt) |
| Shared service account | The service account | **Yes** — without it, "my tickets" returns the service account's tickets |

## MCP Protocol Details

The component communicates with the MCP server using **JSON-RPC 2.0 over HTTP** (streamable-http transport):

1. **Session initialization**: `POST /mcp` with `method: "initialize"` → gets `Mcp-Session-Id` header
2. **Tool calls**: `POST /mcp` with `method: "tools/call"` + `Mcp-Session-Id` header
3. **Tool listing**: `POST /mcp` with `method: "tools/list"` (used for dynamic discovery)

Responses use SSE format (`event: message\ndata: {...}`), parsed in `_call_mcp_tool()` (line 341).

Sessions are cached in the class-level `_mcp_sessions` dict to avoid re-initializing on every tool call.

## MCP Server Deployment

The MCP server runs as a Docker container. Two deployment options:

### Local (development)
```bash
cd /path/to/mcp-atlassian
docker build -t mcp-atlassian .
docker run -p 9000:9000 \
  -e ATLASSIAN_OAUTH_ENABLE=true \
  -e JIRA_URL=https://company.atlassian.net \
  -e CONFLUENCE_URL=https://company.atlassian.net/wiki \
  mcp-atlassian --transport streamable-http --host 0.0.0.0 --port 9000
```

### AWS (production)
Deployed via CDK to ECS Fargate. See `mcp-atlassian/cdk/README.md` for full instructions.

```bash
cd mcp-atlassian/cdk
npm install
npx cdk deploy --profile ai-entourage
```

**Stack outputs:**
- ALB endpoint: `http://mcp-atlassian-alb-XXXXXXXXX.us-west-2.elb.amazonaws.com` (public)
- Service discovery: `atlassian.mcp.internal:9000` (VPC-internal)

**Cost:** ~$13.50/month (Fargate + NAT Gateway + ECR + CloudWatch).

## Running the Flow via API

### With Agent (typical)
```bash
curl -s -u langbuilder:langbuilder \
  "http://localhost:4101/api/v1/run/FLOW_ID?stream=false" \
  -H "Content-Type: application/json" \
  -d '{
    "input_value": "Show me my Jira tickets in project EXC",
    "output_type": "chat",
    "input_type": "chat",
    "tweaks": {
      "AtlassianMCP-XXXXX": {
        "mcp_endpoint": "http://mcp-atlassian-alb-XXXXX.elb.amazonaws.com",
        "atlassian_email": "user@company.com",
        "atlassian_api_token": "ATATT3x...",
        "slack_user_email": "user@company.com"
      },
      "Agent-XXXXX": {
        "api_key": "sk-proj-..."
      }
    }
  }'
```

### Direct MCP test (no LangBuilder)
```bash
# 1. Initialize session
curl -s -D - -X POST "http://ALB_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Basic $(echo -n 'email:token' | base64)" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 2. Call tool (use Mcp-Session-Id from step 1)
curl -s -X POST "http://ALB_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -H "Authorization: Basic $(echo -n 'email:token' | base64)" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"jira_search","arguments":{"jql":"project = EXC ORDER BY created DESC","limit":3}}}'
```

## Key Code Paths

| Method | Line | Purpose |
|--------|------|---------|
| `_get_auth_headers()` | 225 | Builds `Authorization: Basic` + URL headers from component inputs |
| `_get_mcp_url()` | 253 | Returns `{mcp_endpoint}/mcp` |
| `_initialize_mcp_session()` | 263 | JSON-RPC `initialize` → caches `Mcp-Session-Id` |
| `_call_mcp_tool()` | 341 | JSON-RPC `tools/call` with session + auth headers |
| `_list_mcp_tools()` | 421 | JSON-RPC `tools/list` for dynamic tool discovery |
| `_substitute_user_email()` | 470 | Replaces `{user_email}`, `{me}`, `currentUser()` in JQL/CQL |
| `run_model()` | 505 | Main entry: parse args → substitute email → call MCP → return Data |
| `_get_tools()` | 567 | Override to ensure each tool gets its own name (not generic "run_model") |
| `build_tool()` | 583 | Creates 9 LangChain StructuredTool instances for Agent use |

## Parameter Name Mapping

The MCP server uses **snake_case** parameter names. The component maps them correctly:

| Agent sees | Component sends to MCP | Notes |
|------------|----------------------|-------|
| `issue_key` | `issue_key` | |
| `project_key` | `project_key` | |
| `issue_type` | `issue_type` | |
| `cql` (user-facing) | `query` (MCP param name) | |
| `page_id` | `page_id` | |
| `max_results` | `limit` | |
| `fields` (JSON string) | `fields` (dict) | `jira_update_issue` — Agent sends JSON string, component parses to dict |
| `transition_id` | `transition_id` | Numeric string (e.g., "31"), not transition name |
| `content_format` | `content_format` | `"markdown"` (default), `"wiki"`, or `"storage"` |
| `space_key` | `space_key` | For `confluence_create_page` |
| `version_comment` | `version_comment` | Optional, for `confluence_update_page` |
| `is_minor_edit` | `is_minor_edit` | Boolean, for `confluence_update_page` |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Invalid URL 'rest/api/2/myself': No scheme supplied` | MCP server missing `JIRA_URL` env var | Add `JIRA_URL` and `CONFLUENCE_URL` to server environment |
| `Jira global configuration (URL, SSL) is not available from lifespan context` | `get_available_services()` doesn't recognize `ATLASSIAN_OAUTH_ENABLE` when URL is set | Fixed in `environment.py` — add OAuth enable check inside URL blocks |
| `Unknown tool: search` | Wrong tool name — MCP tools are prefixed (e.g., `jira_search`) | Use full tool name from `tools/list` |
| `Unexpected keyword argument: max_results` | MCP server uses `limit`, not `max_results` | Component handles this mapping in `run_model()` |
| Agent uses wrong email / "assigned to me" returns wrong user | `slack_user_email` not set | Pass `slack_user_email` via tweaks |
| `401 Unauthorized` | Bad Atlassian email or expired API token | Regenerate token at https://id.atlassian.com/manage-profile/security/api-tokens |
| `jira_update_issue` validation error on `fields` | Agent sent separate params instead of `fields` dict | The `fields` parameter must be a JSON string, e.g., `'{"summary": "New title"}'` |
| `jira_transition_issue` fails with invalid transition | Wrong `transition_id` for current issue status | Use `jira_get_issue` first to see available transitions. IDs are workflow-dependent. |
| `confluence_create_page` permission error | User lacks create permission in the target space | Try a personal space (e.g., `~ACCOUNT_ID`) or check space permissions |
| Flow node has old code | LangBuilder nodes store embedded code copies | PATCH the flow to update node code, or recreate the node |

## Repository References

| Repo | Purpose |
|------|---------|
| `adubuc-cloudgeometry/mcp-atlassian` | Forked MCP server with per-user Basic Auth support |
| `CloudGeometry/langbuilder` | LangBuilder platform containing this component |
| `sooperset/mcp-atlassian` | Upstream community MCP server (no per-user auth) |
