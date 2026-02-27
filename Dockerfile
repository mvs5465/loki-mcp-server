FROM python:3.11-slim

WORKDIR /app

# Copy source and metadata
COPY pyproject.toml loki_client.py server.py ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run FastMCP server
ENTRYPOINT ["python", "server.py"]
