# Loki MCP Server

This repo contains the Loki-backed MCP server plus the Helm chart used by ArgoCD in the local cluster.

## Repo Shape
- `server.py` exposes the FastMCP tools and the HTTP/SSE endpoint at `/mcp`
- `loki_client.py` contains the Loki API client and query helpers
- `chart/` is the deployable Helm chart consumed by ArgoCD from `local-k8s-apps`
- `.github/workflows/build.yml` builds and pushes the container image to `ghcr.io` on pushes to `main`

## Working Rules
- Keep MCP tool names, parameter shapes, and returned field names stable unless you are intentionally changing the client contract.
- Preserve the `/mcp` transport behavior unless you are deliberately changing how the bridge connects.
- If you change ports, env vars, image tags, or chart values, update the matching ArgoCD app in `local-k8s-apps/apps/services/loki-mcp-app.yaml`.
- The server expects `LOKI_URL`; `HOST` and `PORT` are optional local overrides.

## Local Development
- Install dependencies with `uv sync`
- Run locally with `uv run server.py`
- If you need a quick syntax check, use `uv run python -m py_compile server.py loki_client.py`
- The repo currently has packaging metadata and dev dependencies in `pyproject.toml`, but no committed test suite yet

## Helm And Releases
- If a PR changes anything under `chart/`, bump `chart/Chart.yaml` `version` in the same PR.
- Bump `appVersion` when the deployed application behavior materially changes.
- Merges to `main` can publish a new container image through GitHub Actions.

## Deployment Notes
- The Helm chart is deployed from repo path `chart`, so chart changes are production-facing once referenced by ArgoCD.
- Keep chart defaults aligned with the single-purpose MCP server design; avoid turning the chart into a generic kitchen sink.
