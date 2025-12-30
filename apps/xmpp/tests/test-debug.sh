#!/bin/bash

# Comprehensive Docker Setup Test Script
# Tests the entire XMPP server setup including build, deployment, and functionality

set -x

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cleanup() {
    log_info "Cleaning up test environment..."
    docker compose -f docker-compose.dev.yml down -v --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
}

# Test 1: Check prerequisites
test_prerequisites() {
    log_info "Test 1: Checking prerequisites..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_failure "Docker is not running"
        return 1
    fi
    log_success "Docker is running"

    # Check if docker-compose exists
    if ! command -v docker compose >/dev/null 2>&1; then
        log_failure "docker compose command not found"
        return 1
    fi
    log_success "docker compose is available"

    # Check if required files exist
    local required_files=("Dockerfile" "docker-compose.dev.yml" "scripts/setup/entrypoint.sh")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_failure "Required file not found: $file"
            return 1
        fi
    done
    log_success "All required files present"
}

# Test 2: Validate Docker build
test_docker_build() {
    log_info "Test 2: Testing Docker build..."

    # Clean up any existing images
    docker rmi allthingslinux/prosody:dev 2>/dev/null || true

    # Build the image
    if docker build -t allthingslinux/prosody:dev .; then
        log_success "Docker build completed successfully"
    else
        log_failure "Docker build failed"
        return 1
    fi

    # Check if image was created
    if docker images allthingslinux/prosody:dev | grep -q prosody; then
        log_success "Docker image created successfully"
    else
        log_failure "Docker image not found"
        return 1
    fi
}

# Test 3: Test docker-compose up
test_compose_up() {
    log_info "Test 3: Testing docker-compose deployment..."

    # Start services
    if docker compose -f docker-compose.dev.yml up -d; then
        log_success "docker-compose up completed"
    else
        log_failure "docker-compose up failed"
        return 1
    fi

    # Wait for services to be healthy
    log_info "Waiting for services to start..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        local healthy_count=$(docker compose -f docker-compose.dev.yml ps --format json | jq -r '.State' | grep -c "running" 2>/dev/null || echo "0")

        if [[ $healthy_count -ge 3 ]]; then # postgres, prosody, nginx should be running
            log_success "All services started successfully"
            return 0
        fi

        log_info "Waiting... ($attempt/$max_attempts) - $healthy_count services running"
        sleep 2
        ((attempt++))
    done

    log_failure "Services did not start within timeout"
    docker compose -f docker-compose.dev.yml logs
    return 1
}

# Test 4: Test Prosody connectivity
test_prosody_connectivity() {
    log_info "Test 4: Testing Prosody connectivity..."

    # Wait a bit for Prosody to fully start
    sleep 5

    # Test XMPP port
    if docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev nc -z localhost 5222; then
        log_success "XMPP port 5222 is accessible"
    else
        log_failure "XMPP port 5222 is not accessible"
        return 1
    fi

    # Test HTTP port
    if docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev nc -z localhost 5280; then
        log_success "HTTP port 5280 is accessible"
    else
        log_failure "HTTP port 5280 is not accessible"
        return 1
    fi
}

# Test 5: Test web endpoints
test_web_endpoints() {
    log_info "Test 5: Testing web endpoints..."

    # Wait for nginx to be ready
    sleep 3

    # Test nginx dev endpoint
    if curl -s -f http://localhost:8080/dev-test >/dev/null 2>&1; then
        log_success "Nginx dev-test endpoint is working"
    else
        log_failure "Nginx dev-test endpoint failed"
        return 1
    fi

    # Test status endpoint (if available)
    if curl -s -f http://localhost:8080/status >/dev/null 2>&1; then
        log_success "Prosody status endpoint is working"
    elif curl -s -I http://localhost:8080/status 2>/dev/null | head -1 | grep -q "404"; then
        log_warning "Status endpoint returns 404 (module may not be enabled)"
    else
        log_failure "Status endpoint is not accessible"
        return 1
    fi
}

# Test 6: Test module loading
test_module_loading() {
    log_info "Test 6: Testing module loading..."

    # Check if prosody-modules-enabled directory exists and has content
    local enabled_dir="/usr/local/lib/prosody/prosody-modules-enabled"
    local module_count=$(docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev ls "$enabled_dir" 2>/dev/null | wc -l)

    if [[ $module_count -gt 0 ]]; then
        log_success "Found $module_count enabled modules"
    else
        log_warning "No modules found in $enabled_dir (this is OK if no modules are enabled)"
    fi

    # Check Prosody logs for module loading errors
    local error_count=$(docker compose -f docker-compose.dev.yml logs xmpp-prosody-dev 2>/dev/null | grep -c "Unable to load module" || echo "0")

    if [[ $error_count -eq 0 ]]; then
        log_success "No module loading errors found"
    else
        log_failure "Found $error_count module loading errors"
        docker compose -f docker-compose.dev.yml logs xmpp-prosody-dev | grep "Unable to load module"
        return 1
    fi
}

# Test 7: Test configuration
test_configuration() {
    log_info "Test 7: Testing configuration..."

    # Check if Prosody config is valid
    if docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev prosodyctl check config; then
        log_success "Prosody configuration is valid"
    else
        log_failure "Prosody configuration has errors"
        docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev prosodyctl check config
        return 1
    fi

    # Check if required environment variables are set
    local lua_path=$(docker compose -f docker-compose.dev.yml exec xmpp-prosody-dev env | grep LUA_PATH | cut -d'=' -f2)
    if [[ -n "$lua_path" ]] && [[ "$lua_path" == *"/usr/local/lib/prosody/prosody-modules-enabled"* ]]; then
        log_success "LUA_PATH is correctly configured"
    else
        log_failure "LUA_PATH is not correctly configured"
        return 1
    fi
}

# Main test function
main() {
    log_info "🚀 Starting comprehensive Docker setup test"
    echo "=================================================="

    # Set up cleanup on exit
    trap cleanup EXIT

    # Run tests
    test_prerequisites
    test_docker_build
    test_compose_up
    test_prosody_connectivity
    test_web_endpoints
    test_module_loading
    test_configuration

    # Summary
    echo
    echo "=================================================="
    log_info "Test Summary:"
    echo "  ✅ Passed: $TESTS_PASSED"
    echo "  ❌ Failed: $TESTS_FAILED"
    echo "  📊 Total: $((TESTS_PASSED + TESTS_FAILED))"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "🎉 All tests passed! Docker setup is working correctly."
        exit 0
    else
        log_failure "❌ Some tests failed. Please check the output above."
        exit 1
    fi
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
