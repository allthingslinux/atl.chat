# IRC.atl.chat Test Suite

This directory contains the comprehensive test suite for IRC.atl.chat using pytest and uv.

## Structure

### Traditional Test Organization (by Testing Level)

- **`unit/`** - Unit tests for individual components and functions
  - `test_configuration.py` - Configuration file testing
  - `test_docker_client.py` - Docker client functionality
  - `test_environment_validation.py` - Environment setup validation
  - `test_irc_server_mock.py` - IRC server mock testing
- **`integration/`** - Integration tests using controlled IRC servers
  - `test_protocol.py` - IRC protocol compliance (RFC1459, RFC2812)
  - `test_clients.py` - Client library integration (pydle, python-irc)
  - `test_services.py` - Service integration (NickServ, ChanServ, Atheme)
  - `test_monitoring.py` - Server monitoring and RPC functionality
  - `test_performance.py` - Performance and load testing
  - `test_infrastructure.py` - Infrastructure and deployment tests
  - `test_irc_functionality.py` - General IRC server functionality
- **`e2e/`** - End-to-end workflow tests
- **`protocol/`** - Basic IRC message protocol tests (unit-level)

### Support & Infrastructure

- **`controllers/`** - IRC server controller classes (UnrealIRCd, Atheme)
- **`fixtures/`** - Test fixtures and sample data
- **`utils/`** - Test utilities and helper functions
  - `base_test_cases.py` - Base test case classes for IRC testing
  - `irc_test_client.py` - IRC test client utilities
  - `runner.py` - Test runner utilities and exceptions
  - `specifications.py` - IRC specification definitions
  - `test_helpers.py` - General test helper functions
- **`irc_utils/`** - IRC protocol utilities
  - `message_parser.py` - IRC message parsing
- **`legacy/integration/`** - Legacy integration tests (deprecated, kept for reference)

### Root Level Files

- **`conftest.py`** - Shared pytest fixtures and configuration
- **`README.md`** - Test suite documentation

## Running Tests

### Using Make (Recommended)
```bash
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make test-docker       # Run Docker-related tests
```

### Using uv directly
```bash
uv run pytest tests/                    # Run all tests
uv run pytest tests/unit/              # Run unit tests
uv run pytest tests/integration/       # Run integration tests
uv run pytest tests/protocol/          # Run protocol tests
uv run pytest -m docker                # Run Docker tests
uv run pytest -m slow                  # Run slow tests
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.docker` - Tests requiring Docker
- `@pytest.mark.irc` - Tests requiring IRC server
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.network` - Tests requiring network access

## Configuration

Tests are configured via:
- `pyproject.toml` - pytest configuration and dependencies
- `pytest.ini` - Additional pytest settings

## Fixtures

Common fixtures available:
- `docker_client` - Docker API client
- `project_root` - Project root directory
- `compose_file` - Docker Compose file path
- `irc_helper` - IRC connection helper
- `docker_compose_helper` - Docker Compose operations
- `sample_config_data` - Sample configuration data

## Dependencies

Test dependencies are managed via uv and defined in `pyproject.toml` under `[project.optional-dependencies] test`.
