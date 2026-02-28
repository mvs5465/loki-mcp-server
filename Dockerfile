FROM python:3.11-slim

WORKDIR /app

# Copy dependency metadata first so Docker can cache third-party installs.
COPY pyproject.toml ./

# Install runtime dependencies without copying app code yet.
RUN python - <<'PY' | xargs pip install --no-cache-dir
import tomllib

with open("pyproject.toml", "rb") as f:
    project = tomllib.load(f)["project"]

for dependency in project["dependencies"]:
    print(dependency)
PY

# Copy source after dependencies so code-only changes reuse the cached layer.
COPY loki_client.py server.py ./

# Run FastMCP server
ENTRYPOINT ["python", "server.py"]
