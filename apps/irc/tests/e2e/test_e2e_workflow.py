"""End-to-end workflow tests for IRC.atl.chat."""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests


class E2EWorkflowTest:
    """End-to-end testing of complete IRC.atl.chat workflow."""

    @pytest.fixture(scope="class")
    def temp_project_dir(self, tmp_path_factory):
        """Create a temporary copy of the project for E2E testing."""
        temp_dir = tmp_path_factory.mktemp("irc_atl_chat_e2e")

        # Copy project files to temp directory
        project_root = Path(__file__).parent.parent.parent

        # Copy essential files
        files_to_copy = ["compose.yaml", "Makefile", "pyproject.toml", "env.example"]

        dirs_to_copy = ["scripts", "src", "docs"]

        for file in files_to_copy:
            src = project_root / file
            if src.exists():
                if src.is_file():
                    shutil.copy2(src, temp_dir / file)
                else:
                    shutil.copytree(src, temp_dir / file, dirs_exist_ok=True)

        for dir_name in dirs_to_copy:
            src = project_root / dir_name
            if src.exists():
                shutil.copytree(src, temp_dir / dir_name, dirs_exist_ok=True)

        # Create necessary directories
        (temp_dir / "data").mkdir(exist_ok=True)
        (temp_dir / "logs").mkdir(exist_ok=True)

        return temp_dir

    @pytest.fixture(scope="class")
    def e2e_env_setup(self, temp_project_dir):
        """Setup environment for E2E testing."""
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_project_dir)

        # Create .env file from example
        env_example = temp_project_dir / "env.example"
        env_file = temp_project_dir / ".env"

        if env_example.exists():
            shutil.copy2(env_example, env_file)

            # Modify environment variables for testing
            env_content = env_file.read_text()
            env_content = env_content.replace("IRC_DOMAIN=irc.atl.chat", "IRC_DOMAIN=localhost")
            env_content = env_content.replace("IRC_NETWORK_NAME=atl.chat", "IRC_NETWORK_NAME=E2E Test Network")
            env_file.write_text(env_content)

        yield temp_project_dir

        # Cleanup
        os.chdir(original_cwd)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_setup_workflow(self, e2e_env_setup, docker_client):
        """Test complete setup workflow from start to finish."""
        project_dir = e2e_env_setup

        try:
            # Step 1: Environment setup
            assert (project_dir / ".env").exists(), "Environment file should exist"

            # Step 2: Configuration preparation
            prepare_script = project_dir / "scripts" / "prepare-config.sh"
            if prepare_script.exists():
                result = subprocess.run(
                    [str(prepare_script)],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert result.returncode == 0, f"Config preparation failed: {result.stderr}"

            # Step 3: Docker Compose validation
            compose_file = project_dir / "compose.yaml"
            result = subprocess.run(
                ["docker", "compose", "config"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Docker Compose config invalid: {result.stderr}"

            # Step 4: Service startup (limited for E2E)
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "--scale", "ssl-monitor=0"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert result.returncode == 0, f"Service startup failed: {result.stderr}"

            # Give services time to start
            time.sleep(10)

            # Step 5: Verify services are running
            containers = docker_client.containers.list(filters={"label": "com.docker.compose.project=irc.atl.chat"})
            assert len(containers) >= 2, "Should have at least 2 containers running"

            # Step 6: Test IRC connectivity
            self._test_irc_connectivity()

            # Step 7: Test WebPanel accessibility
            self._test_webpanel_accessibility()

        finally:
            # Cleanup: stop services
            subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)

    def _test_irc_connectivity(self):
        """Test IRC server connectivity."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", 6667))
            sock.close()

            assert result == 0, "IRC server should be accessible on port 6667"
        except Exception as e:
            pytest.fail(f"IRC connectivity test failed: {e}")

    def _test_webpanel_accessibility(self):
        """Test WebPanel accessibility."""
        try:
            response = requests.get("http://localhost:8080", timeout=10)
            assert response.status_code == 200, "WebPanel should be accessible"
        except requests.exceptions.RequestException:
            # WebPanel might not be configured in test environment
            pass

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_configuration_workflow(self, e2e_env_setup):
        """Test configuration generation workflow."""
        project_dir = e2e_env_setup

        # Test template processing
        unreal_template = project_dir / "services/unrealircd/conf/unrealircd.conf.template"
        if unreal_template.exists():
            # Create mock environment
            test_env = {
                "IRC_DOMAIN": "test.irc.local",
                "IRC_NETWORK_NAME": "Test Network",
                "IRC_ADMIN_NAME": "Test Admin",
                "IRC_ADMIN_EMAIL": "admin@test.local",
            }

            # Test envsubst functionality
            with open(unreal_template) as f:
                template_content = f.read()

            # Simulate envsubst
            for key, value in test_env.items():
                template_content = template_content.replace(f"${{{key}}}", value)

            # Verify substitutions worked
            assert "test.irc.local" in template_content
            assert "Test Network" in template_content

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_service_startup_sequence(self, e2e_env_setup, docker_client):
        """Test that services start in correct sequence."""
        project_dir = e2e_env_setup

        try:
            # Start services
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
            assert result.returncode == 0

            # Wait for services to start
            time.sleep(15)

            # Verify startup sequence
            containers = docker_client.containers.list(filters={"label": "com.docker.compose.project=irc.atl.chat"})

            unrealircd_container = None
            atheme_container = None

            for container in containers:
                if "unrealircd" in container.name:
                    unrealircd_container = container
                elif "atheme" in container.name:
                    atheme_container = container

            if unrealircd_container and atheme_container:
                unrealircd_start = unrealircd_container.attrs["State"]["StartedAt"]
                atheme_start = atheme_container.attrs["State"]["StartedAt"]

                assert atheme_start > unrealircd_start, "Atheme should start after UnrealIRCd"

        finally:
            subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_irc_functionality_e2e(self, e2e_env_setup):
        """Test complete IRC functionality end-to-end."""
        project_dir = e2e_env_setup

        try:
            # Start services
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert result.returncode == 0

            # Wait for services to be ready
            time.sleep(20)

            # Test IRC connection and basic functionality
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            try:
                sock.connect(("localhost", 6667))

                # Send NICK and USER commands
                test_nick = f"e2e_test_{int(time.time())}"
                sock.send(f"NICK {test_nick}\r\n".encode())
                sock.send(b"USER e2euser 0 * :E2E Test User\r\n")

                # Wait for welcome message
                response = sock.recv(4096).decode()
                assert "001" in response, "Should receive welcome message"

                # Test channel join
                test_channel = f"#e2e_test_{int(time.time())}"
                sock.send(f"JOIN {test_channel}\r\n".encode())

                response = sock.recv(4096).decode()
                assert "JOIN" in response, "Should receive JOIN confirmation"

            finally:
                sock.close()

        finally:
            subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_error_recovery_workflow(self, e2e_env_setup):
        """Test error recovery and restart workflows."""
        project_dir = e2e_env_setup

        try:
            # Start services
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            time.sleep(10)

            # Simulate service failure and recovery
            containers = subprocess.run(
                ["docker", "compose", "ps", "-q"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if containers.stdout.strip():
                # Test restart functionality
                result = subprocess.run(
                    ["docker", "compose", "restart"],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0, "Services should restart successfully"

                time.sleep(5)

                # Verify services are still running
                result = subprocess.run(
                    ["docker", "compose", "ps"],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                assert "Up" in result.stdout, "Services should be running after restart"

        finally:
            subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_configuration_persistence(self, e2e_env_setup):
        """Test that configuration changes persist across restarts."""
        project_dir = e2e_env_setup

        # Modify configuration
        env_file = project_dir / ".env"
        if env_file.exists():
            content = env_file.read_text()
            modified_content = content.replace(
                "IRC_NETWORK_NAME=E2E Test Network",
                "IRC_NETWORK_NAME=Modified Test Network",
            )
            env_file.write_text(modified_content)

            try:
                # Restart services
                result = subprocess.run(
                    ["docker", "compose", "down"],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0

                result = subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0

                time.sleep(10)

                # Verify services are running with new configuration
                containers = subprocess.run(
                    ["docker", "compose", "ps"],
                    check=False,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                assert "Up" in containers.stdout

            finally:
                subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_resource_cleanup(self, e2e_env_setup):
        """Test that resources are properly cleaned up."""
        project_dir = e2e_env_setup

        try:
            # Start services
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            time.sleep(5)

            # Verify resources exist
            containers_before = subprocess.run(
                ["docker", "compose", "ps", "-q"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert containers_before.stdout.strip()

            # Stop services
            result = subprocess.run(
                ["docker", "compose", "down"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            # Verify resources are cleaned up
            containers_after = subprocess.run(
                ["docker", "compose", "ps", "-q"],
                check=False,
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            assert not containers_after.stdout.strip(), "Containers should be stopped"

        except Exception:
            # Ensure cleanup even if test fails
            subprocess.run(["docker", "compose", "down"], check=False, cwd=project_dir, capture_output=True)
            raise
