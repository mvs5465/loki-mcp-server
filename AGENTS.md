# Loki MCP Server

This repo contains the Loki-backed MCP server plus the Helm chart used by ArgoCD in the local cluster.

## Repo Shape
- `server.py` exposes the FastMCP tools and the HTTP/SSE endpoint at `/mcp`.
- `loki_client.py` contains the Loki API client and log query helpers.
- `chart/` is the deployable Helm chart consumed by ArgoCD from `local-k8s-apps`.
- `.github/workflows/build.yml` builds and pushes the container image to `ghcr.io` on pushes to `main`.

## Working Rules
- Keep the MCP tool names and parameter shapes stable unless you are intentionally changing the client contract.
- If you change ports, env vars, image tags, or chart values, update the matching ArgoCD app definition in `local-k8s-apps/apps/services/loki-mcp-app.yaml`.
- The server expects `LOKI_URL`; `HOST` and `PORT` are optional overrides for local runs.
- Preserve the `/mcp` transport behavior unless you are deliberately changing how the bridge connects.

## Local Development
- Install dependencies with `uv sync`.
- Run locally with `uv run server.py`.
- The repo currently has packaging metadata and dev dependencies in `pyproject.toml`, but no committed test suite yet.

## Deployment Notes
- Merges to `main` can publish a new container image through GitHub Actions.
- The Helm chart is deployed from the repo path `chart`, so chart changes are production-facing once referenced by ArgoCD.
