# Integration Guide: Loki MCP + Ollama + Open WebUI

This guide shows how to integrate the Loki MCP server with your existing Ollama + Open WebUI setup for natural language log analysis.

## Prerequisites

- Local k8s cluster with ArgoCD (from local-k8s-argocd)
- Loki deployed in `monitoring` namespace (via prometheus stack)
- Ollama with ollama-mcp-bridge running in `ai` namespace
- Open WebUI at `chat.lan`

## Setup Steps

### 1. Deploy Loki MCP Server

Add to your `local-k8s-apps` values or deploy directly:

```bash
# Option A: Add to local-k8s-apps app values
# In your apps values, add loki-mcp app

# Option B: Deploy standalone
helm install loki-mcp ./chart -n monitoring

# Verify it's running
kubectl get pods -n monitoring | grep loki-mcp
```

### 2. Configure ollama-mcp-bridge

The ollama-mcp-bridge automatically discovers MCP servers. Ensure the bridge can reach Loki MCP:

```bash
# Verify connectivity from ollama-mcp-bridge pod
kubectl exec -it deployment/ollama-mcp-bridge -n ai -- \
  curl http://loki-mcp.monitoring.svc.cluster.local:8000
```

### 3. Set System Prompt in Open WebUI

1. Open `chat.lan`
2. Create a new chat session
3. Go to Settings → System Prompt
4. Copy from `SYSTEM_PROMPT.md`
5. Save

Or use this quick prompt:
```
You are a Kubernetes cluster assistant with access to real-time logs via loki-mcp tools.
When asked about errors, crashes, or logs: use get_error_summary → search_logs → get_pod_logs as needed.
Always summarize findings clearly with affected services and suggested fixes.
```

### 4. Test It Out

Try these questions in Open WebUI:

- "What errors are happening in my cluster?"
- "Why are pods crashing in the AI namespace?"
- "Show me logs mentioning timeout"
- "List all namespaces"
- "Get logs from the ollama pod"

### 5. Monitor Tool Calls

Watch the ollama-mcp-bridge logs to see tool calls:

```bash
kubectl logs -f deployment/ollama-mcp-bridge -n ai
```

You should see tool invocations like:
```
Tool call: get_error_summary(namespace="", hours=1)
Tool result: Error Summary (last 1 hour):...
```

## Troubleshooting

### "No tool found" errors

1. Check Loki MCP pod is running:
   ```bash
   kubectl get pods -n monitoring -l app=loki-mcp
   ```

2. Check bridge can reach it:
   ```bash
   kubectl exec -it deployment/ollama-mcp-bridge -n ai -- \
     curl -v http://loki-mcp.monitoring.svc.cluster.local:8000/mcp
   ```

3. Check bridge logs for connection errors:
   ```bash
   kubectl logs deployment/ollama-mcp-bridge -n ai --tail=50
   ```

### Tools loaded but not called

This is likely a model/prompt issue:
- Try rephrasing the question more explicitly
- Update system prompt with more specific routing
- Try a different model (mistral:7b has better tool calling)

### Slow responses

- Loki might be slow if your cluster generates lots of logs
- Increase the `limit` parameter in tool calls
- Add more specific filters (namespace, time range)

## Customization

Want to add more tools? Edit `server.py` and add new tools following the pattern:

```python
@mcp.tool()
def my_new_tool(param: str) -> str:
    """Tool description shown to model."""
    # Call loki client
    result = loki.search_logs(param)
    # Format for readability
    return formatted_result
```

Then rebuild and redeploy the image.

## Performance Tips

1. **Always specify namespace** when you know it - faster queries
2. **Use short time ranges** - start with 1 hour, expand if needed
3. **Limit results** - the tools default to 100-5000 lines
4. **Cache results** - the model will remember them in conversation

## Next Steps

- Add more specialized tools (specific error types, performance metrics)
- Integrate with Prometheus MCP for correlated metrics + logs
- Add alerting/runbook suggestions based on errors found
