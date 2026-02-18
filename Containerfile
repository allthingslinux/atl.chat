# ATL Bridge — Discord–IRC–XMPP multi-presence bridge
# Uses uv for fast, reproducible builds

FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY config.example.yaml .
COPY src ./src

# Install (no dev deps)
RUN uv sync --no-dev

# Config mount point (use config.yaml at runtime)
# Data dir for optional persistence
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

# Default: run bridge with config.yaml (bind-mount at runtime)
CMD ["bridge", "--config", "/app/config.yaml"]
