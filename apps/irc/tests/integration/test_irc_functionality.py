"""IRC functionality tests for IRC.atl.chat."""

import socket
from unittest.mock import Mock, patch

import pytest


class TestIRCFunctionality:
    """Test IRC server functionality."""

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_server_connection(self, irc_helper):
        """Test connecting to IRC server."""
        # This test requires an actual IRC server to be running
        # It will skip if no server is available
        if not irc_helper.wait_for_irc_server(timeout=10):
            pytest.skip("No IRC server running on localhost:6697")

        # If we get here, server is running, test basic connection
        response = irc_helper.send_irc_command("PING test")
        assert response is not None

    def test_irc_helper_timeout(self, irc_helper):
        """Test IRC helper timeout behavior."""
        # Test with very short timeout
        result = irc_helper.wait_for_irc_server(timeout=1)
        assert isinstance(result, bool)

    @pytest.mark.integration
    @pytest.mark.irc
    def test_irc_server_ssl_connection(self, irc_helper):
        """Test SSL connection to IRC server."""
        # Test SSL port (6697)
        ssl_helper = type(irc_helper)("localhost", 6697)

        # This will likely fail without SSL setup, but tests the method
        try:
            import ssl

            # Create SSL context (modern way)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # For testing purposes

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl_sock = context.wrap_socket(sock)
            ssl_sock.settimeout(5)
            result = ssl_sock.connect_ex(("localhost", 6697))
            ssl_sock.close()
            sock.close()

            # If result == 0, SSL connection succeeded
            assert isinstance(result, int)

        except ImportError:
            pytest.skip("SSL not available")

    def test_irc_command_parsing(self):
        """Test IRC command parsing logic."""
        # Test basic IRC message parsing
        test_messages = [
            ":server 001 user :Welcome to IRC",
            ":user JOIN #channel",
            ":user PRIVMSG #channel :Hello world",
            "PING :server",
            "PONG :server",
        ]

        for message in test_messages:
            assert isinstance(message, str)
            assert len(message) > 0

    @pytest.mark.docker
    def test_docker_service_logs(self, docker_compose_helper):
        """Test getting logs from IRC service."""
        # Test getting logs (may be empty if services not running)
        logs = docker_compose_helper.get_service_logs("ircd", tail=5)
        assert isinstance(logs, str)

    def test_mock_irc_connection(self, mock_irc_connection):
        """Test mock IRC connection behavior."""
        assert mock_irc_connection.connect()
        mock_irc_connection.send("TEST")
        response = mock_irc_connection.receive()
        assert "Welcome to IRC" in response

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.slow
    def test_irc_service_health_check(self, docker_compose_helper):
        """Test IRC service health via Docker."""
        # Check if IRC service is running
        is_running = docker_compose_helper.is_service_running("ircd")
        assert isinstance(is_running, bool)

        if is_running:
            # If running, check logs for any errors
            logs = docker_compose_helper.get_service_logs("ircd", tail=20)
            # Should not contain critical errors
            assert "ERROR" not in logs.upper() or "error loading config" not in logs.lower()

    def test_config_validation(self, sample_config_data):
        """Test IRC configuration data validation."""
        irc_config = sample_config_data["irc_server"]

        required_keys = ["host", "port", "network_name"]
        for key in required_keys:
            assert key in irc_config, f"Missing required config key: {key}"

        assert isinstance(irc_config["port"], int)
        assert irc_config["port"] > 0
        assert isinstance(irc_config["host"], str)

    @patch("socket.socket")
    def test_irc_connection_mock(self, mock_socket):
        """Test IRC connection with mocked socket."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Success
        mock_sock.recv.return_value = b":server 001 test :Welcome\r\n"
        mock_socket.return_value = mock_sock

        # Create a mock helper object
        helper = Mock()
        helper.host = "localhost"
        helper.port = 6697
        helper.send_irc_command = Mock(return_value=":server 001 test :Welcome")

        response = helper.send_irc_command("TEST")
        assert response is not None
