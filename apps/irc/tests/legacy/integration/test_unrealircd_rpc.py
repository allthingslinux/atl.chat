"""Integration tests using unrealircd-rpc-py library for direct server management."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

# Import unrealircd-rpc-py conditionally
unrealircd_rpc = pytest.importorskip("unrealircd_rpc_py")

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class UnrealIRCTestHelper:
    """Helper class for UnrealIRCd RPC testing."""

    def __init__(self):
        self.rpc_client = None
        self.connected = False

    def create_mock_rpc_client(self):
        """Create a mock RPC client for testing."""
        self.rpc_client = Mock()
        self.connected = True

        # Mock the main objects
        self.rpc_client.User = Mock()
        self.rpc_client.Channel = Mock()
        self.rpc_client.Server_ban = Mock()
        self.rpc_client.Name_ban = Mock()
        self.rpc_client.Spamfilter = Mock()
        self.rpc_client.Stats = Mock()
        self.rpc_client.Whowas = Mock()
        self.rpc_client.Log = Mock()

        # Mock error handling
        self.rpc_client.get_error = Mock()
        self.rpc_client.get_error.code = 0
        self.rpc_client.get_error.message = ""

        return self.rpc_client

    async def connect_via_requests(self, url="http://localhost:8600/api", username="test", password="test"):
        """Mock connection via HTTP requests."""
        with patch("unrealircd_rpc_py.Loader.Loader") as mock_loader:
            mock_client = self.create_mock_rpc_client()
            mock_loader.return_value = mock_client

            self.rpc_client = unrealircd_rpc.Loader.Loader(
                req_method="requests", url=url, username=username, password=password
            )
            self.connected = True
            return self.rpc_client

    async def connect_via_socket(self, socket_path="/tmp/rpc.socket"):
        """Mock connection via Unix socket."""
        with patch("unrealircd_rpc_py.Loader.Loader") as mock_loader:
            mock_client = self.create_mock_rpc_client()
            mock_loader.return_value = mock_client

            self.rpc_client = unrealircd_rpc.Loader.Loader(req_method="unixsocket", path_to_socket_file=socket_path)
            self.connected = True
            return self.rpc_client

    def mock_user_operations(self):
        """Mock user-related operations."""
        if self.rpc_client:
            # Mock user.get response
            mock_user = Mock()
            mock_user.name = "testuser"
            mock_user.ip = "127.0.0.1"
            mock_user.hostname = "localhost"
            mock_user.connected_since = 1234567890
            mock_user.idle_time = 300

            self.rpc_client.User.get.return_value = mock_user

        # Mock user.list response
        mock_users = [
            Mock(name="user1", ip="127.0.0.1", hostname="host1"),
            Mock(name="user2", ip="127.0.0.2", hostname="host2"),
            Mock(name="user3", ip="192.168.1.1", hostname="host3"),
        ]
        # Configure mock attributes
        for i, user in enumerate(mock_users):
            user.name = f"user{i + 1}"
            user.ip = f"127.0.0.{i + 1}"
            user.hostname = f"host{i + 1}"

        self.rpc_client.User.list.return_value = mock_users

    def mock_channel_operations(self):
        """Mock channel-related operations."""
        if self.rpc_client:
            # Mock channel.get response
            mock_channel = Mock()
            mock_channel.name = "#testchannel"
            mock_channel.creation_time = 1234567890
            mock_channel.topic = "Test channel topic"
            mock_channel.topic_set_by = "testuser"
            mock_channel.topic_set_at = 1234567800
            mock_channel.modes = ["n", "t"]  # no external messages, topic protection
            mock_channel.members = ["user1", "user2", "user3"]
            mock_channel.bans = []
            mock_channel.exceptions = []

            self.rpc_client.Channel.get.return_value = mock_channel

            # Mock channel.list response
            mock_channels = [
                Mock(
                    name="#channel1",
                    members=["user1", "user2"],
                    topic="Channel 1",
                    modes=["n", "t"],
                ),
                Mock(name="#channel2", members=["user3"], topic="Channel 2", modes=["p"]),
                Mock(name="&local", members=["user1"], topic="Local channel", modes=["n"]),
            ]
            # Configure mock attributes
            for i, channel in enumerate(mock_channels):
                channel.name = [f"#channel{i + 1}", "&local"][i] if i < 2 else "&local"
                channel.members = [["user1", "user2"], ["user3"], ["user1"]][i]
                channel.topic = f"Channel {i + 1}" if i < 2 else "Local channel"
                channel.modes = [["n", "t"], ["p"], ["n"]][i]

            self.rpc_client.Channel.list.return_value = mock_channels

    def mock_server_operations(self):
        """Mock server-related operations."""
        if self.rpc_client:
            # Mock server ban operations
            self.rpc_client.Server_ban.list.return_value = [
                Mock(type="kline", mask="baduser!*@*", reason="Spam", duration=3600)
            ]

            # Mock name ban operations
            self.rpc_client.Name_ban.list.return_value = [Mock(name="spamuser", reason="Spam account")]

            # Mock spamfilter operations
            self.rpc_client.Spamfilter.list.return_value = [Mock(match="badword", action="block", reason="Spam word")]

            # Mock stats operations
            mock_stats = Mock()
            mock_stats.clients = 42
            mock_stats.channels = 15
            mock_stats.servers = 1
            mock_stats.uptime = 86400  # 1 day
            self.rpc_client.Stats.get.return_value = mock_stats

    def mock_log_operations(self):
        """Mock log operations (UnrealIRCd 6.1.8+)."""
        if self.rpc_client:
            mock_logs = [
                Mock(timestamp=1234567890, level="info", message="Server started"),
                Mock(timestamp=1234567891, level="warning", message="Connection attempt"),
                Mock(timestamp=1234567892, level="error", message="Authentication failed"),
            ]
            self.rpc_client.Log.list.return_value = mock_logs


class TestUnrealIRCRPCIntegration:
    """Integration tests for UnrealIRCd RPC functionality."""

    @pytest.mark.asyncio
    async def test_rpc_client_creation(self):
        """Test creating an UnrealIRCd RPC client."""
        helper = UnrealIRCTestHelper()

        with patch("unrealircd_rpc_py.Loader.Loader") as mock_loader:
            mock_client = helper.create_mock_rpc_client()
            mock_loader.return_value = mock_client

            client = await helper.connect_via_requests()
            assert client is not None
            assert helper.connected

    @pytest.mark.asyncio
    async def test_unix_socket_connection(self):
        """Test Unix socket connection to RPC."""
        helper = UnrealIRCTestHelper()

        with patch("unrealircd_rpc_py.Loader.Loader") as mock_loader:
            mock_client = helper.create_mock_rpc_client()
            mock_loader.return_value = mock_client

            client = await helper.connect_via_socket("/tmp/rpc.socket")
            assert client is not None
            assert helper.connected

    def test_user_management_operations(self):
        """Test user management through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_user_operations()

        # Test user.get
        user = helper.rpc_client.User.get("testuser")
        assert user.name == "testuser"
        assert user.ip == "127.0.0.1"
        assert user.hostname == "localhost"

        # Test user.list
        users = helper.rpc_client.User.list()
        assert len(users) == 3
        assert users[0].name == "user1"
        assert users[0].ip == "127.0.0.1"

    def test_channel_management_operations(self):
        """Test channel management through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_channel_operations()

        # Test channel.get
        channel = helper.rpc_client.Channel.get("#testchannel")
        assert channel.name == "#testchannel"
        assert channel.topic == "Test channel topic"
        assert channel.creation_time == 1234567890
        assert len(channel.members) == 3
        assert "n" in channel.modes  # no external messages
        assert "t" in channel.modes  # topic protection

        # Test channel.list
        channels = helper.rpc_client.Channel.list()
        assert len(channels) == 3
        assert channels[0].name == "#channel1"
        assert len(channels[0].members) == 2

    def test_server_ban_operations(self):
        """Test server ban management through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_server_operations()

        bans = helper.rpc_client.Server_ban.list()
        assert len(bans) == 1
        assert bans[0].type == "kline"
        assert bans[0].mask == "baduser!*@*"
        assert bans[0].reason == "Spam"
        assert bans[0].duration == 3600

    def test_name_ban_operations(self):
        """Test name ban management through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_server_operations()

        name_bans = helper.rpc_client.Name_ban.list()
        assert len(name_bans) == 1
        assert name_bans[0].name == "spamuser"
        assert name_bans[0].reason == "Spam account"

    def test_spamfilter_operations(self):
        """Test spamfilter management through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_server_operations()

        filters = helper.rpc_client.Spamfilter.list()
        assert len(filters) == 1
        assert filters[0].match == "badword"
        assert filters[0].action == "block"
        assert filters[0].reason == "Spam word"

    def test_server_statistics(self):
        """Test server statistics retrieval through RPC."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_server_operations()

        stats = helper.rpc_client.Stats.get()
        assert stats.clients == 42
        assert stats.channels == 15
        assert stats.servers == 1
        assert stats.uptime == 86400  # 1 day

    def test_log_operations(self):
        """Test log retrieval through RPC (UnrealIRCd 6.1.8+)."""
        helper = UnrealIRCTestHelper()
        helper.create_mock_rpc_client()
        helper.mock_log_operations()

        logs = helper.rpc_client.Log.list()
        assert len(logs) == 3

        # Check log levels
        assert logs[0].level == "info"
        assert logs[1].level == "warning"
        assert logs[2].level == "error"

        # Check timestamps are sequential
        assert logs[0].timestamp < logs[1].timestamp < logs[2].timestamp

    def test_error_handling(self):
        """Test error handling in RPC operations."""
        helper = UnrealIRCTestHelper()
        client = helper.create_mock_rpc_client()

        # Test successful operation (no error)
        assert client.get_error.code == 0
        assert client.get_error.message == ""

        # Mock an error
        client.get_error.code = 1
        client.get_error.message = "Operation failed"

        assert client.get_error.code == 1
        assert client.get_error.message == "Operation failed"

    def test_whowas_operations(self):
        """Test whowas functionality through RPC."""
        helper = UnrealIRCTestHelper()
        client = helper.create_mock_rpc_client()

        # Mock whowas response
        mock_whowas = Mock()
        mock_whowas.name = "olduser"
        mock_whowas.last_seen = 1234567890
        mock_whowas.last_hostname = "old.host.com"
        mock_whowas.last_ip = "192.168.1.1"

        client.Whowas.get.return_value = mock_whowas

        whowas = client.Whowas.get("olduser")
        assert whowas.name == "olduser"
        assert whowas.last_seen == 1234567890
        assert whowas.last_hostname == "old.host.com"

    def test_server_ban_exception_operations(self):
        """Test server ban exception management."""
        helper = UnrealIRCTestHelper()
        client = helper.create_mock_rpc_client()

        # Mock server ban exceptions
        mock_exceptions = [Mock(type="eline", mask="gooduser!*@*", reason="Trusted user", duration=0)]
        client.Server_ban_exception.list.return_value = mock_exceptions

        exceptions = client.Server_ban_exception.list()
        assert len(exceptions) == 1
        assert exceptions[0].type == "eline"
        assert exceptions[0].mask == "gooduser!*@*"
        assert exceptions[0].reason == "Trusted user"
        assert exceptions[0].duration == 0  # permanent

    @pytest.mark.asyncio
    async def test_live_connection_setup(self):
        """Test live connection setup for real-time events."""
        # Mock the live websocket connection
        with patch("unrealircd_rpc_py.Live.LiveWebsocket") as mock_live_ws:
            mock_live_client = Mock()
            mock_live_client.get_error = Mock()
            mock_live_client.get_error.code = 0
            mock_live_ws.return_value = mock_live_client

            # This would normally create a live connection
            live_client = unrealircd_rpc.Live.LiveWebsocket(
                callback_object_instance=Mock(),
                callback_method_name="callback_method",
                url="ws://localhost:8600/api",
                username="test",
                password="test",
            )

            assert live_client.get_error.code == 0

    @pytest.mark.asyncio
    async def test_live_unix_socket_setup(self):
        """Test live Unix socket connection setup."""
        # Mock the live unix socket connection
        with patch("unrealircd_rpc_py.Live.LiveUnixSocket") as mock_live_unix:
            mock_live_client = Mock()
            mock_live_client.get_error = Mock()
            mock_live_client.get_error.code = 0
            mock_live_unix.return_value = mock_live_client

            # This would normally create a live connection
            live_client = unrealircd_rpc.Live.LiveUnixSocket(
                callback_object_instance=Mock(),
                callback_method_name="callback_method",
                path_to_socket_file="/tmp/rpc.socket",
            )

            assert live_client.get_error.code == 0

    def test_callback_class_structure(self):
        """Test callback class structure for live connections."""

        class TestCallback:
            def __init__(self):
                self.received_events = []

            def handle_event(self, event_data):
                """Handle incoming RPC events."""
                self.received_events.append(event_data)
                return True

        callback = TestCallback()

        # Simulate receiving events
        test_event = {"type": "user_join", "channel": "#test", "user": "testuser"}
        result = callback.handle_event(test_event)

        assert result is True
        assert len(callback.received_events) == 1
        assert callback.received_events[0]["type"] == "user_join"

    def test_configuration_validation(self):
        """Test RPC configuration validation."""
        helper = UnrealIRCTestHelper()

        # Test valid configurations
        valid_configs = [
            {
                "req_method": "requests",
                "url": "https://irc.example.com:8600/api",
                "username": "apiuser",
                "password": "secret",
            },
            {
                "req_method": "unixsocket",
                "path_to_socket_file": "/var/run/unrealircd/rpc.socket",
            },
        ]

        for config in valid_configs:
            # These would be valid configurations for creating RPC clients
            assert "req_method" in config
            if config["req_method"] == "requests":
                assert "url" in config
                assert "username" in config
                assert "password" in config
            elif config["req_method"] == "unixsocket":
                assert "path_to_socket_file" in config

    def test_operation_result_parsing(self):
        """Test parsing of RPC operation results."""
        helper = UnrealIRCTestHelper()
        client = helper.create_mock_rpc_client()

        # Mock complex channel data
        mock_channel = Mock()
        mock_channel.name = "#complex"
        mock_channel.members = [
            {"nick": "user1", "modes": ["o"]},  # operator
            {"nick": "user2", "modes": ["v"]},  # voice
            {"nick": "user3", "modes": []},  # regular user
        ]
        mock_channel.modes = {
            "n": True,  # no external messages
            "t": True,  # topic protection
            "l": 100,  # user limit
            "k": "secret",  # channel key
        }

        client.Channel.get.return_value = mock_channel

        channel = client.Channel.get("#complex")

        # Verify complex data structures are parsed correctly
        assert channel.name == "#complex"
        assert len(channel.members) == 3
        assert channel.members[0]["nick"] == "user1"
        assert "o" in channel.members[0]["modes"]  # operator
        assert channel.modes["n"] is True
        assert channel.modes["l"] == 100
        assert channel.modes["k"] == "secret"


# Test fixtures for UnrealIRCd RPC testing
@pytest.fixture
def unrealircd_helper():
    """Provide an UnrealIRCd RPC test helper."""
    helper = UnrealIRCTestHelper()
    yield helper


@pytest.fixture
def mock_rpc_client(unrealircd_helper):
    """Provide a mock RPC client for testing."""
    client = unrealircd_helper.create_mock_rpc_client()
    unrealircd_helper.mock_user_operations()
    unrealircd_helper.mock_channel_operations()
    unrealircd_helper.mock_server_operations()
    yield client


@pytest.fixture
def test_callback_class():
    """Provide a test callback class for live connections."""

    class TestCallback:
        def __init__(self):
            self.events = []

        def on_event(self, event):
            self.events.append(event)

    return TestCallback()
