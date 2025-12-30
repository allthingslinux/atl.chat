#!/bin/bash

# Simple test script for admin interface
# Direct approach - no complex functions

set -euo pipefail

echo "🧪 Simple Admin Interface Test"
echo "=============================="
echo

# Test 1: Basic connectivity
echo "Test 1: Basic HTTP endpoints"
echo "curl -s -I http://localhost:5280/status"
curl -s -I http://localhost:5280/status
echo

echo "curl -s -I http://localhost:8080/status"
curl -s -I http://localhost:8080/status
echo

# Test 2: Admin interface
echo "Test 2: Admin interface"
echo "curl -s -I http://localhost:5280/admin/"
curl -s -I http://localhost:5280/admin/
echo

echo "curl -s -I http://localhost:8080/admin/"
curl -s -I http://localhost:8080/admin/
echo

# Test 3: Check Prosody logs
echo "Test 3: Recent Prosody logs"
docker compose -f docker-compose.dev.yml logs xmpp-prosody-dev --tail=5
