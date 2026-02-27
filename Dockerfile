FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source
COPY loki_client.py server.py ./

# Run MCP server via stdio
ENTRYPOINT ["python", "-m", "mcp.server.stdio"]
