#!/bin/bash
# shellcheck shell=bash

# Generate cloak keys via UnrealIRCd container and update .env automatically.
# Run from project root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

cd "$PROJECT_ROOT"

output=$(docker compose -f compose.yaml -p atl-chat run --rm atl-irc-server gencloak 2>/dev/null)
echo "$output"

keys=($(echo "$output" | grep -oE '"[^"]{50,}"' | tr -d '"'))
if [ ${#keys[@]} -ne 3 ]; then
    echo "Failed to parse 3 cloak keys from gencloak output"
    exit 1
fi

[ -f "$ENV_FILE" ] || cp .env.example "$ENV_FILE"

if grep -q '^IRC_CLOAK_KEY_1=' "$ENV_FILE"; then
    sed -i "s|^IRC_CLOAK_KEY_1=.*|IRC_CLOAK_KEY_1=${keys[0]}|" "$ENV_FILE"
    sed -i "s|^IRC_CLOAK_KEY_2=.*|IRC_CLOAK_KEY_2=${keys[1]}|" "$ENV_FILE"
    sed -i "s|^IRC_CLOAK_KEY_3=.*|IRC_CLOAK_KEY_3=${keys[2]}|" "$ENV_FILE"
else
    sed -i "/^IRC_CLOAK_PREFIX=/a\\
# Cloak keys - keep secret; must be identical on all servers. Generate with: just irc gencloak\\
IRC_CLOAK_KEY_1=${keys[0]}\\
IRC_CLOAK_KEY_2=${keys[1]}\\
IRC_CLOAK_KEY_3=${keys[2]}" "$ENV_FILE"
fi

"$SCRIPT_DIR/prepare-config.sh"
echo "Cloak keys updated in .env and config applied."
