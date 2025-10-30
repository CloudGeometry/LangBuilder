# OpenWebUI API Integration

This guide explains how to expose LangBuilder flows through the built-in OpenAI-compatible shim so they can be used directly inside [Open WebUI](https://github.com/open-webui/open-webui).

## Prerequisites

- LangBuilder running locally (for example `make backend` or `langbuilder run`)
- Open WebUI `v0.6.34` or newer
- A LangBuilder API key (create one under **Settings → API Keys**)

## 1. Start LangBuilder

```bash
make init     # one-time dependency install
make backend  # FastAPI + shim on http://127.0.0.1:7860
```

Optionally run the Vite dev UI in another terminal with `make frontend`.

## 2. Prepare a flow

1. Open the LangBuilder UI.
2. Create or open the flow you want to expose.
3. Choose **Share ▾ → API access** and set an **Endpoint Name** (for example `support-bot`). The shim will expose it as `lb:<endpoint-name>`.
4. (Optional) If other users will call it with their own API keys, set the flow access to **PUBLIC** in **Share ▾ → Flow settings**.

Verify the shim by listing models:

```bash
curl -H "Authorization: Bearer <LANGBUILDER_API_KEY>" \
     http://127.0.0.1:7860/v1/models
```

Your flow should appear as `lb:<endpoint-name>` (or `lb:<flow-id>` if no endpoint name is defined).

## 3. Run Open WebUI against LangBuilder

```bash
docker run -d --name openwebui \
  -p 8000:8080 \
  -v open-webui:/app/backend/data \
  -e WEBUI_AUTH=False \
  -e OPENAI_API_BASE_URL="http://<langbuilder-host>:7860/v1" \
  -e OPENAI_API_KEY="<LANGBUILDER_API_KEY>" \
  -e WEBUI_URL="http://localhost:8000" \
  --restart always \
  ghcr.io/open-webui/open-webui:v0.6.34
```

Replace `<langbuilder-host>` with:

- `host.docker.internal` on macOS or Windows (Docker Desktop).
- The LAN IP of your LangBuilder machine on Linux (for example `192.168.x.x`). You can discover it with `hostname -I`.

After the container starts:

1. Open `http://localhost:8000`.
2. Go to **Admin Settings → Connections → OpenAI** and verify the connection using the same base URL and API key.
3. Models returned by `/v1/models` appear automatically and are prefixed with `lb:`. Select the desired `lb:` entry in the chat sidebar and start chatting—LangBuilder will run the corresponding flow.

## Troubleshooting

- **401 Unauthorized** – Ensure you are using a LangBuilder API key and the base URL ends with `/v1`.
- **No models listed** – Confirm the flow has an endpoint name and the `curl /v1/models` check returns it.
- **Empty responses** – The shim responds with non-streaming completions but gracefully ignores `stream=true`; refresh LangBuilder to ensure you have the latest build.
- **Docker networking** – Use the appropriate host when setting `OPENAI_API_BASE_URL`; Linux containers cannot resolve `host.docker.internal`.

Once configured, any new flow with an endpoint name automatically appears as a selectable model in Open WebUI. Remove or rename flows in LangBuilder to control availability.
