"""Service Integration Tests

Tests for IRC services integration including NickServ, ChanServ, and Atheme.
Uses controlled server with services enabled.
"""

import socket
import time

import pytest
import requests

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_services, mark_specifications


class IRCIntegrationClient:
    """Enhanced IRC client for service integration testing."""

    def __init__(self, host: str = "localhost", port: int = 6697, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.socket = None
        self.connected = False
        self.buffer = ""
        self.messages = []
        self.events = []
        self.nickname = None

    def connect(self, nickname: str | None = None) -> bool:
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

            self.nickname = nickname or f"testuser_{int(time.time())}"
            self.send_command(f"NICK {self.nickname}")
            self.send_command("USER testuser 0 * :Test User")

            response = self.socket.recv(4096).decode()
            if "001" in response:
                self.connected = True
                return True

        except Exception:
            return False

        return False

    def disconnect(self):
        """Disconnect from server."""
        if self.socket:
            self.socket.close()
        self.connected = False

    def send_command(self, command: str) -> bool:
        """Send IRC command."""
        if not self.socket:
            return False
        try:
            self.socket.send(f"{command}\r\n".encode())
            return True
        except Exception:
            return False

    def wait_for_response(self, expected_text: str, timeout: int = 5) -> bool:
        """Wait for specific response text."""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                data = self.socket.recv(4096).decode()
                if expected_text in data:
                    return True
            except:
                pass
            time.sleep(0.1)
        return False


@mark_services
class TestNickServIntegration(BaseServerTestCase):
    """Test NickServ functionality with controlled server and services."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = True  # Enable services for service tests
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_nickserv_registration_workflow(self):
        """Test complete NickServ registration workflow."""
        test_nick = f"nickserv_test_{int(time.time())}"
        password = "testpass123"

        client = IRCIntegrationClient(self.hostname, self.port)
        try:
            assert client.connect(test_nick)
            time.sleep(2)

            # Register nickname
            email = "test@example.com"
            assert client.send_command(f"NICKSERV REGISTER {password} {email}")

            # Should receive confirmation
            assert client.wait_for_response("NOTICE", timeout=10)

            # Try to identify with the registered nick
            time.sleep(2)
            assert client.send_command(f"NICKSERV IDENTIFY {password}")

            # Should receive identification confirmation
            assert client.wait_for_response("NOTICE", timeout=10)
        finally:
            client.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_nickserv_ghost_command(self):
        """Test NickServ GHOST command."""
        test_nick = f"ghost_test_{int(time.time())}"
        password = "ghostpass123"

        client = IRCIntegrationClient(self.hostname, self.port)
        try:
            assert client.connect(test_nick)
            time.sleep(2)

            # Register the nickname first
            email = "ghost@example.com"
            assert client.send_command(f"NICKSERV REGISTER {password} {email}")
            time.sleep(3)

            # Try GHOST command (should work even without ghost present)
            assert client.send_command(f"NICKSERV GHOST {test_nick}")
            # Should receive some response
            assert client.wait_for_response("NOTICE", timeout=10)
        finally:
            client.disconnect()


@mark_services
class TestChanServIntegration(BaseServerTestCase):
    """Test ChanServ functionality with controlled server and services."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = True  # Enable services for service tests
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_chanserv_channel_registration(self):
        """Test ChanServ channel registration."""
        test_nick = f"chanserv_user_{int(time.time())}"
        test_channel = f"#chanserv_test_{int(time.time())}"

        client = IRCIntegrationClient(self.hostname, self.port)
        try:
            assert client.connect(test_nick)
            time.sleep(2)

            # Join channel first
            assert client.send_command(f"JOIN {test_channel}")
            time.sleep(2)

            # Register channel with ChanServ
            assert client.send_command(f"CHANSERV REGISTER {test_channel}")

            # Should receive registration confirmation
            assert client.wait_for_response("NOTICE", timeout=10)
        finally:
            client.disconnect()

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_chanserv_channel_info(self):
        """Test ChanServ INFO command."""
        test_nick = f"chanserv_info_{int(time.time())}"
        test_channel = f"#chanserv_info_{int(time.time())}"

        client = IRCIntegrationClient(self.hostname, self.port)
        try:
            assert client.connect(test_nick)
            time.sleep(2)

            # Join and register channel
            assert client.send_command(f"JOIN {test_channel}")
            time.sleep(2)
            assert client.send_command(f"CHANSERV REGISTER {test_channel}")
            time.sleep(3)

            # Get channel info
            assert client.send_command(f"CHANSERV INFO {test_channel}")

            # Should receive channel information
            assert client.wait_for_response("NOTICE", timeout=10)
        finally:
            client.disconnect()


@mark_services
class TestServiceIntegration(BaseServerTestCase):
    """Test overall service integration and coordination."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = True  # Enable services for service tests
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_unrealircd_atheme_integration(self):
        """Test integration between UnrealIRCd and Atheme services."""
        # Create test clients
        client1 = self.connectClient("integration_test_1")
        client2 = self.connectClient("integration_test_2")

        test_channel = f"#integration_{int(time.time())}"

        # Both clients join channel
        self.joinChannel(client1, test_channel)
        self.joinChannel(client2, test_channel)

        # Send test messages
        self.sendLine(client1, f"PRIVMSG {test_channel} :Integration test message")
        self.sendLine(client2, f"PRIVMSG {test_channel} :Response message")

        # Test NickServ
        self.sendLine(client1, "NICKSERV HELP")
        nickserv_response = self.getMessage(client1)
        # Should get some response from NickServ
        assert nickserv_response

        # Test ChanServ
        self.sendLine(client1, "CHANSERV HELP")
        chanserv_response = self.getMessage(client1)
        # Should get some response from ChanServ
        assert chanserv_response

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.atheme
    @pytest.mark.slow
    def test_multi_service_coordination(self):
        """Test coordination between multiple services."""
        client = self.connectClient("coordination_test")

        services_to_test = [
            ("NICKSERV", "HELP"),
            ("CHANSERV", "HELP"),
        ]

        for service, command in services_to_test:
            self.sendLine(client, f"{service} {command}")
            response = self.getMessage(client)
            # Should receive response from each service
            assert response.command in {"NOTICE", "PRIVMSG"}


class TestWebPanelIntegration(BaseServerTestCase):
    """Test WebPanel integration (may require separate WebPanel service)."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = True  # Enable services for service tests
            self.faketime = None
            self.server_support = None

            # Run the controller (hostname/port already set by inject_controller fixture)
            self.controller.run(
                self.hostname,
                self.port,
                password=self.password,
                ssl=self.ssl,
                run_services=self.run_services,
                faketime=self.faketime,
            )

        self.clients = {}

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_accessibility(self):
        """Test WebPanel web interface accessibility."""
        try:
            response = requests.get("http://localhost:8080", timeout=10, allow_redirects=True)
            assert response.status_code == 200
            content = response.text.lower()
            assert "irc" in content or "unreal" in content
        except requests.exceptions.RequestException:
            pytest.skip("WebPanel not available for testing")

    @pytest.mark.integration
    @pytest.mark.irc
    @pytest.mark.webpanel
    @pytest.mark.slow
    def test_webpanel_irc_integration(self):
        """Test WebPanel IRC integration."""
        # Create some IRC activity
        client = self.connectClient("webpanel_test")
        test_channel = f"#webpanel_{int(time.time())}"

        self.joinChannel(client, test_channel)
        self.sendLine(client, f"PRIVMSG {test_channel} :WebPanel integration test")

        # WebPanel should potentially show this activity
        # (This is a basic connectivity test - full WebPanel testing
        # would require WebPanel to be running and configured)
        try:
            response = requests.get("http://localhost:8080", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("WebPanel not available for integration testing")
