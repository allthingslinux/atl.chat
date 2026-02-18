# Testing Strategy & Framework

This guide covers the comprehensive testing framework for IRC.atl.chat, including unit tests, integration tests, end-to-end tests, and performance testing.

## Overview

### Testing Philosophy

IRC.atl.chat employs a **defense-in-depth** testing strategy with multiple layers of quality assurance:

- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Service interaction validation
- **End-to-End Tests**: Complete workflow verification
- **Performance Tests**: Load and stress testing
- **Protocol Tests**: RFC compliance validation

### Test Architecture

```
tests/
├── unit/                    # Fast, isolated unit tests
├── integration/            # Service interaction tests
├── e2e/                    # Complete workflow tests
├── protocol/               # IRC protocol compliance
├── controllers/            # Test infrastructure
├── fixtures/               # Test data and helpers
├── utils/                  # Testing utilities
└── legacy/                 # Deprecated tests (reference only)
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that don't require external dependencies:

#### Configuration Testing
```python
def test_environment_validation():
    """Test environment variable validation logic"""
    validator = EnvironmentValidator()
    assert validator.validate_domain("irc.example.com")
    assert not validator.validate_domain("invalid..domain")
```

#### Docker Client Testing
```python
def test_docker_client_connection(docker_client):
    """Test Docker API connectivity"""
    assert docker_client.ping()
    containers = docker_client.containers.list()
    assert isinstance(containers, list)
```

#### IRC Server Mock Testing
```python
def test_irc_server_mock():
    """Test IRC server mock responses"""
    mock = IRCdMock()
    mock.start()
    client = IRCClient()
    client.connect("localhost", mock.port)
    assert client.receive_welcome()
```

### Integration Tests (`tests/integration/`)

Tests that verify component interactions with controlled environments:

#### IRC Protocol Compliance
```python
def test_rfc1459_nick_command(irc_server):
    """Test RFC1459 NICK command implementation"""
    client = IRCClient()
    client.connect(irc_server.host, irc_server.port)

    # Test valid nick change
    client.send("NICK testuser")
    response = client.receive()
    assert ":testuser" in response

    # Test nick collision
    client2 = IRCClient()
    client2.connect(irc_server.host, irc_server.port)
    client2.send("NICK testuser")
    response = client2.receive()
    assert "433" in response  # ERR_NICKNAMEINUSE
```

#### Service Integration
```python
def test_nickserv_registration(irc_services):
    """Test NickServ registration workflow"""
    client = IRCClient()
    client.connect(irc_services.host, irc_services.port)

    # Register nickname
    client.send("NICKSERV REGISTER mypass user@example.com")
    response = client.receive()
    assert "Nickname registered" in response

    # Verify registration
    client.send("NICKSERV INFO mynick")
    response = client.receive()
    assert "user@example.com" in response
```

#### Client Library Integration
```python
def test_python_irc_client():
    """Test python-irc library integration"""
    import irc.client

    def on_welcome(connection, event):
        connection.quit("Test complete")

    client = irc.client.IRC()
    server = client.server()
    server.connect("localhost", 6667, "testuser")
    server.add_global_handler("welcome", on_welcome)
    client.process_forever()
```

### End-to-End Tests (`tests/e2e/`)

Complete workflow validation from user perspective:

#### Full IRC Session
```python
def test_complete_irc_workflow():
    """Test complete user journey"""
    # Start services
    services = DockerServices()
    services.start()

    try:
        # Connect client
        client = IRCClient()
        client.connect("localhost", 6697, tls=True)

        # Register with services
        client.nickserv_register("testpass", "test@example.com")
        client.nickserv_identify("testpass")

        # Join channel
        client.join("#testchannel")

        # Send message
        client.privmsg("#testchannel", "Hello World!")

        # Verify message received
        messages = client.get_messages()
        assert "Hello World!" in str(messages)

    finally:
        services.stop()
```

### Protocol Tests (`tests/protocol/`)

IRC specification compliance validation:

#### Message Parsing
```python
def test_irc_message_parsing():
    """Test IRC message format parsing"""
    parser = IRCMessageParser()

    # Test PRIVMSG
    msg = parser.parse(":nick!user@host PRIVMSG #channel :Hello World")
    assert msg.command == "PRIVMSG"
    assert msg.params[0] == "#channel"
    assert msg.params[1] == "Hello World"

    # Test JOIN
    msg = parser.parse(":nick!user@host JOIN #channel")
    assert msg.command == "JOIN"
    assert msg.params[0] == "#channel"
```

#### RFC Compliance
```python
def test_rfc2812_channel_modes():
    """Test RFC2812 channel mode specifications"""
    # Test mode combinations
    modes = ChannelModes()
    modes.set("+nt")  # Topic protection + no external messages
    assert modes.has_mode("n")
    assert modes.has_mode("t")

    # Test mode conflicts
    modes.set("+ps")  # Private + secret (should be valid)
    assert modes.has_mode("p") and modes.has_mode("s")
```

## Test Infrastructure

### Controllers

Test controllers provide controlled test environments:

#### IRC Server Controller
```python
class UnrealIRCdController:
    def __init__(self, config_path):
        self.config_path = config_path
        self.container = None

    def start(self):
        """Start IRC server with test configuration"""
        self.container = docker.containers.run(
            "atl-irc-server:test",
            volumes={self.config_path: "/config"},
            ports={"6667": None},  # Random port
            detach=True
        )
        self.host = "localhost"
        self.port = self._get_mapped_port(6667)

    def stop(self):
        """Stop IRC server"""
        if self.container:
            self.container.stop()
            self.container.remove()
```

#### Atheme Services Controller
```python
class AthemeController:
    def __init__(self, irc_host, irc_port):
        self.irc_host = irc_host
        self.irc_port = irc_port
        self.container = None

    def start(self):
        """Start Atheme services linked to IRC server"""
        network = docker.networks.get("test-network")
        self.container = docker.containers.run(
            "atheme:test",
            network_mode=f"container:{irc_container.id}",
            detach=True
        )
```

### Fixtures

Reusable test fixtures provide common test data:

#### Docker Fixtures
```python
@pytest.fixture(scope="session")
def docker_client():
    """Docker API client fixture"""
    import docker
    client = docker.from_env()
    assert client.ping()
    return client

@pytest.fixture(scope="session")
def docker_compose_helper(project_root):
    """Docker Compose operations helper"""
    return DockerComposeHelper(project_root)
```

#### IRC Test Fixtures
```python
@pytest.fixture
def irc_server():
    """Running IRC server fixture"""
    controller = UnrealIRCdController("tests/fixtures/unrealircd.conf")
    controller.start()
    yield controller
    controller.stop()

@pytest.fixture
def irc_client(irc_server):
    """Connected IRC client fixture"""
    client = IRCClient()
    client.connect(irc_server.host, irc_server.port)
    yield client
    client.disconnect()
```

### Test Helpers

Utility functions for common testing operations:

#### IRC Client Helper
```python
class IRCTestClient:
    def __init__(self, host, port, tls=False):
        self.socket = None
        self.host = host
        self.port = port
        self.tls = tls

    def connect(self, nickname="testuser"):
        """Connect to IRC server"""
        if self.tls:
            context = ssl.create_default_context()
            self.socket = context.wrap_socket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            )
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.socket.connect((self.host, self.port))

        # Send NICK and USER
        self.send(f"NICK {nickname}")
        self.send(f"USER {nickname} 0 * :Test User")

    def send(self, message):
        """Send IRC message"""
        self.socket.send(f"{message}\r\n".encode())

    def receive(self, timeout=1):
        """Receive IRC message"""
        self.socket.settimeout(timeout)
        try:
            data = self.socket.recv(4096).decode()
            return data.strip()
        except socket.timeout:
            return None
```

## Running Tests

### Command Line Execution

#### Using Make (Recommended)
```bash
# Complete test suite
make test

# Specific test categories
make test-unit         # Unit tests (~30 seconds)
make test-integration  # Integration tests (~2 minutes)
make test-e2e          # End-to-end tests (~5 minutes)
make test-protocol     # Protocol tests (~1 minute)
make test-performance  # Performance tests (~10 minutes)

# Targeted testing
make test-services     # Service integration tests
make test-docker       # Docker-related tests
make test-quick        # Fast environment check
```

#### Using uv Directly
```bash
# All tests
uv run pytest tests/

# With coverage
uv run pytest --cov=src --cov-report=html tests/

# Specific markers
uv run pytest -m "docker and integration"

# Verbose output
uv run pytest -v tests/unit/
```

#### Selective Test Execution
```bash
# Run specific test file
uv run pytest tests/integration/test_services.py

# Run specific test function
uv run pytest tests/unit/test_configuration.py::test_domain_validation

# Run tests matching pattern
uv run pytest -k "nickserv"

# Run with different log levels
uv run pytest --log-level=DEBUG tests/
```

### Test Configuration

#### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    docker: Tests requiring Docker
    irc: Tests requiring IRC server
    slow: Slow-running tests
    network: Tests requiring network access
    performance: Performance tests
```

#### pyproject.toml
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "docker: Tests requiring Docker",
    "irc: Tests requiring IRC server",
    "slow: Slow-running tests",
]
```

## Test Data & Fixtures

### Sample Data
```python
@pytest.fixture
def sample_irc_config():
    """Sample IRC server configuration"""
    return {
        "server_name": "test.irc.example.com",
        "server_description": "Test IRC Server",
        "network_name": "TestNet",
        "admin_info": {
            "name": "Test Admin",
            "email": "admin@test.example.com"
        },
        "ports": {
            "plain": 6667,
            "ssl": 6697,
            "server": 6900
        }
    }

@pytest.fixture
def sample_user_registration():
    """Sample user registration data"""
    return {
        "nickname": "testuser",
        "username": "test",
        "realname": "Test User",
        "password": "securepassword123",
        "email": "test@example.com"
    }
```

### Test Scenarios

#### Channel Operations
```python
def test_channel_creation_and_join(irc_server, irc_client):
    """Test channel creation and joining"""
    # Create channel
    irc_client.send("JOIN #testchannel")

    # Verify join
    response = irc_client.receive()
    assert "JOIN #testchannel" in response

    # Check topic
    irc_client.send("TOPIC #testchannel")
    response = irc_client.receive()
    assert "331" in response  # RPL_NOTOPIC
```

#### User Modes
```python
def test_user_mode_changes(irc_client):
    """Test user mode modifications"""
    # Set invisible mode
    irc_client.send("MODE testuser +i")
    response = irc_client.receive()
    assert "MODE testuser +i" in response

    # Verify mode set
    irc_client.send("MODE testuser")
    response = irc_client.receive()
    assert "+i" in response
```

## Performance Testing

### Load Testing
```python
def test_concurrent_connections(irc_server):
    """Test multiple concurrent connections"""
    clients = []

    # Create 100 concurrent connections
    for i in range(100):
        client = IRCClient()
        client.connect(irc_server.host, irc_server.port)
        client.nick(f"user{i}")
        clients.append(client)

    # Verify all connections active
    active_count = sum(1 for c in clients if c.is_connected())
    assert active_count == 100

    # Clean up
    for client in clients:
        client.quit()
```

### Stress Testing
```python
def test_message_flood_protection(irc_server, irc_client):
    """Test flood protection mechanisms"""
    # Join channel
    irc_client.join("#floodtest")

    # Send rapid messages
    for i in range(50):
        irc_client.privmsg("#floodtest", f"Flood message {i}")

    # Verify flood protection activated
    response = irc_client.receive()
    assert "482" in response  # ERR_CHANOPRIVSNEEDED or flood message
```

### Benchmarking
```python
def test_message_throughput(benchmark):
    """Benchmark message processing throughput"""

    def send_messages():
        client = IRCClient()
        client.connect("localhost", 6697, tls=True)
        client.join("#benchmark")

        for i in range(1000):
            client.privmsg("#benchmark", f"Message {i}")

        client.quit()

    # Run benchmark
    result = benchmark(send_messages)
    assert result.stats.mean < 1.0  # Should complete within 1 second
```

## CI/CD Integration

### GitHub Actions Testing
```yaml
- name: Run Tests
  run: |
    make test-unit
    make test-integration

- name: Run Performance Tests
  run: |
    make test-performance

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Test Reporting
```bash
# Generate HTML reports
uv run pytest --html=report.html --self-contained-html

# Generate coverage reports
uv run pytest --cov=src --cov-report=html --cov-report=xml

# JUnit XML for CI
uv run pytest --junitxml=test-results.xml
```

## Debugging Tests

### Test Isolation
```python
# Run single failing test
uv run pytest tests/integration/test_services.py::test_nickserv_registration -v

# Run with debugging
uv run pytest --pdb tests/unit/test_configuration.py

# Capture logs
uv run pytest --log-cli-level=DEBUG -s
```

### Common Issues

#### Docker Connection Issues
```bash
# Verify Docker is running
docker ps

# Check Docker socket permissions
ls -la /var/run/docker.sock

# Test Docker connectivity
docker run hello-world
```

#### Port Conflicts
```bash
# Find used ports
netstat -tlnp | grep :6697

# Use random ports in tests
@pytest.fixture
def irc_server():
    controller = UnrealIRCdController()
    controller.start()  # Uses random available port
    return controller
```

#### Service Dependencies
```bash
# Ensure services start in order
@pytest.fixture(scope="session", autouse=True)
def start_services():
    services = DockerServices()
    services.start()
    yield
    services.stop()
```

## Test Maintenance

### Adding New Tests

#### Unit Test Template
```python
import pytest

class TestConfigurationValidation:
    """Test configuration validation functions"""

    def test_valid_domain_names(self):
        """Test domain name validation"""
        validator = DomainValidator()

        valid_domains = [
            "irc.example.com",
            "chat.example.org",
            "irc.subdomain.example.net"
        ]

        for domain in valid_domains:
            assert validator.is_valid(domain)

    def test_invalid_domain_names(self):
        """Test invalid domain rejection"""
        validator = DomainValidator()

        invalid_domains = [
            "",
            "invalid..domain",
            "domain",
            "domain.",
            ".domain.com"
        ]

        for domain in invalid_domains:
            assert not validator.is_valid(domain)
```

#### Integration Test Template
```python
import pytest

class TestIRCConnectivity:
    """Test IRC server connectivity"""

    def test_ssl_connection(self, irc_server):
        """Test SSL/TLS connection to IRC server"""
        client = IRCClient()
        client.connect(irc_server.host, irc_server.port, tls=True)

        # Verify secure connection
        assert client.is_connected()
        assert client.is_encrypted()

        # Test basic IRC commands
        client.nick("ssltest")
        response = client.receive()
        assert "ssltest" in response

        client.quit()

    def test_plaintext_connection_disabled(self, irc_server):
        """Test that plaintext connections are disabled"""
        client = IRCClient()

        with pytest.raises(ConnectionError):
            client.connect(irc_server.host, 6667, tls=False)
```

### Test Organization

#### Test File Structure
```
tests/
├── unit/
│   ├── test_configuration.py
│   ├── test_validation.py
│   └── test_utils.py
├── integration/
│   ├── test_irc_server.py
│   ├── test_services.py
│   └── test_clients.py
├── e2e/
│   ├── test_user_workflow.py
│   └── test_admin_workflow.py
└── fixtures/
    ├── docker_fixtures.py
    ├── irc_fixtures.py
    └── data_fixtures.py
```

#### Test Naming Conventions
```python
# Unit tests
def test_function_name_condition_expected_result():
    pass

# Integration tests
def test_component_interaction_scenario():
    pass

# End-to-end tests
def test_complete_user_journey():
    pass
```

## Coverage Goals

### Target Coverage Metrics
- **Unit Tests**: >90% coverage
- **Integration Tests**: >80% coverage
- **Critical Paths**: 100% coverage
- **Error Handling**: Complete coverage

### Coverage Reporting
```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Check coverage thresholds
uv run pytest --cov=src --cov-fail-under=85

# Exclude files from coverage
uv run pytest --cov=src --cov-report=html \
    --cov-report=term-missing \
    --cov-exclude="*/tests/*" \
    --cov-exclude="*/migrations/*"
```

## Performance Benchmarks

### Test Execution Times
- **Unit Tests**: <30 seconds
- **Integration Tests**: <2 minutes
- **End-to-End Tests**: <5 minutes
- **Performance Tests**: <10 minutes
- **Full Suite**: <20 minutes

### Resource Usage
- **Memory**: <512MB per test run
- **Disk**: <1GB for test data
- **Network**: Minimal external dependencies

## Related Documentation

- [README.md](../README.md) - Quick start guide
- [DOCKER.md](DOCKER.md) - Container setup for testing
- [CONFIG.md](CONFIG.md) - Configuration testing
- [CI_CD.md](CI_CD.md) - CI/CD testing integration
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development testing workflow