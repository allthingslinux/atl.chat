
# --- 1. Builder stage: Build Prosody and LuaRocks ---
FROM debian:bookworm-slim AS builder

ARG LUAROCKS_VERSION=3.11.1
ARG PROSODY_VERSION=13.0.2

# Set shell options for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    libc6-dev \
    libidn2-dev \
    liblua5.4-dev \
    libsqlite3-dev \
    libssl-dev \
    libicu-dev \
    libmariadb-dev-compat \
    libexpat1-dev \
    libunbound-dev \
    libevent-dev \
    libreadline-dev \
    make \
    unzip \
    lua5.4 \
    lua-bitop \
    lua-dbi-mysql \
    lua-dbi-postgresql \
    lua-expat \
    lua-filesystem \
    lua-socket \
    lua-sec \
    lua-unbound \
    ca-certificates \
    curl \
    dumb-init \
    gosu \
    wget \
    jq \
    mercurial \
    rsync && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Build Prosody
WORKDIR /usr/src
RUN set -x && \
    curl -fsSL -o prosody.tar.gz "https://prosody.im/downloads/source/prosody-${PROSODY_VERSION}.tar.gz" && \
    mkdir -p prosody && \
    tar -xzf prosody.tar.gz -C prosody --strip-components=1 && \
    rm prosody.tar.gz

WORKDIR /usr/src/prosody
RUN ./configure \
    --prefix=/usr/local \
    --sysconfdir=/etc/prosody \
    --datadir=/var/lib/prosody \
    --with-lua=/usr \
    --runwith=lua5.4 \
    --no-example-certs && \
    make -j"$(nproc)" && \
    make install

WORKDIR /usr/src
RUN rm -rf prosody*

# Build LuaRocks
WORKDIR /usr/src/luarocks
RUN curl -fsSL -o luarocks-${LUAROCKS_VERSION}.tar.gz https://luarocks.org/releases/luarocks-${LUAROCKS_VERSION}.tar.gz && \
    tar zxf luarocks-${LUAROCKS_VERSION}.tar.gz && \
    rm luarocks-${LUAROCKS_VERSION}.tar.gz

WORKDIR /usr/src/luarocks/luarocks-${LUAROCKS_VERSION}
RUN ./configure --with-lua=/usr && \
    make bootstrap

WORKDIR /usr/src/luarocks
RUN rm -rf luarocks*

# --- 2. Runtime stage: Minimal image ---
FROM debian:bookworm-slim

# Set shell options for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    lua5.4 \
    lua-bitop \
    lua-dbi-mysql \
    lua-dbi-postgresql \
    lua-dbi-sqlite3 \
    lua-expat \
    lua-filesystem \
    lua-socket \
    lua-sec \
    lua-unbound \
    lua-readline \
    lua-event \
    lua-ldap \
    lua-luaossl \
    liblua5.4-dev \
    libicu72 \
    libidn2-0 \
    ca-certificates \
    curl \
    dumb-init \
    gosu \
    jq \
    rsync \
    wget \
    tar \
    unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Prosody and LuaRocks from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /usr/bin/luarocks* /usr/bin/

# --- User, permissions, and directories ---
RUN groupadd -r prosody && \
    useradd -r -g prosody prosody && \
    mkdir -p /var/lib/prosody /var/lib/prosody/custom_plugins /var/log/prosody /var/run/prosody /certs /etc/prosody/certs && \
    chown -R prosody:prosody /var/lib/prosody /var/log/prosody /var/run/prosody /certs /etc/prosody/certs

# Copy scripts and make executable
COPY --chown=prosody:prosody scripts/setup/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=prosody:prosody scripts/maintenance/health-check.sh /usr/local/bin/health-check.sh

RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/health-check.sh

# Using local cache approach: modules are cloned locally and enabled via symlinks
# Copy both the full repository and the enabled modules directory
COPY prosody-modules /usr/local/lib/prosody/prosody-modules
COPY prosody-modules-enabled /usr/local/lib/prosody/prosody-modules-enabled

# Ensure the directories exist even if cache is not available
RUN mkdir -p /usr/local/lib/prosody/prosody-modules /usr/local/lib/prosody/prosody-modules-enabled

# --- Expose all relevant ports ---
EXPOSE 5222 5223 5269 5270 5280 5281 5347 5000

# --- Healthcheck, volumes, and final setup ---
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 CMD /usr/local/bin/health-check.sh

# Create volumes for persistent data
VOLUME ["/var/lib/prosody", "/var/log/prosody", "/certs"]

# Set Lua paths for modules and C libraries
ENV LUA_PATH="/usr/lib/prosody/?.lua;/usr/lib/prosody/?/init.lua;/usr/local/lib/prosody/?.lua;/usr/local/lib/prosody/?/init.lua;/usr/local/lib/prosody/prosody-modules-enabled/?.lua;/usr/local/lib/prosody/prosody-modules-enabled/?/init.lua;/var/lib/prosody/custom_plugins/?.lua;/var/lib/prosody/custom_plugins/?/init.lua;;" \
    LUA_CPATH="/usr/lib/prosody/?.so;/usr/local/lib/prosody/?.so;;"

WORKDIR /var/lib/prosody

# --- Entrypoint as PID 1 for signal handling ---
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/usr/local/bin/entrypoint.sh"]