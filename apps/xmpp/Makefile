.PHONY: help dev dev-up dev-down dev-logs dev-build dev-clean prod prod-up prod-down prod-logs prod-build prod-clean build clean logs status setup-modules update-modules list-modules list-local-modules enable-module test db-backup db-restore

# Default target
help: ## Show this help message
	@echo "XMPP Server Management Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Environment
dev: dev-up ## Start development environment

dev-up: ## Start development environment
	docker compose -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "Adminer: http://localhost:8081"
	@echo "Logs:   http://localhost:8082"

dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

dev-logs: ## View development logs
	docker compose -f docker-compose.dev.yml logs -f

dev-build: ## Build development containers
	docker compose -f docker-compose.dev.yml build --no-cache

dev-clean: ## Clean development environment (targeted cleanup: only xmpp-server-dev resources)
	@echo "🧹 Performing targeted development environment cleanup..."
	@echo "Stopping and removing containers..."
	docker compose -f docker-compose.dev.yml down -v --remove-orphans
	@echo "Removing XMPP development networks..."
	docker network ls --filter "label=com.docker.compose.project=xmpp-server-dev" -q | xargs -r docker network rm
	@echo "Removing XMPP development volumes..."
	docker volume ls --filter "label=com.docker.compose.project=xmpp-server-dev" -q | xargs -r docker volume rm
	@echo "Removing XMPP development images..."
	docker image ls --filter "label=com.docker.compose.project=xmpp-server-dev" -q | xargs -r docker rmi
	@echo "Removing dangling images and build cache..."
	docker image prune -f
	docker builder prune -f
	@echo "✅ Targeted development cleanup complete!"

# Production Environment
prod: prod-up ## Start production environment

prod-up: ## Start production environment
	docker compose up -d
	@echo "Production environment started!"

prod-down: ## Stop production environment
	docker compose down

prod-logs: ## View production logs
	docker compose logs -f

prod-build: ## Build production containers
	docker compose build --no-cache

prod-clean: ## Clean production environment (targeted cleanup: only xmpp-server resources)
	@echo "🧹 Performing targeted production environment cleanup..."
	@echo "Stopping and removing containers..."
	docker compose down -v --remove-orphans
	@echo "Removing XMPP production networks..."
	docker network ls --filter "label=com.docker.compose.project=xmpp-server" -q | xargs -r docker network rm
	@echo "Removing XMPP production volumes..."
	docker volume ls --filter "label=com.docker.compose.project=xmpp-server" -q | xargs -r docker volume rm
	@echo "Removing XMPP production images..."
	docker image ls --filter "label=com.docker.compose.project=xmpp-server" -q | xargs -r docker rmi
	@echo "Removing dangling images and build cache..."
	docker image prune -f
	docker builder prune -f
	@echo "✅ Targeted production cleanup complete!"

# General Commands
build: ## Build all containers
	docker compose -f docker-compose.dev.yml build
	docker compose build

clean: ## Clean all environments (FULL WIPE: containers, networks, volumes, images)
	@echo "🧹 Performing FULL cleanup of all environments..."
	@echo "Cleaning development environment..."
	docker compose -f docker-compose.dev.yml down -v --remove-orphans
	@echo "Cleaning production environment..."
	docker compose down -v --remove-orphans
	@echo "Removing Docker networks..."
	docker network prune -f
	@echo "Removing Docker volumes..."
	docker volume prune -f
	@echo "Removing Docker images..."
	docker image prune -f
	@echo "Removing build cache..."
	docker builder prune -f
	@echo "System-wide cleanup..."
	docker system prune -a -f --volumes
	@echo "✅ Full cleanup complete!"

logs: ## View logs from all running containers
	docker compose -f docker-compose.dev.yml logs -f || docker compose logs -f

status: ## Check status of all services
	@echo "=== Development Services ==="
	docker compose -f docker-compose.dev.yml ps
	@echo ""
	@echo "=== Production Services ==="
	docker compose ps

# Module Management (Local-First Approach)
setup-modules: ## Setup Prosody community modules locally (run once)
	@echo "Setting up Prosody community modules locally..."
	./scripts/setup-modules-locally.sh

update-modules: ## Update local Prosody community modules repository
	@echo "Updating local Prosody community modules..."
	@if [[ -d "prosody-modules/.hg" ]]; then \
		(cd prosody-modules && (hg pull bundle 2>/dev/null || hg pull default) && hg update); \
		echo "✅ Modules updated successfully"; \
	else \
		echo "❌ prosody-modules repository not found. Run 'make setup-modules' first"; \
	fi

# Database Commands
db-backup: ## Backup PostgreSQL database
	@echo "Backing up database..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-postgres-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		BACKUP_FILE="backup_$$(date +%Y%m%d_%H%M%S).sql"; \
		docker exec $$CONTAINER pg_dumpall -U prosody > $$BACKUP_FILE; \
		echo "Database backup saved to: $$BACKUP_FILE"; \
	else \
		echo "Database container not running"; \
	fi

db-restore: ## Restore PostgreSQL database (usage: make db-restore FILE=backup.sql)
	@echo "Restoring database from: $(FILE)"
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-postgres-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ] && [ -f "$(FILE)" ]; then \
		docker exec -i $$CONTAINER psql -U prosody < $(FILE); \
		echo "Database restored from: $(FILE)"; \
	else \
		echo "Database container not running or backup file not found"; \
	fi

# Testing
test: ## Run basic connectivity tests
	@echo "Running connectivity tests..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		echo "Testing Prosody connectivity..."; \
		docker exec $$CONTAINER prosodyctl status || echo "Prosody not responding"; \
		echo "Testing PostgreSQL connectivity..."; \
		docker exec $$CONTAINER psql -h xmpp-postgres-dev -U prosody -d prosody -c "SELECT 1;" || echo "PostgreSQL not accessible"; \
	else \
		echo "Development environment not running"; \
	fi



# Utility Commands
shell: ## Open shell in running Prosody container
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec -it $$CONTAINER /bin/bash; \
	else \
		echo "Development environment not running"; \
	fi

shell-prod: ## Open shell in running production Prosody container
	@CONTAINER=$$(docker compose ps -q xmpp-prosody 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec -it $$CONTAINER /bin/bash; \
	else \
		echo "Production environment not running"; \
	fi

reload: ## Reload Prosody configuration
	@echo "Reloading Prosody configuration..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER prosodyctl reload; \
	else \
		echo "Development environment not running"; \
	fi

restart: ## Restart Prosody service
	@echo "Restarting Prosody service..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER prosodyctl restart; \
	else \
		echo "Development environment not running"; \
	fi

# ============================================================================
# PROSODY MANAGER COMMANDS (from app/bin/prosody-manager)
# ============================================================================

# User Management
adduser: ## Add a user (usage: make adduser USER=user@domain.com [PASSWORD=secret])
	@echo "Adding user: $(USER)"
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		if [ -n "$(PASSWORD)" ]; then \
			docker exec $$CONTAINER bash -c "echo -e '$(PASSWORD)\n$(PASSWORD)' | prosodyctl adduser $(USER)"; \
		else \
			docker exec -it $$CONTAINER prosodyctl adduser $(USER); \
		fi; \
	else \
		echo "Development environment not running"; \
	fi

deluser: ## Delete a user (usage: make deluser USER=user@domain.com)
	@echo "Deleting user: $(USER)"
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER prosodyctl deluser $(USER); \
	else \
		echo "Development environment not running"; \
	fi

passwd: ## Change user password (usage: make passwd USER=user@domain.com [PASSWORD=newpass])
	@echo "Changing password for user: $(USER)"
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		if [ -n "$(PASSWORD)" ]; then \
			docker exec $$CONTAINER prosodyctl passwd $(USER) $(PASSWORD); \
		else \
			docker exec -it $$CONTAINER prosodyctl passwd $(USER); \
		fi; \
	else \
		echo "Development environment not running"; \
	fi

prosody-status: ## Show Prosody server status
	@echo "Getting Prosody status..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER prosodyctl status; \
	else \
		echo "Development environment not running"; \
	fi

# Module Management
list-modules: ## List installed Prosody modules
	@echo "Listing installed modules..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER find /usr/local/lib/prosody -name "mod_*.lua" | sort; \
	else \
		echo "Development environment not running"; \
	fi

list-local-modules: ## List available local modules
	@echo "Available modules in prosody-modules repository:"
	@if [[ -d "prosody-modules" ]]; then \
		ls prosody-modules/ | grep "^mod_" | sort; \
	else \
		echo "❌ prosody-modules repository not found. Run 'make setup-modules' first"; \
	fi

enable-module: ## Enable a module (usage: make enable-module MODULE=mod_new_module)
	@echo "Enabling module: $(MODULE)"
	@if [[ ! -d "prosody-modules/$(MODULE)" ]]; then \
		echo "❌ Module $(MODULE) not found in prosody-modules repository"; \
		echo "Run 'make list-modules' to see available modules"; \
		exit 1; \
	fi
	@mkdir -p prosody-modules-enabled
	@if [[ -L "prosody-modules-enabled/$(MODULE)" ]]; then \
		echo "✅ Module $(MODULE) is already enabled"; \
	else \
		ln -sf "../prosody-modules/$(MODULE)" "prosody-modules-enabled/$(MODULE)"; \
		echo "✅ Module $(MODULE) enabled successfully"; \
		echo "📝 Rebuild the container to apply changes: make dev-build"; \
	fi

# Certificate Management
check-cert: ## Check certificate status (usage: make check-cert DOMAIN=example.com)
	@echo "Checking certificate for: $(DOMAIN)"
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/certificate-monitor.sh check "$(DOMAIN)"; \
	else \
		echo "Development environment not running"; \
	fi

cert-status: ## Show certificate monitoring status
	@echo "Getting certificate status..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/certificate-monitor.sh status; \
	else \
		echo "Development environment not running"; \
	fi

# Environment Setup
setup-dev: ## Setup development environment files
	@echo "Setting up development environment..."
	@./scripts/setup-environment.sh --non-interactive development

setup-prod: ## Setup production environment files
	@echo "Setting up production environment..."
	@./scripts/setup-environment.sh --non-interactive production

setup-all: ## Setup all environment files
	@echo "Setting up all environments..."
	@./scripts/setup-environment.sh --non-interactive all

# Health Checks
health: ## Run comprehensive health checks
	@echo "Running health checks..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/health-check.sh; \
	else \
		echo "Development environment not running"; \
	fi

# ============================================================================
# CERTIFICATE MONITORING COMMANDS (from scripts/certificate-monitor.sh)
# ============================================================================

cert-monitor: ## Run certificate monitoring
	@echo "Running certificate monitoring..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/certificate-monitor.sh monitor; \
	else \
		echo "Development environment not running"; \
	fi

cert-renewal: ## Check and renew certificates if needed
	@echo "Checking for certificate renewals..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/certificate-monitor.sh auto-renew; \
	else \
		echo "Development environment not running"; \
	fi

cert-dashboard: ## Generate certificate health dashboard
	@echo "Generating certificate dashboard..."
	@CONTAINER=$$(docker compose -f docker-compose.dev.yml ps -q xmpp-prosody-dev 2>/dev/null); \
	if [ -n "$$CONTAINER" ]; then \
		docker exec $$CONTAINER /usr/local/bin/certificate-monitor.sh dashboard; \
	else \
		echo "Development environment not running"; \
	fi

# ============================================================================
# RUNTIME DIRECTORY MANAGEMENT
# ============================================================================

runtime-init: ## Initialize runtime directory structure
	@echo "Initializing runtime directory..."
	@mkdir -p .runtime/certs/live .runtime/certs/accounts .runtime/certs/archive
	@mkdir -p .runtime/logs .runtime/backups .runtime/cache .runtime/db
	@mkdir -p .runtime/sessions .runtime/uploads .runtime/turn
	@echo "Runtime directory structure initialized"

runtime-clean: ## Clean runtime directory (remove all data)
	@echo "Cleaning runtime directory..."
	@rm -rf .runtime/*
	@echo "Runtime directory cleaned"

runtime-backup: ## Backup runtime directory
	@echo "Backing up runtime directory..."
	@BACKUP_FILE="runtime-backup-$$(date +%Y%m%d_%H%M%S).tar.gz"; \
	tar -czf "$$BACKUP_FILE" .runtime/; \
	echo "Runtime backup saved to: $$BACKUP_FILE"

runtime-restore: ## Restore runtime directory (usage: make runtime-restore FILE=backup.tar.gz)
	@echo "Restoring runtime directory from: $(FILE)"
	@if [ -f "$(FILE)" ]; then \
		rm -rf .runtime.bak; \
		mv .runtime .runtime.bak 2>/dev/null || true; \
		mkdir -p .runtime; \
		tar -xzf "$(FILE)" -C .runtime --strip-components=1 2>/dev/null || tar -xzf "$(FILE)" -C ./; \
		echo "Runtime directory restored from: $(FILE)"; \
	else \
		echo "Backup file not found: $(FILE)"; \
		exit 1; \
	fi

runtime-logs: ## Show runtime logs
	@echo "=== Runtime Logs ==="
	@find .runtime/logs -name "*.log" -type f -exec echo "=== {} ===" \; -exec tail -20 {} \; 2>/dev/null || echo "No log files found"

runtime-status: ## Show runtime directory status
	@echo "=== Runtime Directory Status ==="
	@echo "Directory: .runtime/"
	@du -sh .runtime/ 2>/dev/null || echo "Runtime directory not found"
	@echo ""
	@echo "Subdirectories:"
	@find .runtime -type d -exec ls -ld {} \; 2>/dev/null | sort || echo "No subdirectories found"
	@echo ""
	@echo "Files:"
	@find .runtime -type f -exec ls -lh {} \; 2>/dev/null | head -20 || echo "No files found"
