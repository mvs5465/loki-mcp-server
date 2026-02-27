"""Loki API client with log analysis utilities."""

import httpx
from datetime import datetime, timedelta
from typing import Optional, Any
from collections import Counter
import re


class LokiClient:
    def __init__(self, loki_url: str = "http://loki.monitoring.svc.cluster.local:3100"):
        self.url = loki_url
        self.client = httpx.Client(timeout=30.0)

    def query_range(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Execute a LogQL range query."""
        if not start:
            start = datetime.now() - timedelta(hours=1)
        if not end:
            end = datetime.now()

        params = {
            "query": query,
            "start": int(start.timestamp()) * 1_000_000_000,
            "end": int(end.timestamp()) * 1_000_000_000,
            "limit": limit,
        }

        resp = self.client.get(f"{self.url}/loki/api/v1/query_range", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_labels(self, label_name: str) -> list[str]:
        """Get all values for a label."""
        resp = self.client.get(
            f"{self.url}/loki/api/v1/label/{label_name}/values"
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_namespaces(self) -> list[str]:
        """Get all namespaces in logs."""
        return self.get_labels("namespace")

    def get_pods_in_namespace(self, namespace: str) -> list[str]:
        """Get all pods in a namespace."""
        resp = self.client.get(
            f"{self.url}/loki/api/v1/label/pod_name/values",
            params={"query": f'{{namespace="{namespace}"}}'},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def parse_log_entries(self, result: dict) -> list[dict]:
        """Parse Loki response into structured log entries."""
        entries = []
        for stream in result.get("data", {}).get("result", []):
            labels = stream.get("stream", {})
            for timestamp_ns_str, line in stream.get("values", []):
                entries.append({
                    "timestamp": datetime.fromtimestamp(int(timestamp_ns_str) / 1_000_000_000),
                    "message": line,
                    "labels": labels,
                })
        return entries

    def extract_error_level(self, message: str) -> Optional[str]:
        """Extract error level from log message."""
        level_pattern = r"\b(ERROR|WARN|WARNING|PANIC|FATAL|DEBUG|INFO|TRACE)\b"
        match = re.search(level_pattern, message, re.IGNORECASE)
        return match.group(1).upper() if match else None

    def get_error_summary(
        self,
        namespace: str = "",
        hours: int = 1,
    ) -> dict[str, Any]:
        """Get summary of errors in timeframe."""
        start = datetime.now() - timedelta(hours=hours)

        # Build query - include namespace filter if specified
        if namespace:
            query = f'{{namespace="{namespace}"}} |= "ERROR" or |= "PANIC" or |= "FATAL"'
        else:
            query = '|= "ERROR" or |= "PANIC" or |= "FATAL"'

        result = self.query_range(query, start=start, limit=5000)
        entries = self.parse_log_entries(result)

        # Analyze errors
        error_types = Counter()
        error_messages = []
        affected_pods = set()

        for entry in entries:
            msg = entry["message"]
            pod = entry["labels"].get("pod_name", "unknown")
            affected_pods.add(pod)

            # Try to extract error type
            if "ERROR" in msg:
                error_types["ERROR"] += 1
            if "PANIC" in msg:
                error_types["PANIC"] += 1
            if "FATAL" in msg:
                error_types["FATAL"] += 1

            # Store unique error messages (limit to 10)
            if len(error_messages) < 10:
                error_messages.append(msg[:200])  # Truncate long messages

        return {
            "total_errors": len(entries),
            "time_range_hours": hours,
            "error_breakdown": dict(error_types.most_common()),
            "affected_pods": list(affected_pods),
            "sample_errors": error_messages,
            "namespaces": [namespace] if namespace else ["all"],
        }

    def get_pod_restarts(
        self,
        namespace: str = "",
        hours: int = 1,
    ) -> dict[str, Any]:
        """Find pods that have restarted recently."""
        start = datetime.now() - timedelta(hours=hours)

        # Look for restart-related logs
        if namespace:
            query = f'{{namespace="{namespace}"}} |= "restart" or |= "CrashLoopBackOff" or |= "OOMKilled"'
        else:
            query = '|= "restart" or |= "CrashLoopBackOff" or |= "OOMKilled"'

        result = self.query_range(query, start=start, limit=5000)
        entries = self.parse_log_entries(result)

        # Group by pod
        restarts_by_pod = Counter()
        restart_reasons = {}

        for entry in entries:
            pod = entry["labels"].get("pod_name", "unknown")
            restarts_by_pod[pod] += 1
            if pod not in restart_reasons:
                restart_reasons[pod] = entry["message"][:200]

        return {
            "total_restart_events": len(entries),
            "affected_pods": dict(restarts_by_pod.most_common(10)),
            "restart_reasons": restart_reasons,
            "time_range_hours": hours,
        }

    def search_logs(
        self,
        query: str,
        namespace: str = "",
        hours: int = 1,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search logs with a flexible query."""
        start = datetime.now() - timedelta(hours=hours)

        # Build LogQL query
        if namespace:
            logql = f'{{namespace="{namespace}"}} |~ "{query}"'
        else:
            logql = f'|~ "{query}"'

        result = self.query_range(logql, start=start, limit=limit)
        entries = self.parse_log_entries(result)

        # Group by pod
        logs_by_pod = {}
        for entry in entries:
            pod = entry["labels"].get("pod_name", "unknown")
            if pod not in logs_by_pod:
                logs_by_pod[pod] = []
            logs_by_pod[pod].append({
                "timestamp": entry["timestamp"].isoformat(),
                "message": entry["message"][:300],
            })

        return {
            "query": query,
            "total_matches": len(entries),
            "logs_by_pod": logs_by_pod,
            "time_range_hours": hours,
        }
