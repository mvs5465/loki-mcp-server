"""FastMCP server for semantic log querying via Loki."""

import os
import sys
import logging
import signal
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from loki_client import LokiClient
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize MCP server
logger.info("Starting loki-mcp server...")
port = int(os.getenv("PORT", "8000"))
host = os.getenv("HOST", "0.0.0.0")
mcp = FastMCP(
    "loki-mcp",
    host=host,
    port=port,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)

# Initialize Loki client
loki_url = os.getenv("LOKI_URL", "http://loki.monitoring.svc.cluster.local:3100")
logger.info(f"Initializing LokiClient with URL: {loki_url}")
try:
    loki = LokiClient(loki_url)
    logger.info("LokiClient initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LokiClient: {e}", exc_info=True)
    # Continue anyway - tools will fail at call time if needed
    loki = None


@mcp.tool()
def get_error_summary(namespace: str = "", hours: int = 1) -> str:
    """
    Get a summary of errors happening in your cluster.

    Args:
        namespace: Filter to specific namespace (empty = all namespaces)
        hours: Look back this many hours (default: 1)

    Returns:
        Summary of error counts, types, affected pods, and sample errors

    Example: "What errors are happening in my cluster?"
    -> Call with namespace="", hours=1
    """
    if loki is None:
        return "Error: Loki client is not initialized. Check Loki service connectivity."

    result = loki.get_error_summary(namespace=namespace, hours=hours)

    # Format as readable summary
    summary = f"Error Summary (last {hours} hour(s)):\n"
    summary += f"Total Errors: {result['total_errors']}\n"

    if result['error_breakdown']:
        summary += "Error Breakdown:\n"
        for error_type, count in result['error_breakdown'].items():
            summary += f"  {error_type}: {count}\n"

    if result['affected_pods']:
        summary += f"Affected Pods: {', '.join(result['affected_pods'][:10])}\n"

    if result['sample_errors']:
        summary += "Sample Error Messages:\n"
        for msg in result['sample_errors'][:3]:
            summary += f"  - {msg}\n"

    return summary


@mcp.tool()
def find_pod_restarts(namespace: str = "", hours: int = 1) -> str:
    """
    Find pods that have restarted or crashed recently.

    Args:
        namespace: Filter to specific namespace (empty = all namespaces)
        hours: Look back this many hours (default: 1)

    Returns:
        List of pods with restart counts and reasons

    Example: "Which pods are crashing in my cluster?"
    -> Call with namespace="", hours=2
    """
    if loki is None:
        return "Error: Loki client is not initialized. Check Loki service connectivity."

    result = loki.get_pod_restarts(namespace=namespace, hours=hours)

    summary = f"Pod Restart Summary (last {hours} hour(s)):\n"
    summary += f"Total Restart Events: {result['total_restart_events']}\n"

    if result['affected_pods']:
        summary += "Pods with Restarts:\n"
        for pod, count in list(result['affected_pods'].items())[:10]:
            summary += f"  {pod}: {count} events\n"
            if pod in result['restart_reasons']:
                summary += f"    Reason: {result['restart_reasons'][pod][:100]}\n"

    return summary


@mcp.tool()
def search_logs(query: str, namespace: str = "", hours: int = 1, limit: int = 100) -> str:
    """
    Search logs with a regex pattern.

    Args:
        query: Regex pattern to search for
        namespace: Filter to specific namespace (empty = all namespaces)
        hours: Look back this many hours (default: 1)
        limit: Maximum number of log lines to return (default: 100)

    Returns:
        Matching logs grouped by pod

    Example: "Find all logs mentioning 'timeout'"
    -> Call with query="timeout", namespace="", hours=2
    """
    if loki is None:
        return "Error: Loki client is not initialized. Check Loki service connectivity."

    result = loki.search_logs(query=query, namespace=namespace, hours=hours, limit=limit)

    summary = f"Search Results for '{query}' (last {hours} hour(s)):\n"
    summary += f"Total Matches: {result['total_matches']}\n\n"

    for pod, logs in list(result['logs_by_pod'].items())[:5]:
        summary += f"Pod: {pod}\n"
        for log in logs[:3]:
            summary += f"  [{log['timestamp']}] {log['message']}\n"
        summary += "\n"

    return summary


@mcp.tool()
def list_namespaces() -> str:
    """
    List all namespaces that have logs in Loki.

    Returns:
        List of namespace names

    Example: "What namespaces are in my cluster?"
    """
    if loki is None:
        return "Error: Loki client is not initialized. Check Loki service connectivity."

    namespaces = loki.get_namespaces()
    return f"Namespaces with logs:\n" + "\n".join(f"  - {ns}" for ns in namespaces)


@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "", hours: int = 1, limit: int = 100) -> str:
    """
    Get logs for a specific pod.

    Args:
        pod_name: Name of the pod to query
        namespace: Namespace of the pod (empty = search all)
        hours: Look back this many hours (default: 1)
        limit: Maximum log lines to return (default: 100)

    Returns:
        Recent logs from the specified pod

    Example: "Show me logs from the ollama pod"
    -> Call with pod_name="ollama*", namespace="ai", hours=1
    """
    if loki is None:
        return "Error: Loki client is not initialized. Check Loki service connectivity."

    # Build query for specific pod
    if namespace:
        escaped_namespace = loki._escape_logql_string(namespace)
        escaped_pod_name = loki._escape_logql_string(pod_name)
        query = f'{{pod_name=~"{escaped_pod_name}",namespace="{escaped_namespace}"}}'
    else:
        escaped_pod_name = loki._escape_logql_string(pod_name)
        query = f'{{pod_name=~"{escaped_pod_name}"}}'

    start_time = __import__('datetime').datetime.now() - __import__('datetime').timedelta(hours=hours)
    result = loki.query_range(query, start=start_time, limit=limit)
    entries = loki.parse_log_entries(result)

    summary = f"Logs for pod '{pod_name}' (last {hours} hour(s)):\n"
    summary += f"Total Lines: {len(entries)}\n\n"

    for entry in entries[-20:]:  # Show last 20 lines
        summary += f"[{entry['timestamp'].isoformat()}] {entry['message']}\n"

    return summary

# Use the built-in FastMCP ASGI app so the transport matches the installed MCP SDK.
app = mcp.streamable_http_app()


if __name__ == "__main__":
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        logger.info(f"Starting HTTP MCP server on {host}:{port}")
        logger.info(f"MCP endpoint: http://{host}:{port}/mcp")

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
