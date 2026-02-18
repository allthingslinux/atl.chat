"""Test configuration and shared fixtures for IRC.atl.chat testing.

This conftest.py supports both the legacy test structure and the new consolidated structure.
New tests should use the consolidated structure in tests/consolidated/.

Legacy tests in tests/legacy/integration/ are still supported for backward compatibility.
"""

import importlib
import os
import time
from pathlib import Path

import docker
import pytest

# Docker fixtures using pytest-docker-tools
from pytest_docker_tools import build, container

from .controllers.base_controllers import BaseServerController, TestCaseControllerConfig
from .utils.base_test_cases import BaseServerTestCase

# Build UnrealIRCd image from project Containerfile (self-contained tests)
_unrealircd_build_path = Path(__file__).resolve().parent.parent / "services" / "unrealircd"
unrealircd_image = build(
    path=str(_unrealircd_build_path),
    dockerfile="Containerfile",
    tag="ircatlchat-unrealircd:latest",
)


@pytest.fixture(scope="function")
def prepared_config_dir(tmp_path):
    """Create and prepare a temporary directory with UnrealIRCd config files."""
    import shutil
    from pathlib import Path

    config_dir = tmp_path / "container_config"
    config_dir.mkdir(exist_ok=True)

    # Source directory with real configs (relative to apps/irc)
    _conftest_dir = Path(__file__).resolve().parent
    source_dir = _conftest_dir.parent / "services" / "unrealircd" / "config"

    # Copy all config files
    for config_file in source_dir.glob("*.conf"):
        dest_file = config_dir / config_file.name
        shutil.copy2(config_file, dest_file)
        dest_file.chmod(0o644)  # Make readable by anyone

    # Copy subdirectories
    for subdir in ["help", "aliases", "tls"]:
        if (source_dir / subdir).exists():
            shutil.copytree(source_dir / subdir, config_dir / subdir, dirs_exist_ok=True)
            # Set permissions on subdirectory files
            for file in (config_dir / subdir).rglob("*"):
                if file.is_file():
                    file.chmod(0o644)

    # Copy other necessary files
    for pattern in ["*.list", "*.default.conf", "*.optional.conf"]:
        for file in source_dir.glob(pattern):
            dest_file = config_dir / file.name
            shutil.copy2(file, dest_file)
            dest_file.chmod(0o644)

    return config_dir


unrealircd_container = container(
    image="{unrealircd_image.id}",
    ports={
        "6697/tcp": None,  # Main IRC port (TLS only)
        "8000/tcp": None,  # Plaintext/websocket port for tests using tls=False
    },
    volumes={
        "{prepared_config_dir}": {"bind": "/home/unrealircd/unrealircd/config", "mode": "rw"},
    },
    command=["start"],  # Run server in foreground (entrypoint start case)
    scope="function",
)


def pytest_addoption(parser):
    """Called by pytest, registers CLI options passed to the pytest command."""
    parser.addoption("--controller", help="Which module to use to run the tested software.")
    parser.addoption("--services-controller", help="Which module to use to run a services package.")
    parser.addoption("--openssl-bin", type=str, default="openssl", help="The openssl binary to use")


def pytest_configure(config):
    """Called by pytest, after it parsed the command-line."""
    module_name = config.getoption("controller")
    services_module_name = config.getoption("services_controller")

    if module_name is None:
        # Default to UnrealIRCd controller if not specified
        from .controllers.unrealircd_controller import get_unrealircd_controller_class

        BaseServerTestCase.controllerClass = get_unrealircd_controller_class()
        BaseServerTestCase.show_io = True
        return

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        pytest.exit(f"Cannot import module {module_name}", 1)

    controller_class = module.get_irctest_controller_class()
    if issubclass(controller_class, BaseServerController):
        from . import server_tests as module
    else:
        pytest.exit(
            f"{module_name}.Controller should be a subclass of irctest.basecontroller.BaseServerController",
            1,
        )

    if services_module_name is not None:
        try:
            services_module = importlib.import_module(services_module_name)
        except ImportError:
            pytest.exit(f"Cannot import module {services_module_name}", 1)
        controller_class.services_controller_class = services_module.get_irctest_controller_class()

    BaseServerTestCase.controllerClass = controller_class
    BaseServerTestCase.controllerClass.openssl_bin = config.getoption("openssl_bin")
    BaseServerTestCase.show_io = True


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Provide a Docker client for testing."""
    try:
        client = docker.from_env()
        # Test that Docker is available
        client.ping()
        return client
    except docker.errors.DockerException as e:
        pytest.skip(f"Docker not available: {e}")


# pytest-docker fixtures (automatic Docker Compose management)
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Override default docker-compose.yml location."""
    import os

    return os.path.join(str(pytestconfig.rootdir), "compose.yaml")


@pytest.fixture(scope="session")
def docker_compose_project_name():
    """Generate unique project name for tests."""
    import uuid

    return f"irc_atl_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def docker_setup():
    """Docker compose commands to run before tests."""
    return ["down -v", "up --build -d"]


@pytest.fixture(scope="session")
def docker_cleanup():
    """Docker compose commands to run after tests."""
    return ["down -v"]


def is_irc_service_responsive(host, port=6697):
    """Check if IRC service is responsive."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def irc_service(docker_ip, docker_services):
    """Ensure IRC service is up and responsive."""
    port = docker_services.port_for("unrealircd", 6697)
    url = f"{docker_ip}:{port}"

    docker_services.wait_until_responsive(
        timeout=60.0, pause=1.0, check=lambda: is_irc_service_responsive(docker_ip, port)
    )
    return url


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the IRC app root directory (apps/irc)."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def repo_root(project_root: Path) -> Path:
    """Get the monorepo root directory."""
    return project_root.parent.parent


@pytest.fixture(scope="session")
def compose_file(repo_root: Path) -> Path:
    """Get the root docker-compose file path (single source of truth)."""
    return repo_root / "compose.yaml"


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_config_data() -> dict:
    """Provide sample configuration data for testing."""
    return {
        "irc_server": {
            "host": "localhost",
            "port": 6697,
            "ssl_port": 6697,
            "network_name": "test.network",
        },
        "services": {
            "atheme": {"enabled": True, "port": 8080},
            "webpanel": {"enabled": True, "port": 8081},
        },
    }


@pytest.fixture
def mock_docker_container(mocker):
    """Mock Docker container for testing."""
    mock_container = mocker.Mock()
    mock_container.name = "test_container"
    mock_container.status = "running"
    mock_container.logs.return_value = [b"Test log output"]
    return mock_container


@pytest.fixture
def controller(unrealircd_container):
    """Controller instance with Docker container support."""
    from .controllers.unrealircd_controller import get_unrealircd_controller_class

    controller_class = get_unrealircd_controller_class()
    config = TestCaseControllerConfig()
    return controller_class(config, container_fixture=unrealircd_container)


# Removed autouse controller injection - tests should explicitly request controller fixture when needed


@pytest.fixture
def mock_requests_get(mocker):
    """Mock requests.get for testing HTTP calls."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.text = "OK"

    mock_get = mocker.patch("requests.get")
    mock_get.return_value = mock_response
    return mock_get


class DockerComposeHelper:
    """Helper class for Docker Compose operations in tests."""

    def __init__(self, compose_file: Path, project_root: Path):
        self.compose_file = compose_file
        self.project_root = project_root

    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is running."""
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "compose", "ps", service_name],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            return "Up" in result.stdout
        except Exception:
            return False

    def get_service_logs(self, service_name: str, tail: int = 50) -> str:
        """Get logs from a service."""
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "compose", "logs", "--tail", str(tail), service_name],
                check=False,
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except Exception:
            return ""


@pytest.fixture
def docker_compose_helper(compose_file: Path, repo_root: Path) -> DockerComposeHelper:
    """Provide a Docker Compose helper for tests (uses root compose)."""
    return DockerComposeHelper(compose_file, repo_root)


class IRCTestHelper:
    """Helper class for IRC-related testing operations."""

    def __init__(self, host: str = "localhost", port: int = 6697):
        self.host = host
        self.port = port

    def wait_for_irc_server(self, timeout: int = 30) -> bool:
        """Wait for IRC server to be ready."""
        import socket

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    return True

            except Exception:
                pass

            time.sleep(1)

        return False

    def send_irc_command(self, command: str) -> str | None:
        """Send a command to the IRC server and get response."""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))

            sock.send(f"{command}\r\n".encode())

            response = sock.recv(4096).decode()
            sock.close()

            return response

        except Exception:
            return None


@pytest.fixture
def irc_helper() -> IRCTestHelper:
    """Provide an IRC test helper."""
    return IRCTestHelper()


@pytest.fixture
def mock_irc_connection(mocker):
    """Mock IRC connection for testing."""
    mock_conn = mocker.Mock()
    mock_conn.connect.return_value = True
    mock_conn.send.return_value = None
    mock_conn.receive.return_value = ":server 001 test :Welcome to IRC"
    return mock_conn


class MockIRCClient:
    """Mock IRC client for testing."""

    def __init__(self):
        self.connected = False
        self.messages = []

    def connect(self):
        """Mock connection to IRC server."""
        self.connected = True
        return True

    def send(self, command):
        """Mock sending command."""
        self.messages.append(command)
        return True

    def wait_for_message(self, code=None):
        """Mock waiting for specific message."""
        if code == "001":
            return ":server 001 nick :Welcome to IRC"
        elif code == "432":
            return ":server 432 nick :Erroneous nickname"
        return None

    def disconnect(self):
        """Mock disconnect."""
        self.connected = False


@pytest.fixture
def irc_client():
    """Provide a mock IRC client for testing."""
    return MockIRCClient()


# Configuration for different test environments
@pytest.fixture(params=["minimal", "full"])
def test_config(request, sample_config_data):
    """Provide different test configurations."""
    if request.param == "minimal":
        return {k: v for k, v in sample_config_data.items() if k == "irc_server"}
    return sample_config_data


# Cleanup fixture for tests that create files/directories
@pytest.fixture
def cleanup_files():
    """Fixture to track and cleanup files created during tests."""
    created_files = []
    created_dirs = []

    def track_file(path: Path):
        created_files.append(path)

    def track_dir(path: Path):
        created_dirs.append(path)

    yield track_file, track_dir

    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()

    for dir_path in created_dirs:
        if dir_path.exists():
            import shutil

            shutil.rmtree(dir_path)


# Environment setup fixture
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(repo_root: Path, tmp_path_factory):
    """Setup test environment variables and configuration."""
    # Set test environment
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("DOCKER_COMPOSE_FILE", str(repo_root / "compose.yaml"))

    # Create temporary test directories that get cleaned up automatically
    temp_test_root = tmp_path_factory.mktemp("irc_atl_test")

    # Create temporary test directories
    test_dirs = {
        "data": temp_test_root / "data",
        "logs": temp_test_root / "logs",
        "temp": temp_test_root / "temp",
    }

    for test_dir in test_dirs.values():
        test_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup test environment
    test_env_vars = ["TESTING", "DOCKER_COMPOSE_FILE"]
    for var in test_env_vars:
        os.environ.pop(var, None)


def _inject_controller_if_needed(request):
    """Helper to inject controller only when needed."""
    if hasattr(request.instance, "setup_method"):
        # Check if this is an integration test that needs Docker
        if any(marker in ["integration", "irc", "docker", "atheme", "webpanel"] for marker in request.keywords):
            # Only request controller fixture when actually needed
            controller = request.getfixturevalue("controller")
            request.instance.controller = controller
            # Set up connection details
            container_ports = controller.get_container_ports()
            request.instance.hostname = "localhost"
            request.instance.port = container_ports.get("6697/tcp", 6697)


@pytest.fixture(autouse=True)
def inject_controller(request):
    """Automatically inject controller fixture into test classes that need it."""
    _inject_controller_if_needed(request)
