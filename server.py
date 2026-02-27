"""FastMCP server for semantic log querying via Loki."""

import os
from mcp.server.fastmcp import FastMCP
from loki_client import LokiClient

# Initialize MCP server
mcp = FastMCP("loki-mcp")
loki = LokiClient(os.getenv("LOKI_URL", "http://loki.monitoring.svc.cluster.local:3100"))


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
    # Build query for specific pod
    if namespace:
        query = f'{{pod_name=~"{pod_name}",namespace="{namespace}"}}'
    else:
        query = f'{{pod_name=~"{pod_name}"}}'

    start_time = __import__('datetime').datetime.now() - __import__('datetime').timedelta(hours=hours)
    result = loki.query_range(query, start=start_time, limit=limit)
    entries = loki.parse_log_entries(result)

    summary = f"Logs for pod '{pod_name}' (last {hours} hour(s)):\n"
    summary += f"Total Lines: {len(entries)}\n\n"

    for entry in entries[-20:]:  # Show last 20 lines
        summary += f"[{entry['timestamp'].isoformat()}] {entry['message']}\n"

    return summary


if __name__ == "__main__":
    mcp.run()
