# ATL Bridge task runner
# Install just: pacman -S just (Arch) or cargo install just

default:
    just --list

# Install dependencies
sync:
    uv sync

# Run tests
test:
    uv run pytest tests -v

# Lint (check only)
lint:
    uv run ruff check src tests

# Format code
format:
    uv run ruff format src tests

# Format check (CI-style, no changes)
format-check:
    uv run ruff format --check src tests

# Type check
typecheck:
    uv run basedpyright

# Run the bridge (requires config)
run config="config.yaml":
    uv run bridge --config {{ config }}

# Full CI pipeline locally
ci: sync lint format-check test

# Coverage report
coverage:
    uv run pytest tests -v --cov=src/bridge --cov-report=term-missing --cov-report=html

# Fix lint issues (where fixable)
fix:
    uv run ruff check src tests --fix
    uv run ruff format src tests
