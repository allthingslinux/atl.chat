"""Monitoring and RPC Tests

Tests for IRC server monitoring and RPC functionality.
Includes both unit tests with mocks and integration tests with controlled server.
"""

import time
from datetime import datetime
from unittest.mock import Mock

import pytest

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications

# Import unrealircd-rpc-py conditionally
try:
    import unrealircd_rpc_py as unrealircd_rpc

    RPC_AVAILABLE = True
except ImportError:
    unrealircd_rpc = None
    RPC_AVAILABLE = False


class UnrealIRCMonitor:
    """Monitor class for UnrealIRCd server health using RPC."""

    def __init__(self, rpc_client):
        self.rpc = rpc_client
        self.last_check = None
        self.health_status = {}

    def check_server_health(self):
        """Check overall server health."""
        try:
            stats = self.rpc.Stats.get()

            health = {
                "timestamp": datetime.now().isoformat(),
                "clients": stats.clients,
                "channels": stats.channels,
                "servers": stats.servers,
                "uptime": stats.uptime,
                "status": "healthy",
            }

            if stats.clients < 0:
                health["status"] = "error"
                health["issues"] = ["Invalid client count"]

            if stats.uptime < 0:
                health["status"] = "error"
                health["issues"] = ["Invalid uptime"]

            self.health_status = health
            self.last_check = datetime.now()

            return health

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    def monitor_user_activity(self):
        """Monitor user activity and connections."""
        try:
            users = self.rpc.User.list()
            current_time = time.time()

            activity = {
                "total_users": len(users),
                "active_connections": len([u for u in users if hasattr(u, "idle_time") and u.idle_time < 300]),
                "idle_connections": len([u for u in users if hasattr(u, "idle_time") and u.idle_time >= 300]),
                "timestamp": datetime.now().isoformat(),
            }

            return activity

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    def monitor_channel_health(self):
        """Monitor channel health and statistics."""
        try:
            channels = self.rpc.Channel.list()

            channel_stats = {
                "total_channels": len(channels),
                "empty_channels": len([c for c in channels if not c.members or len(c.members) == 0]),
                "active_channels": len([c for c in channels if c.members and len(c.members) > 0]),
                "large_channels": len([c for c in channels if c.members and len(c.members) > 50]),
                "timestamp": datetime.now().isoformat(),
            }

            return channel_stats

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    def monitor_security_status(self):
        """Monitor security-related server status."""
        try:
            server_bans = self.rpc.Server_ban.list()
            name_bans = self.rpc.Name_ban.list()
            spam_filters = self.rpc.Spamfilter.list()

            security_stats = {
                "server_bans": len(server_bans),
                "name_bans": len(name_bans),
                "spam_filters": len(spam_filters),
                "active_bans": len(
                    [b for b in server_bans if hasattr(b, "duration") and (b.duration == 0 or b.duration > time.time())]
                ),
                "timestamp": datetime.now().isoformat(),
            }

            return security_stats

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }


class TestUnrealIRCMonitoringUnit:
    """Unit tests for UnrealIRCd monitoring (with mocked RPC)."""

    def test_monitor_creation(self):
        """Test creating a monitoring instance."""
        mock_rpc = Mock()
        monitor = UnrealIRCMonitor(mock_rpc)

        assert monitor.rpc == mock_rpc
        assert monitor.last_check is None
        assert monitor.health_status == {}

    def test_server_health_check(self):
        """Test server health checking."""
        mock_rpc = Mock()
        mock_stats = Mock()
        mock_stats.clients = 42
        mock_stats.channels = 15
        mock_stats.servers = 1
        mock_stats.uptime = 86400

        mock_rpc.Stats.get.return_value = mock_stats

        monitor = UnrealIRCMonitor(mock_rpc)
        health = monitor.check_server_health()

        assert health["status"] == "healthy"
        assert health["clients"] == 42
        assert health["channels"] == 15
        assert health["servers"] == 1
        assert health["uptime"] == 86400
        assert "timestamp" in health

    def test_server_health_error_handling(self):
        """Test health check error handling."""
        mock_rpc = Mock()
        mock_rpc.Stats.get.side_effect = Exception("RPC connection failed")

        monitor = UnrealIRCMonitor(mock_rpc)
        health = monitor.check_server_health()

        assert health["status"] == "error"
        assert "error" in health

    def test_user_activity_monitoring(self):
        """Test user activity monitoring."""
        mock_rpc = Mock()
        mock_users = [Mock(idle_time=i * 60) for i in range(10)]

        mock_rpc.User.list.return_value = mock_users

        monitor = UnrealIRCMonitor(mock_rpc)
        activity = monitor.monitor_user_activity()

        assert activity["total_users"] == 10
        assert activity["active_connections"] == 5  # idle_time < 300 (5 minutes)
        assert activity["idle_connections"] == 5  # idle_time >= 300
        assert "timestamp" in activity

    def test_channel_health_monitoring(self):
        """Test channel health monitoring."""
        mock_rpc = Mock()
        mock_channels = [Mock(members=[f"user{i}" for i in range(j + 1)]) for j in range(15)]

        mock_rpc.Channel.list.return_value = mock_channels

        monitor = UnrealIRCMonitor(mock_rpc)
        channel_stats = monitor.monitor_channel_health()

        assert channel_stats["total_channels"] == 15
        assert channel_stats["empty_channels"] == 0  # No channels with 0 members
        assert channel_stats["active_channels"] == 15  # Channels with members
        assert channel_stats["large_channels"] == 0  # No channel with >50 members
        assert "timestamp" in channel_stats

    def test_security_status_monitoring(self):
        """Test security status monitoring."""
        mock_rpc = Mock()
        mock_server_bans = [Mock(duration=0) for _ in range(5)]
        mock_name_bans = [Mock() for _ in range(3)]
        mock_spam_filters = [Mock() for _ in range(2)]

        mock_rpc.Server_ban.list.return_value = mock_server_bans
        mock_rpc.Name_ban.list.return_value = mock_name_bans
        mock_rpc.Spamfilter.list.return_value = mock_spam_filters

        monitor = UnrealIRCMonitor(mock_rpc)
        security_stats = monitor.monitor_security_status()

        assert security_stats["server_bans"] == 5
        assert security_stats["name_bans"] == 3
        assert security_stats["spam_filters"] == 2
        assert security_stats["active_bans"] == 5  # All have duration=0 (permanent)
        assert "timestamp" in security_stats

    @pytest.fixture
    def mock_monitor(self):
        """Provide a monitor with mock data for testing."""
        mock_rpc = Mock()

        # Mock stats
        mock_stats = Mock()
        mock_stats.clients = 25
        mock_stats.channels = 8
        mock_stats.servers = 1
        mock_stats.uptime = 3600
        mock_rpc.Stats.get.return_value = mock_stats

        # Mock users with various idle times
        mock_users = [Mock(idle_time=i * 300) for i in range(25)]  # Various idle times
        mock_rpc.User.list.return_value = mock_users

        # Mock channels with different member counts
        mock_channels = [Mock(members=[f"user{i}" for i in range(j + 1)]) for j in range(8)]
        mock_rpc.Channel.list.return_value = mock_channels

        # Mock security data
        mock_bans = [Mock(duration=0) for _ in range(5)]
        mock_name_bans = [Mock() for _ in range(2)]
        mock_filters = [Mock() for _ in range(3)]
        mock_rpc.Server_ban.list.return_value = mock_bans
        mock_rpc.Name_ban.list.return_value = mock_name_bans
        mock_rpc.Spamfilter.list.return_value = mock_filters

        monitor = UnrealIRCMonitor(mock_rpc)
        yield monitor

    def test_comprehensive_monitoring(self, mock_monitor):
        """Test comprehensive monitoring functionality."""
        health = mock_monitor.check_server_health()
        activity = mock_monitor.monitor_user_activity()
        channels = mock_monitor.monitor_channel_health()
        security = mock_monitor.monitor_security_status()

        # Verify all monitoring functions work
        assert health["status"] == "healthy"
        assert activity["total_users"] == 25
        assert channels["total_channels"] == 8
        assert security["server_bans"] == 5

        # Verify timestamps are set
        assert mock_monitor.last_check is not None
        assert isinstance(mock_monitor.last_check, datetime)

    @pytest.fixture
    def high_load_monitor(self):
        """Provide a monitor simulating high server load."""
        mock_rpc = Mock()

        # High load stats
        mock_stats = Mock()
        mock_stats.clients = 1000
        mock_stats.channels = 500
        mock_stats.servers = 5
        mock_stats.uptime = 604800  # 1 week
        mock_rpc.Stats.get.return_value = mock_stats

        # Many users
        mock_users = [Mock(idle_time=0) for _ in range(1000)]
        mock_rpc.User.list.return_value = mock_users

        # Many channels
        mock_channels = [Mock(members=[f"user{i}" for i in range(51)]) for _ in range(500)]
        mock_rpc.Channel.list.return_value = mock_channels

        monitor = UnrealIRCMonitor(mock_rpc)
        yield monitor

    def test_high_load_monitoring(self, high_load_monitor):
        """Test monitoring under high load conditions."""
        health = high_load_monitor.check_server_health()
        activity = high_load_monitor.monitor_user_activity()
        channels = high_load_monitor.monitor_channel_health()

        assert health["status"] == "healthy"
        assert health["clients"] == 1000
        assert health["channels"] == 500

        assert activity["total_users"] == 1000
        assert activity["active_connections"] == 1000  # All active

        assert channels["total_channels"] == 500
        assert channels["large_channels"] == 500  # All have >50 members


class TestUnrealIRCMonitoringIntegration(BaseServerTestCase):
    """Integration tests for UnrealIRCd monitoring with controlled server."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = False
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
    @pytest.mark.slow
    def test_monitoring_with_real_server(self):
        """Test monitoring functionality with a real controlled server."""
        # Create some activity on the server first
        client1 = self.connectClient("monitor_test_1")
        client2 = self.connectClient("monitor_test_2")

        test_channel = f"#monitor_test_{int(time.time())}"
        self.joinChannel(client1, test_channel)
        self.joinChannel(client2, test_channel)

        # Send some messages to create activity
        self.sendLine(client1, f"PRIVMSG {test_channel} :Monitoring test message")
        self.sendLine(client2, f"PRIVMSG {test_channel} :Another test message")

        # Verify the server is running and responsive
        assert self.controller.proc is not None
        assert self.controller.port_open

        # Test that our clients are still connected
        self.sendLine(client1, "PING test")
        pong = self.getMessage(client1)
        self.assertMessageMatch(pong, command="PONG", params=["test"])

    @mark_specifications("RFC1459", "RFC2812")
    @pytest.mark.integration
    @pytest.mark.irc
    def test_server_basic_stats_via_irc(self):
        """Test basic server statistics gathering via IRC commands."""
        client = self.connectClient("stats_test")

        # Test LUSERS command for user/server counts
        self.sendLine(client, "LUSERS")
        lusers_response = self.getMessage(client)
        assert lusers_response.command in ["251", "252", "253", "254", "255"]

        # Test TIME command
        self.sendLine(client, "TIME")
        time_response = self.getMessage(client)
        self.assertMessageMatch(time_response, command="391")

        # Test INFO command
        self.sendLine(client, "INFO")
        info_response = self.getMessage(client)
        assert info_response.command in ["371", "374"]


class TestUnrealIRCRPCIntegration(BaseServerTestCase):
    """Integration tests for UnrealIRCd RPC with controlled server."""

    def setup_method(self, method):
        """Override setup to use controller fixture."""
        # Controller will be injected via autouse fixture
        if hasattr(self, "controller") and self.controller is not None:
            # Set default test parameters
            self.password = None
            self.ssl = False
            self.run_services = False
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
    @pytest.mark.slow
    def test_rpc_integration_framework_ready(self):
        """Test that RPC integration framework is ready for controlled server."""
        # Verify server is running
        assert self.controller.port_open

        # Create some IRC activity that RPC could monitor
        client1 = self.connectClient("rpc_test_1")
        client2 = self.connectClient("rpc_test_2")

        test_channel = f"#rpc_test_{int(time.time())}"
        self.joinChannel(client1, test_channel)
        self.joinChannel(client2, test_channel)

        # Send messages
        self.sendLine(client1, f"PRIVMSG {test_channel} :RPC integration test")
        self.sendLine(client2, f"PRIVMSG {test_channel} :Another RPC test")

        # Test server management via standard IRC commands
        self.sendLine(client1, "ADMIN")
        admin_response = self.getMessage(client1)
        assert admin_response.command in ["256", "257", "258", "259"]

        # Test STATS command
        self.sendLine(client1, "STATS u")
        stats_response = self.getMessage(client1)
        assert stats_response.command in ["210", "219", "481"]

        # Test LINKS command
        self.sendLine(client1, "LINKS")
        links_response = self.getMessage(client1)
        assert links_response.command in ["364", "365"]
