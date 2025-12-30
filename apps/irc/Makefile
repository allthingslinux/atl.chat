.PHONY: help build rebuild up down restart status logs logs-ircd logs-atheme logs-webpanel dev-shell dev-logs test test-unit test-integration test-e2e test-protocol test-performance test-services test-env test-irc test-docker test-quick lint clean reset info ssl-setup ssl-status ssl-renew ssl-logs ssl-stop ssl-clean generate-password modules-list modules-installed webpanel stop

# Default target - comprehensive help
help:
	@echo "IRC.atl.chat - Docker IRC Server"
	@echo "==============================="
	@echo ""
	@echo "🚀 ONE COMMAND SETUP (Recommended):"
	@echo "  make up             - Complete automated setup and start"
	@echo "  make down           - Stop all services"
	@echo ""
	@echo "✅ What 'make up' does automatically:"
	@echo "  • Creates all required directories"
	@echo "  • Sets up proper permissions (works on any system)"
	@echo "  • Processes configuration templates"
	@echo "  • Builds containers"
	@echo "  • Starts all services"
	@echo "  • Ensures host can read log files"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make status         - Check service status"
	@echo "  make logs           - View all logs"
	@echo "  make logs-ircd      - View UnrealIRCd logs"
	@echo ""
	@echo "🔧 TROUBLESHOOTING:"
	@echo "  make restart        - Restart all services"
	@echo "  make rebuild        - Rebuild containers from scratch"
	@echo ""
	@echo "🧪 TESTING:"
	@echo "  make test           - Run comprehensive test suite"
	@echo "  make test-unit      - Run fast unit tests (no Docker)"
	@echo "  make test-integration - Run integration tests (requires Docker)"
	@echo "  make test-e2e       - Run end-to-end tests (requires Docker)"
	@echo "  make test-protocol  - Run IRC protocol tests (integration)"
	@echo "  make test-performance - Run performance tests (marker-based)"
	@echo "  make test-services  - Run Atheme service tests"
	@echo "  make test-env       - Test environment setup only"
	@echo "  make test-irc       - Test IRC functionality only"
	@echo "  make test-docker    - Run Docker-related tests"
	@echo "  make test-quick     - Quick environment check"
	@echo ""
	@echo "⚙️ ADVANCED OPTIONS:"
	@echo "  make setup          - Setup only (no start)"
	@echo "  make start-only     - Start only (assumes setup done)"
	@echo "  make quick-start    - Alias for 'make up'"
	@echo ""
	@echo "🔐 SSL MANAGEMENT:"
	@echo "  make ssl-setup      - Setup SSL certificates"
	@echo "  make ssl-status     - Check SSL status"
	@echo ""
	@echo "🗂️ ACCESS POINTS:"
	@echo "  📡 IRC:      localhost:6697 (TLS only)"
	@echo "  🌐 WebPanel: http://localhost:8080"
	@echo "  📝 Logs:     tail -f logs/unrealircd/ircd.log"
	@echo "  📋 JSON:     tail -f logs/unrealircd/ircd.json.log"

# Configuration
DOCKER_COMPOSE := docker compose
DOCKER := docker
SHELL := /bin/bash

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
NC := \033[0m # No Color

# ============================================================================
# BUILDING COMMANDS
# ============================================================================

# Building operations
build:
	@echo -e "$(PURPLE)=== Building Services ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Building IRC services..."
	$(DOCKER_COMPOSE) build $(if $(NO_CACHE),--no-cache)
	@echo -e "$(GREEN)[SUCCESS]$(NC) All services built successfully!"

rebuild:
	@echo -e "$(PURPLE)=== Rebuilding Services (No Cache) ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Rebuilding IRC services without cache..."
	$(DOCKER_COMPOSE) build --no-cache
	@echo -e "$(GREEN)[SUCCESS]$(NC) All services rebuilt successfully!"

# ============================================================================
# SERVICE MANAGEMENT COMMANDS
# ============================================================================

# Service operations
up:
	@echo -e "$(PURPLE)=== Starting IRC.atl.chat ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running comprehensive setup and permission handling..."
	@./scripts/init.sh
	@./scripts/prepare-config.sh
	@docker compose up -d
	@echo -e "$(GREEN)[SUCCESS]$(NC) Services started!"
	@echo -e "$(BLUE)[INFO]$(NC) IRC Server: localhost:6697 (TLS only)"
	@echo -e "$(BLUE)[INFO]$(NC) WebPanel: http://localhost:8080"
	@echo -e "$(BLUE)[INFO]$(NC) Log files accessible at: logs/unrealircd/"

# Setup only (no start)
setup:
	@echo -e "$(PURPLE)=== Setup Only ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running setup without starting services..."
	@./scripts/init.sh
	@./scripts/prepare-config.sh
	@docker compose up -d
	@echo -e "$(GREEN)[SUCCESS]$(NC) Setup completed! Use 'make start-only' to start services."

# Start services only (assumes setup is done)
start-only:
	@echo -e "$(PURPLE)=== Starting Services Only ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Starting services (assuming setup is complete)..."
	$(DOCKER_COMPOSE) up -d
	@echo -e "$(GREEN)[SUCCESS]$(NC) Services started!"

down:
	@echo -e "$(PURPLE)=== Stopping Services ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Stopping all services..."
	$(DOCKER_COMPOSE) down
	@echo -e "$(GREEN)[SUCCESS]$(NC) All services stopped and removed."


restart:
	@echo -e "$(PURPLE)=== Restarting Services ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Restarting all services..."
	$(DOCKER_COMPOSE) restart
	@echo -e "$(GREEN)[SUCCESS]$(NC) Services restarted successfully!"

# Status and monitoring
status:
	@echo -e "$(PURPLE)=== Service Status ===$(NC)"
	$(DOCKER_COMPOSE) ps
	@echo ""
	@echo -e "$(BLUE)[INFO]$(NC) Health checks:"
	$(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

logs:
	@echo -e "$(PURPLE)=== Service Logs ===$(NC)"
	$(DOCKER_COMPOSE) logs -f

logs-ircd:
	@echo -e "$(PURPLE)=== UnrealIRCd Logs ===$(NC)"
	$(DOCKER_COMPOSE) logs -f unrealircd

logs-atheme:
	@echo -e "$(PURPLE)=== Atheme Logs ===$(NC)"
	$(DOCKER_COMPOSE) logs -f atheme

logs-webpanel:
	@echo -e "$(PURPLE)=== WebPanel Logs ===$(NC)"
	$(DOCKER_COMPOSE) logs -f unrealircd-webpanel

# ============================================================================
# MODULE MANAGEMENT (Advanced)
# ============================================================================

modules-list:
	@echo -e "$(PURPLE)=== Available Modules ===$(NC)"
	$(DOCKER_COMPOSE) exec unrealircd manage-modules.sh list

modules-installed:
	@echo -e "$(PURPLE)=== Installed Modules ===$(NC)"
	$(DOCKER_COMPOSE) exec unrealircd manage-modules.sh installed

# ============================================================================
# WEBPANEL COMMANDS
# ============================================================================

webpanel:
	@echo -e "$(PURPLE)=== WebPanel Access ===$(NC)"
	@echo "WebPanel URL: http://localhost:8080"
	@echo "IRC Server: localhost:6697 (TLS only)"
	@echo ""
	@echo "To access webpanel:"
	@echo "  1. Start services: make up"
	@echo "  2. Open browser: http://localhost:8080"

# ============================================================================
# DEVELOPMENT COMMANDS
# ============================================================================

dev-shell:
	@echo -e "$(PURPLE)=== Development Shell ===$(NC)"
	$(DOCKER_COMPOSE) exec ircd bash

dev-logs:
	@echo -e "$(PURPLE)=== All Logs with Timestamps ===$(NC)"
	$(DOCKER_COMPOSE) logs -f --timestamps

# Testing and validation
test:
	@echo -e "$(PURPLE)=== Running Comprehensive Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running test suite with uv..."
	@uv run pytest tests/
	@echo -e "$(GREEN)[SUCCESS]$(NC) Test suite completed!"

test-env:
	@echo -e "$(PURPLE)=== Environment Validation Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Validating environment setup, permissions, and configuration..."
	@uv run pytest tests/unit/test_environment_validation.py tests/unit/test_docker_client.py -v

test-irc:
	@echo -e "$(PURPLE)=== IRC Functionality Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Testing IRC server functionality..."
	@uv run pytest tests/integration/test_irc_functionality.py tests/integration/test_protocol.py -v

test-unit:
	@echo -e "$(PURPLE)=== Unit Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running pure unit tests (no Docker required)..."
	@uv run pytest tests/unit/ -v

test-integration:
	@echo -e "$(PURPLE)=== Integration Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running integration tests..."
	@uv run pytest tests/integration/ -v

test-e2e:
	@echo -e "$(PURPLE)=== End-to-End Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running end-to-end tests..."
	@uv run pytest tests/e2e/ -v

test-protocol:
	@echo -e "$(PURPLE)=== Protocol Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running IRC protocol tests..."
	@uv run pytest tests/protocol/ -v

test-performance:
	@echo -e "$(PURPLE)=== Performance Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running performance tests..."
	@uv run pytest -m performance -v

test-services:
	@echo -e "$(PURPLE)=== Service Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running Atheme service integration tests..."
	@uv run pytest -m atheme -v


test-docker:
	@echo -e "$(PURPLE)=== Docker-related Tests ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Running tests that require Docker..."
	@uv run pytest -m docker -v

test-quick:
	@echo -e "$(PURPLE)=== Quick Environment Check ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Checking Docker Compose configuration..."
	$(DOCKER_COMPOSE) config --quiet
	@echo -e "$(GREEN)[SUCCESS]$(NC) Docker Compose configuration is valid!"
	@echo -e "$(BLUE)[INFO]$(NC) Checking service health..."
	@if $(DOCKER_COMPOSE) ps | grep -q "Up"; then \
		echo -e "$(GREEN)[SUCCESS]$(NC) Services are running!"; \
	else \
		echo -e "$(YELLOW)[WARNING]$(NC) No services are currently running."; \
		echo -e "$(BLUE)[INFO]$(NC) Start services with: make up"; \
	fi

lint:
	@echo -e "$(PURPLE)=== Linting Scripts ===$(NC)"
	@if command -v shellcheck >/dev/null 2>&1; then \
		echo -e "$(BLUE)[INFO]$(NC) Running shellcheck..."; \
		shellcheck scripts/*.sh; \
		echo -e "$(GREEN)[SUCCESS]$(NC) Shellcheck completed!"; \
	else \
		echo -e "$(YELLOW)[WARNING]$(NC) shellcheck not found. Install it for script validation."; \
	fi
	@if command -v hadolint >/dev/null 2>&1; then \
		echo -e "$(BLUE)[INFO]$(NC) Running hadolint..."; \
		hadolint src/backend/unrealircd/Containerfile src/backend/atheme/Containerfile src/frontend/webpanel/Containerfile src/frontend/gamja/Containerfile; \
		echo -e "$(GREEN)[SUCCESS]$(NC) Hadolint completed!"; \
	else \
		echo -e "$(YELLOW)[WARNING]$(NC) hadolint not found. Install it for Containerfile validation."; \
	fi

# ============================================================================
# MAINTENANCE
# ============================================================================

clean:
	@echo -e "$(PURPLE)=== Cleaning Up ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Removing containers and networks..."
	$(DOCKER_COMPOSE) down
	@echo -e "$(BLUE)[INFO]$(NC) Removing unused images..."
	$(DOCKER) image prune -f
	@echo -e "$(GREEN)[SUCCESS]$(NC) Cleanup completed!"

# ============================================================================
# QUICK ACTIONS
# ============================================================================

stop: ## Stop all services
	@echo -e "$(PURPLE)=== Stopping Services ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) Stopping all services..."
	$(DOCKER_COMPOSE) down
	@echo -e "$(GREEN)[SUCCESS]$(NC) All services stopped and removed."

reset: ## Reset everything - WARNING: destroys data!
	@echo -e "$(RED)=== WARNING: This will DELETE all data! ===$(NC)"
	@echo -e "$(YELLOW)This includes: containers, images, volumes, and data directories$(NC)"
	@echo ""
	@read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm && \
	if [[ "$$confirm" == "yes" ]]; then \
		echo -e "$(BLUE)[INFO]$(NC) Stopping services..."; \
		$(DOCKER_COMPOSE) down -v; \
		echo -e "$(BLUE)[INFO]$(NC) Removing images..."; \
		$(DOCKER) image prune -f; \
		echo -e "$(BLUE)[INFO]$(NC) Removing data directories..."; \
		rm -rf data/ logs/; \
		echo -e "$(GREEN)[SUCCESS]$(NC) Complete reset done."; \
	else \
		echo -e "$(YELLOW)[CANCELLED]$(NC) Reset cancelled."; \
	fi

info: ## Show system information
	@echo -e "$(PURPLE)=== System Information ===$(NC)"
	@echo "Docker version:"
	$(DOCKER) --version
	@echo ""
	@echo "Docker Compose version:"
	$(DOCKER_COMPOSE) --version
	@echo ""
	@echo "Available disk space:"
	df -h . | tail -1
	@echo ""
	@echo "Memory usage:"
	free -h

# ============================================================================
# SSL MANAGEMENT (Simple & Automatic)
# ============================================================================

ssl-setup: ## One-command SSL setup - sets up everything automatically
	@echo -e "$(PURPLE)=== SSL Setup - One Command to Rule Them All ===$(NC)"
	@echo -e "$(BLUE)[INFO]$(NC) This will:"
	@echo -e "$(BLUE)[INFO]$(NC)   1. Issue SSL certificates for your domain"
	@echo -e "$(BLUE)[INFO]$(NC)   2. Start automatic Docker monitoring"
	@echo -e "$(BLUE)[INFO]$(NC)   3. Configure daily renewal at 2 AM"
	@echo ""
	@./scripts/ssl-manager.sh issue
	@docker compose up -d ssl-monitor
	@echo ""
	@echo -e "$(GREEN)[SUCCESS]$(NC) SSL is now fully automated!"
	@echo -e "$(BLUE)[INFO]$(NC) Certificates will renew automatically every day at 2 AM"
	@echo -e "$(BLUE)[INFO]$(NC) Check status anytime with: make ssl-status"

ssl-status: ## Check SSL certificate status
	@echo -e "$(PURPLE)=== SSL Certificate Status ===$(NC)"
	@if [[ -f "src/backend/unrealircd/conf/tls/server.cert.pem" ]]; then \
		./scripts/ssl-manager.sh check; \
		echo ""; \
		docker compose ps ssl-monitor | grep -q "Up" && echo -e "$(GREEN)[OK]$(NC) SSL monitoring is running" || echo -e "$(YELLOW)[WARNING]$(NC) SSL monitoring is not running"; \
	else \
		echo -e "$(YELLOW)[INFO]$(NC) No SSL certificates found. Run 'make ssl-setup' to get started."; \
	fi

ssl-renew: ## Force certificate renewal
	@echo -e "$(PURPLE)=== Forcing SSL Certificate Renewal ===$(NC)"
	@if [[ -f "src/backend/unrealircd/conf/tls/server.cert.pem" ]]; then \
		./scripts/ssl-manager.sh renew; \
	else \
		echo -e "$(YELLOW)[WARNING]$(NC) No SSL certificates found. Run 'make ssl-setup' first."; \
	fi

ssl-logs: ## View SSL monitoring logs
	@echo -e "$(PURPLE)=== SSL Monitoring Logs ===$(NC)"
	@docker compose logs -f ssl-monitor --tail=50

ssl-stop: ## Stop SSL monitoring
	@echo -e "$(PURPLE)=== Stopping SSL Monitoring ===$(NC)"
	@docker compose down ssl-monitor
	@echo -e "$(GREEN)[SUCCESS]$(NC) SSL monitoring stopped"

ssl-clean: ## Remove SSL certificates and monitoring (CAUTION: destroys certificates!)
	@echo -e "$(RED)=== WARNING: This will DELETE your SSL certificates! ===$(NC)"
	@echo -e "$(YELLOW)This action cannot be undone.$(NC)"
	@echo ""
	@read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm && \
	if [[ "$$confirm" == "yes" ]]; then \
		echo -e "$(BLUE)[INFO]$(NC) Removing SSL certificates..."; \
		rm -rf data/letsencrypt src/backend/unrealircd/conf/tls; \
		docker compose down ssl-monitor; \
		echo -e "$(GREEN)[SUCCESS]$(NC) SSL certificates and monitoring removed."; \
	else \
		echo -e "$(YELLOW)[CANCELLED]$(NC) SSL cleanup cancelled."; \
	fi

# ============================================================================
# UTILITIES
# ============================================================================

generate-password: ## Generate new IRC operator password hash
	@echo -e "$(PURPLE)=== Generating IRC Operator Password ===$(NC)"
	@./src/backend/unrealircd/scripts/generate-oper-password.sh
