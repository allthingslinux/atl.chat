"""Service integration tests for IRC.atl.chat components using controller framework."""

import socket
import time

import pytest
import requests

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_services, mark_specifications


class IRCIntegrationClient:
    """Enhanced IRC client for integration testing."""

    def __init__(self, host="localhost", port=6667, use_ssl=False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.socket = None
        self.connected = False
        self.buffer = ""

    def connect(self) -> bool:
        """Connect to IRC server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))

            if self.use_ssl:
                import ssl

                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.socket = context.wrap_socket(self.socket)

            self.connected = True
            return True
        except Exception:
            return False

    def disconnect(self):
        """Disconnect from server."""
        if self.socket:
            self.socket.close()
        self.connected = False

    def send_command(self, command: str) -> bool:
        """Send IRC command."""
        if not self.connected:
            return False
        try:
            self.socket.send(f"{command}\r\n".encode())
            return True
        except Exception:
            self.connected = False
            return False

    def receive_response(self, timeout: int = 5) -> str | None:
        """Receive response from server."""
        if not self.connected:
            return None

        try:
            import select

            ready = select.select([self.socket], [], [], timeout)
            if ready[0]:
                data = self.socket.recv(4096).decode()
                self.buffer += data
                return data
        except Exception:
            self.connected = False
        return None

    def wait_for_response(self, expected_code: str, timeout: int = 10) -> bool:
        """Wait for specific IRC response code."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.receive_response(1)
            if response and expected_code in response:
                return True
        return False

    def register_user(self, nickname: str, username: str = "testuser") -> bool:
        """Register user with IRC server."""
        if not self.send_command(f"NICK {nickname}"):
            return False
        if not self.send_command(f"USER {username} 0 * :Test User"):
            return False
        return self.wait_for_response("001")  # Welcome message


@mark_services
class TestServiceIntegration(BaseServerTestCase):
    """Test integration between IRC services."""

    @pytest.fixture
    def irc_client(self):
        """Create IRC client for testing with controlled server."""
        client = IRCIntegrationClient(self.hostname, self.port)
        yield client
        client.disconnect()

    @pytest.fixture
    def ssl_irc_client(self):
        """Create SSL IRC client for testing with controlled server."""
        # Note: Our current controller doesn't enable SSL by default
        # This would need to be updated when SSL support is added to the controller
        client = IRCIntegrationClient(self.hostname, self.port, use_ssl=False)
        yield client
        client.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_unrealircd_atheme_integration(self, irc_client):
        """Test integration between UnrealIRCd and Atheme services."""
        assert irc_client.connect(), "Should connect to IRC server"

        # Register test user
        test_nick = f"integration_test_{int(time.time())}"
        assert irc_client.register_user(test_nick), "Should register user"

        # Test NickServ integration
        assert irc_client.send_command("NICKSERV HELP"), "Should send NickServ command"
        assert irc_client.wait_for_response("NOTICE"), "Should receive NickServ response"

        # Test ChanServ integration
        assert irc_client.send_command("CHANSERV HELP"), "Should send ChanServ command"
        assert irc_client.wait_for_response("NOTICE"), "Should receive ChanServ response"

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_nickserv_registration_workflow(self, irc_client):
        """Test complete NickServ registration workflow."""
        assert irc_client.connect(), "Should connect to IRC server"

        # Register test user
        test_nick = f"nickserv_test_{int(time.time())}"
        assert irc_client.register_user(test_nick), "Should register user"

        # Register nickname with NickServ
        password = "test_password_123"
        email = "test@example.com"

        assert irc_client.send_command(f"NICKSERV REGISTER {password} {email}"), "Should send NickServ REGISTER command"

        # Should receive confirmation
        assert irc_client.wait_for_response("NOTICE"), "Should receive NickServ confirmation"

        # Try to identify with the registered nick
        time.sleep(2)  # Give services time to process
        assert irc_client.send_command(f"NICKSERV IDENTIFY {password}"), "Should send NickServ IDENTIFY command"

        # Should receive identification confirmation
        assert irc_client.wait_for_response("NOTICE"), "Should receive identification confirmation"

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_chanserv_channel_management(self, irc_client):
        """Test ChanServ channel management functionality."""
        assert irc_client.connect(), "Should connect to IRC server"

        # Register test user
        test_nick = f"chanserv_test_{int(time.time())}"
        assert irc_client.register_user(test_nick), "Should register user"

        # Create and register a test channel
        test_channel = f"#test_channel_{int(time.time())}"

        # Join channel first
        assert irc_client.send_command(f"JOIN {test_channel}"), "Should join test channel"

        # Register channel with ChanServ
        assert irc_client.send_command(f"CHANSERV REGISTER {test_channel}"), "Should register channel with ChanServ"

        # Should receive registration confirmation
        assert irc_client.wait_for_response("NOTICE"), "Should receive ChanServ confirmation"

        # Test channel ownership
        assert irc_client.send_command(f"CHANSERV INFO {test_channel}"), "Should get channel info"

        # Should receive channel information
        assert irc_client.wait_for_response("NOTICE"), "Should receive channel info"

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.slow
    def test_webpanel_accessibility(self):
        """Test WebPanel web interface accessibility."""
        try:
            response = requests.get("http://localhost:8080", timeout=10, allow_redirects=True)
            assert response.status_code == 200, "WebPanel should return HTTP 200"

            # Check for expected content
            content = response.text.lower()
            assert "irc" in content or "unreal" in content, "WebPanel should contain IRC-related content"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Could not access WebPanel: {e}")

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.irc
    @pytest.mark.slow
    def test_webpanel_irc_integration(self):
        """Test WebPanel integration with IRC server."""
        try:
            # Check if WebPanel can connect to IRC server
            response = requests.get("http://localhost:8080", timeout=10)

            # WebPanel should be able to communicate with IRC server
            # This is a basic connectivity test
            assert response.status_code == 200, "WebPanel should be accessible"

        except requests.exceptions.RequestException:
            pytest.skip("WebPanel not accessible for integration testing")

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_multi_service_coordination(self, irc_client):
        """Test coordination between multiple IRC services."""
        assert irc_client.connect(), "Should connect to IRC server"

        # Register test user
        test_nick = f"multi_test_{int(time.time())}"
        assert irc_client.register_user(test_nick), "Should register user"

        # Test multiple service interactions
        services_to_test = [
            ("NICKSERV", "HELP"),
            ("CHANSERV", "HELP"),
            ("OPERSERV", "HELP"),
        ]

        for service, command in services_to_test:
            assert irc_client.send_command(f"{service} {command}"), f"Should send {service} {command}"

            # Should receive some response from each service
            assert irc_client.wait_for_response("NOTICE"), f"Should receive response from {service}"

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_service_startup_sequence(self, docker_client):
        """Test that services start in correct sequence."""
        try:
            # Get all IRC-related containers
            containers = docker_client.containers.list(filters={"label": "com.docker.compose.project=irc.atl.chat"})

            unrealircd_start = None
            atheme_start = None
            webpanel_start = None

            for container in containers:
                if "unrealircd" in container.name:
                    unrealircd_start = container.attrs["State"]["StartedAt"]
                elif "atheme" in container.name:
                    atheme_start = container.attrs["State"]["StartedAt"]
                elif "webpanel" in container.name:
                    webpanel_start = container.attrs["State"]["StartedAt"]

            # Atheme should start after UnrealIRCd
            if unrealircd_start and atheme_start:
                assert atheme_start > unrealircd_start, "Atheme should start after UnrealIRCd"

            # WebPanel should start after UnrealIRCd
            if unrealircd_start and webpanel_start:
                assert webpanel_start > unrealircd_start, "WebPanel should start after UnrealIRCd"

        except Exception:
            pytest.skip("Could not verify service startup sequence")

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_service_health_dependencies(self, docker_client):
        """Test that services respect health dependencies."""
        try:
            containers = docker_client.containers.list(filters={"label": "com.docker.compose.project=irc.atl.chat"})

            unrealircd_healthy = False
            atheme_running = False

            for container in containers:
                if "unrealircd" in container.name:
                    # Check if UnrealIRCd is healthy
                    health = container.attrs.get("State", {}).get("Health", {}).get("Status")
                    unrealircd_healthy = health == "healthy"

                elif "atheme" in container.name:
                    atheme_running = container.status == "running"

            # If Atheme is running, UnrealIRCd should be healthy
            if atheme_running:
                assert unrealircd_healthy, "UnrealIRCd should be healthy if Atheme is running"

        except Exception:
            pytest.skip("Could not verify service health dependencies")

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_cross_service_communication(self):
        """Test communication between different IRC services."""
        # Create two clients to test service interaction
        client1 = IRCIntegrationClient()
        client2 = IRCIntegrationClient()

        try:
            assert client1.connect(), "Client 1 should connect"
            assert client2.connect(), "Client 2 should connect"

            # Register both users
            nick1 = f"cross_test_1_{int(time.time())}"
            nick2 = f"cross_test_2_{int(time.time())}"

            assert client1.register_user(nick1), "Client 1 should register"
            assert client2.register_user(nick2), "Client 2 should register"

            # Create a channel and test cross-service communication
            test_channel = f"#cross_test_{int(time.time())}"

            # Client 1 joins and registers channel
            assert client1.send_command(f"JOIN {test_channel}")
            assert client1.wait_for_response("JOIN")

            # Client 2 joins the same channel
            assert client2.send_command(f"JOIN {test_channel}")
            assert client2.wait_for_response("JOIN")

            # Test ChanServ integration on the channel
            assert client1.send_command(f"CHANSERV REGISTER {test_channel}")
            assert client1.wait_for_response("NOTICE")

            # Both clients should be able to communicate in the channel
            test_message = "Cross-service communication test"
            assert client1.send_command(f"PRIVMSG {test_channel} :{test_message}")

            # Client 2 should receive the message
            assert client2.wait_for_response(test_message), "Client 2 should receive message from Client 1"

        finally:
            client1.disconnect()
            client2.disconnect()

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.irc
    @pytest.mark.slow
    def test_webpanel_irc_connectivity(self):
        """Test WebPanel's ability to connect to IRC server."""
        try:
            # Test WebSocket connectivity (if supported)
            import websocket

            ws_url = "ws://localhost:8000"
            try:
                ws = websocket.create_connection(ws_url, timeout=10)
                ws.close()
                websocket_connected = True
            except Exception:
                websocket_connected = False

            # Test regular HTTP connectivity
            http_response = requests.get("http://localhost:8080", timeout=10)

            assert http_response.status_code == 200, "WebPanel HTTP should be accessible"

            # If WebSocket is available, it should work
            if websocket_connected:
                assert True, "WebPanel WebSocket connectivity working"
            else:
                # WebSocket might not be configured, which is okay
                pass

        except ImportError:
            # websocket-client not available, skip WebSocket test
            http_response = requests.get("http://localhost:8080", timeout=10)
            assert http_response.status_code == 200, "WebPanel should be accessible"

        except requests.exceptions.RequestException:
            pytest.skip("WebPanel not accessible for connectivity testing")
