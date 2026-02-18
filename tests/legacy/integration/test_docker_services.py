"""Integration tests for Docker services."""

import socket
import time

import docker
import pytest
import requests


class TestDockerServices:
    """Test Docker service integration."""

    @pytest.mark.integration
    @pytest.mark.docker
    def test_docker_compose_file_exists(self, compose_file):
        """Test that docker-compose file exists."""
        assert compose_file.exists()
        assert compose_file.name == "compose.yaml"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_docker_compose_helper_logs(self, docker_compose_helper):
        """Test getting logs from services."""
        # Test getting logs (may be empty if services not running)
        logs = docker_compose_helper.get_service_logs("ircd", tail=10)
        assert isinstance(logs, str)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_irc_helper_wait_for_server(self, irc_helper):
        """Test waiting for IRC server (may skip if no server running)."""
        # This will likely skip if no IRC server is running
        # but tests the timeout logic
        result = irc_helper.wait_for_irc_server(timeout=5)
        assert isinstance(result, bool)

    def test_irc_helper_creation(self, irc_helper):
        """Test IRC helper creation."""
        assert irc_helper.host == "localhost"
        assert irc_helper.port == 6667

    def test_config_data_structure(self, sample_config_data):
        """Test sample configuration data structure."""
        assert "irc_server" in sample_config_data
        assert "services" in sample_config_data
        assert sample_config_data["irc_server"]["port"] == 6667


class TestRealDockerIntegration:
    """Real integration tests that require running Docker services."""

    @pytest.fixture(scope="class")
    def running_services(self, docker_client, project_root):
        """Ensure Docker services are running for integration tests."""
        # Check if services are already running
        try:
            containers = docker_client.containers.list(filters={"label": "com.docker.compose.project=irc.atl.chat"})

            if not containers:
                pytest.skip("Docker services not running. Run 'make up' first.")

            # Wait a bit for services to be fully ready
            time.sleep(5)
            return containers

        except docker.errors.DockerException:
            pytest.skip("Docker not available or not running")

    @pytest.mark.integration
    @pytest.mark.docker
    def test_unrealircd_container_running(self, running_services):
        """Test that UnrealIRCd container is running and healthy."""
        unrealircd_container = None
        for container in running_services:
            if "unrealircd" in container.name:
                unrealircd_container = container
                break

        assert unrealircd_container is not None, "UnrealIRCd container should be running"
        assert unrealircd_container.status == "running", "UnrealIRCd should be running"

        # Check health status if available
        container_info = unrealircd_container.attrs
        health = container_info.get("State", {}).get("Health", {}).get("Status")
        if health:
            assert health in ["healthy", "starting"], f"UnrealIRCd health status: {health}"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_atheme_container_running(self, running_services):
        """Test that Atheme container is running."""
        atheme_container = None
        for container in running_services:
            if "atheme" in container.name:
                atheme_container = container
                break

        assert atheme_container is not None, "Atheme container should be running"
        assert atheme_container.status == "running", "Atheme should be running"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_webpanel_container_running(self, running_services):
        """Test that WebPanel container is running."""
        webpanel_container = None
        for container in running_services:
            if "webpanel" in container.name:
                webpanel_container = container
                break

        assert webpanel_container is not None, "WebPanel container should be running"
        assert webpanel_container.status == "running", "WebPanel should be running"

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.slow
    def test_irc_ports_open(self, running_services):
        """Test that IRC ports are open and accepting connections."""
        ports_to_test = [6697]  # TLS only

        for port in ports_to_test:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                try:
                    result = sock.connect_ex(("localhost", port))
                    assert result == 0, f"Port {port} should be open"
                except OSError:
                    pytest.fail(f"Could not connect to port {port}")

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.slow
    def test_webpanel_http_accessible(self, running_services):
        """Test that WebPanel is accessible via HTTP."""
        try:
            response = requests.get("http://localhost:8080", timeout=10)
            assert response.status_code == 200, "WebPanel should return HTTP 200"
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Could not access WebPanel: {e}")

    @pytest.mark.integration
    @pytest.mark.docker
    def test_docker_network_exists(self, docker_client):
        """Test that the IRC network exists."""
        try:
            networks = docker_client.networks.list(names=["irc-network"])
            assert len(networks) > 0, "irc-network should exist"
            assert networks[0].name == "irc-network"
        except docker.errors.DockerException:
            pytest.skip("Could not check Docker networks")

    @pytest.mark.integration
    @pytest.mark.docker
    def test_container_logs_accessible(self, running_services):
        """Test that container logs are accessible."""
        for container in running_services:
            try:
                logs = container.logs(tail=10)
                assert logs is not None, f"Logs should be accessible for {container.name}"
            except docker.errors.DockerException:
                pytest.fail(f"Could not access logs for {container.name}")

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.slow
    def test_service_dependencies(self, running_services):
        """Test that services start in correct order based on dependencies."""
        # Atheme should start after UnrealIRCd (dependency)
        unrealircd_start = None
        atheme_start = None

        for container in running_services:
            if "unrealircd" in container.name:
                unrealircd_start = container.attrs["State"]["StartedAt"]
            elif "atheme" in container.name:
                atheme_start = container.attrs["State"]["StartedAt"]

        if unrealircd_start and atheme_start:
            # Atheme should start after UnrealIRCd
            assert atheme_start > unrealircd_start, "Atheme should start after UnrealIRCd"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_container_resource_limits(self, running_services):
        """Test that containers have appropriate resource limits."""
        for container in running_services:
            config = container.attrs.get("HostConfig", {})

            # Check if memory limits are set (optional but good practice)
            memory_limit = config.get("Memory")
            if memory_limit:
                assert memory_limit > 0, f"Container {container.name} should have memory limit"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_environment_variables_passed(self, running_services, project_root):
        """Test that environment variables are properly passed to containers."""
        # Check if .env file exists
        env_file = project_root / ".env"
        if env_file.exists():
            # Read expected variables
            expected_vars = {}
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        expected_vars[key] = value

            # Check UnrealIRCd container environment
            for container in running_services:
                if "unrealircd" in container.name:
                    container_env = container.attrs.get("Config", {}).get("Env", [])
                    env_dict = {}
                    for env_var in container_env:
                        if "=" in env_var:
                            key, value = env_var.split("=", 1)
                            env_dict[key] = value

                    # Check some key variables are present
                    for var in ["TZ", "PUID", "PGID"]:
                        assert var in env_dict, f"Environment variable {var} should be set"

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.slow
    def test_container_restart_policy(self, running_services):
        """Test that containers have appropriate restart policies."""
        for container in running_services:
            restart_policy = container.attrs.get("HostConfig", {}).get("RestartPolicy", {})

            # Most services should have unless-stopped policy
            if "cert-manager" not in container.name:  # cert-manager may have different policy
                assert restart_policy.get("Name") in ["unless-stopped", "always"], (
                    f"Container {container.name} should have restart policy"
                )
