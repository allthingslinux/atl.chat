#!/bin/bash

# Simple test script for admin interface
# Direct approach - no complex functions
# Run from repo root or apps/xmpp; uses compose.yaml from apps/xmpp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XMPP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$XMPP_ROOT/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/compose.yaml"

echo "🧪 Simple Admin Interface Test"
echo "=============================="
echo

# Test 1: Basic connectivity (Prosody HTTP on 5280)
echo "Test 1: Basic HTTP endpoints"
echo "curl -s -I http://localhost:5280/status"
curl -s -I http://localhost:5280/status
echo

# Test 2: Admin interface
echo "Test 2: Admin interface"
echo "curl -s -I http://localhost:5280/admin/"
curl -s -I http://localhost:5280/admin/
echo

# Test 3: Check Prosody logs
echo "Test 3: Recent Prosody logs"
(cd "$REPO_ROOT" && docker compose -f "$COMPOSE_FILE" logs atl-xmpp-server --tail=5)
