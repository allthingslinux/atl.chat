# ============================================================================
# ATL Bridge — Discord–IRC–XMPP multi-presence bridge
# ============================================================================
# Stage 1: common     — base image + non-root user + shared env
# Stage 2: build      — install deps with uv, bake VERSION
# Stage 3: production — minimal runtime image
# ============================================================================

# ============================================================================
# STAGE 1: Common
# ============================================================================
FROM python:3.12-slim AS common

LABEL org.opencontainers.image.source="https://github.com/allthingslinux/bridge" \
    org.opencontainers.image.description="ATL Bridge - Discord–IRC–XMPP multi-presence bridge" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.authors="All Things Linux" \
    org.opencontainers.image.vendor="All Things Linux" \
    org.opencontainers.image.title="ATL Bridge" \
    org.opencontainers.image.documentation="https://github.com/allthingslinux/bridge/blob/main/README.md"

RUN groupadd --system --gid 1001 nonroot && \
    useradd --create-home --system --uid 1001 --gid nonroot nonroot

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ============================================================================
# STAGE 2: Build
# ============================================================================
FROM common AS build

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

ARG VERSION=""
ARG GIT_SHA=""
ARG BUILD_DATE=""

RUN set -eux; \
    if [ -n "$VERSION" ]; then \
    echo "$VERSION" > /app/VERSION; \
    else \
    echo "dev" > /app/VERSION; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev

# ============================================================================
# STAGE 3: Production
# ============================================================================
FROM common AS production

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONOPTIMIZE=1

COPY --from=build --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --from=build --chown=nonroot:nonroot /app/src /app/src
COPY --from=build --chown=nonroot:nonroot /app/pyproject.toml /app/pyproject.toml
COPY --from=build --chown=nonroot:nonroot /app/VERSION /app/VERSION

# /app/config.yaml is bind-mounted at runtime; /data for optional persistence
RUN mkdir -p /data && chown nonroot:nonroot /data

USER nonroot

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import bridge; print('ok')" || exit 1

CMD ["bridge", "--config", "/app/config.yaml"]
