# Loki MCP Server

An MCP (Model Context Protocol) server for semantic log querying via Loki. Designed to help AI models answer natural language questions about your cluster logs.

## Features

- **Error Summary**: Aggregate errors across your cluster with breakdowns by type
- **Pod Restart Detection**: Find crashing/restarting pods
- **Log Search**: Regex-based log search across your cluster
- **Namespace/Pod Discovery**: List available namespaces and query specific pods
- **Semantic Tool Design**: Tool names and parameters match natural language questions

## Tools

### `get_error_summary`
Get a summary of errors happening in your cluster.
- `namespace`: Filter to specific namespace (empty = all)
- `hours`: Look back this many hours (default: 1)

### `find_pod_restarts`
Find pods that have restarted or crashed recently.
- `namespace`: Filter to specific namespace (empty = all)
- `hours`: Look back this many hours (default: 1)

### `search_logs`
Search logs with a regex pattern.
- `query`: Regex pattern to search for
- `namespace`: Filter to specific namespace (empty = all)
- `hours`: Look back this many hours (default: 1)
- `limit`: Maximum log lines to return (default: 100)

### `list_namespaces`
List all namespaces that have logs in Loki.

### `get_pod_logs`
Get logs for a specific pod.
- `pod_name`: Pod name (supports wildcards like `ollama*`)
- `namespace`: Namespace of the pod (empty = search all)
- `hours`: Look back this many hours (default: 1)
- `limit`: Maximum log lines to return (default: 100)

## Development

```bash
# Install dependencies
uv sync

# Run the server
uv run server.py
```

The server exposes FastMCP over streamable HTTP at `/mcp` (default port `8000`).

## Deployment (In-Cluster)

Add to your local-k8s-apps Helm values with:
- Deployment with the MCP server
- Exposed via HTTP on port 8000
- Environment variable: `LOKI_URL` pointing to Loki service

The Ollama MCP bridge will load this server's tools and expose them to the model.
