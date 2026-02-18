"""Unit tests for Docker client functionality."""

from unittest.mock import Mock, patch


class TestDockerClient:
    """Test Docker client operations."""

    def test_docker_client_creation(self, docker_client):
        """Test that Docker client can be created."""
        assert docker_client is not None
        # The docker_client fixture already tests connectivity

    def test_mock_docker_container(self, mock_docker_container):
        """Test mock Docker container behavior."""
        assert mock_docker_container.name == "test_container"
        assert mock_docker_container.status == "running"

        # Test logs method
        logs = mock_docker_container.logs()
        assert logs == [b"Test log output"]

    def test_docker_compose_helper_creation(self, docker_compose_helper):
        """Test Docker Compose helper creation."""
        assert docker_compose_helper is not None
        assert docker_compose_helper.compose_file.exists()

    def test_docker_service_check(self, docker_compose_helper):
        """Test service status checking (requires Docker)."""
        # This would test actual Docker services if running
        # For now, just test the method exists and doesn't crash
        result = docker_compose_helper.is_service_running("nonexistent")
        assert isinstance(result, bool)

    def test_docker_compose_helper_logs_method(self, docker_compose_helper):
        """Test Docker Compose helper logs retrieval."""
        # Test with mock subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Test log output\n", stderr="")

            logs = docker_compose_helper.get_service_logs("test_service")
            assert logs == "Test log output\n"

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "docker" in call_args[0][0]
            assert "compose" in call_args[0][0]
            assert "logs" in call_args[0][0]

    def test_docker_compose_helper_service_running(self, docker_compose_helper):
        """Test service status checking with mocked output."""
        with patch("subprocess.run") as mock_run:
            # Test when service is running
            mock_run.return_value = Mock(
                returncode=0,
                stdout="test_container   Up   10 minutes   0.0.0.0:6667->6667/tcp",
                stderr="",
            )

            result = docker_compose_helper.is_service_running("test_service")
            assert result is True

            # Test when service is not running
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = docker_compose_helper.is_service_running("test_service")
            assert result is False
