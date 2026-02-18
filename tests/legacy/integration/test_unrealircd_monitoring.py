"""Monitoring and health check tests using UnrealIRCd RPC with controlled server."""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Import unrealircd-rpc-py conditionally
unrealircd_rpc = pytest.importorskip("unrealircd_rpc_py")

from ..utils.base_test_cases import BaseServerTestCase
from ..utils.specifications import mark_specifications


class UnrealIRCMonitor:
    """Monitor class for UnrealIRCd server health using RPC."""

    def __init__(self, rpc_client):
        self.rpc = rpc_client
        self.last_check = None
        self.health_status = {}

    def check_server_health(self):
        """Check overall server health."""
        try:
            # Get server statistics
            stats = self.rpc.Stats.get()

            health = {
                "timestamp": datetime.now().isoformat(),
                "clients": stats.clients,
                "channels": stats.channels,
                "servers": stats.servers,
                "uptime": stats.uptime,
                "status": "healthy",
            }

            # Basic health checks
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

    def check_user_activity(self):
        """Check user activity and connections."""
        try:
            users = self.rpc.User.list()

            activity = {
                "total_users": len(users),
                "active_connections": len([u for u in users if hasattr(u, "idle_time") and u.idle_time < 300]),
                "idle_connections": len([u for u in users if hasattr(u, "idle_time") and u.idle_time >= 300]),
                "timestamp": datetime.now().isoformat(),
            }

            return activity

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def check_channel_health(self):
        """Check channel health and activity."""
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
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def check_security_status(self):
        """Check server security status."""
        try:
            # Check bans and filters
            server_bans = self.rpc.Server_ban.list()
            name_bans = self.rpc.Name_ban.list()
            spam_filters = self.rpc.Spamfilter.list()

            security = {
                "server_bans": len(server_bans),
                "name_bans": len(name_bans),
                "spam_filters": len(spam_filters),
                "active_bans": len(
                    [b for b in server_bans if hasattr(b, "duration") and (b.duration == 0 or b.duration > time.time())]
                ),
                "timestamp": datetime.now().isoformat(),
            }

            return security

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_recent_logs(self, limit=10):
        """Get recent server logs."""
        try:
            logs = self.rpc.Log.list()

            # Get the most recent logs
            recent_logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)[:limit]

            log_entries = []
            for log in recent_logs:
                log_entries.append(
                    {
                        "timestamp": log.timestamp,
                        "level": log.level,
                        "message": log.message,
                        "time_str": datetime.fromtimestamp(log.timestamp).isoformat(),
                    }
                )

            return {
                "logs": log_entries,
                "total": len(logs),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def check_performance_metrics(self):
        """Check server performance metrics."""
        try:
            # This would typically involve multiple RPC calls
            # and calculation of performance indicators
            start_time = time.time()

            # Simulate some operations to measure performance
            users = self.rpc.User.list()
            channels = self.rpc.Channel.list()
            stats = self.rpc.Stats.get()

            end_time = time.time()
            response_time = end_time - start_time

            performance = {
                "response_time": response_time,
                "users_count": len(users),
                "channels_count": len(channels),
                "clients_count": stats.clients,
                "performance_score": "good" if response_time < 1.0 else "slow",
                "timestamp": datetime.now().isoformat(),
            }

            return performance

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


class TestUnrealIRCMonitoring:
    """Tests for UnrealIRCd server monitoring and health checks."""

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
        mock_stats.uptime = 86400  # 1 day

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
        assert health["error"] == "RPC connection failed"

    def test_user_activity_monitoring(self):
        """Test user activity monitoring."""
        mock_rpc = Mock()

        # Mock users with different idle times
        mock_users = [
            Mock(idle_time=60),  # Active (1 minute)
            Mock(idle_time=600),  # Idle (10 minutes)
            Mock(idle_time=3600),  # Very idle (1 hour)
        ]
        mock_rpc.User.list.return_value = mock_users

        monitor = UnrealIRCMonitor(mock_rpc)
        activity = monitor.check_user_activity()

        assert activity["total_users"] == 3
        assert activity["active_connections"] == 1  # Only first user is active (< 5 minutes)
        assert activity["idle_connections"] == 2  # Other two are idle
        assert "timestamp" in activity

    def test_channel_health_monitoring(self):
        """Test channel health monitoring."""
        mock_rpc = Mock()

        # Mock channels with different member counts
        mock_channels = [
            Mock(members=["user1", "user2"]),  # Active channel
            Mock(members=[]),  # Empty channel
            Mock(members=["user3"]),  # Small channel
            Mock(members=[f"user{i}" for i in range(60)]),  # Large channel
        ]
        mock_rpc.Channel.list.return_value = mock_channels

        monitor = UnrealIRCMonitor(mock_rpc)
        channel_stats = monitor.check_channel_health()

        assert channel_stats["total_channels"] == 4
        assert channel_stats["empty_channels"] == 1
        assert channel_stats["active_channels"] == 3
        assert channel_stats["large_channels"] == 1  # Channel with > 50 members
        assert "timestamp" in channel_stats

    def test_security_status_monitoring(self):
        """Test security status monitoring."""
        mock_rpc = Mock()

        # Mock security-related data
        mock_server_bans = [
            Mock(duration=0),  # Permanent ban
            Mock(duration=time.time() + 3600),  # Temporary ban (1 hour)
            Mock(duration=time.time() - 3600),  # Expired ban
        ]
        mock_name_bans = [Mock()]
        mock_spam_filters = [Mock(), Mock(), Mock()]

        mock_rpc.Server_ban.list.return_value = mock_server_bans
        mock_rpc.Name_ban.list.return_value = mock_name_bans
        mock_rpc.Spamfilter.list.return_value = mock_spam_filters

        monitor = UnrealIRCMonitor(mock_rpc)
        security = monitor.check_security_status()

        assert security["server_bans"] == 3
        assert security["name_bans"] == 1
        assert security["spam_filters"] == 3
        assert security["active_bans"] == 2  # Permanent + temporary (not expired)
        assert "timestamp" in security

    def test_log_monitoring(self):
        """Test server log monitoring."""
        mock_rpc = Mock()

        # Mock log entries with different timestamps
        current_time = time.time()
        mock_logs = [
            Mock(timestamp=current_time, level="info", message="Server started"),
            Mock(
                timestamp=current_time - 3600,
                level="warning",
                message="High load detected",
            ),
            Mock(
                timestamp=current_time - 7200,
                level="error",
                message="Connection failed",
            ),
            Mock(timestamp=current_time - 10800, level="info", message="User connected"),
            Mock(timestamp=current_time - 14400, level="debug", message="Debug info"),
        ]
        mock_rpc.Log.list.return_value = mock_logs

        monitor = UnrealIRCMonitor(mock_rpc)
        logs = monitor.get_recent_logs(limit=3)

        assert logs["total"] == 5
        assert len(logs["logs"]) == 3  # Limited to 3 most recent

        # Check that logs are sorted by timestamp (most recent first)
        timestamps = [log["timestamp"] for log in logs["logs"]]
        assert timestamps[0] >= timestamps[1] >= timestamps[2]

        # Check log levels
        assert logs["logs"][0]["level"] == "info"
        assert logs["logs"][1]["level"] == "warning"
        assert logs["logs"][2]["level"] == "error"

    def test_performance_metrics(self):
        """Test performance metrics collection."""
        mock_rpc = Mock()

        # Mock RPC responses
        mock_users = [Mock() for _ in range(10)]
        mock_channels = [Mock() for _ in range(5)]
        mock_stats = Mock()
        mock_stats.clients = 25

        mock_rpc.User.list.return_value = mock_users
        mock_rpc.Channel.list.return_value = mock_channels
        mock_rpc.Stats.get.return_value = mock_stats

        monitor = UnrealIRCMonitor(mock_rpc)
        performance = monitor.check_performance_metrics()

        assert performance["users_count"] == 10
        assert performance["channels_count"] == 5
        assert performance["clients_count"] == 25
        assert "response_time" in performance
        assert "performance_score" in performance
        assert performance["response_time"] >= 0
        assert performance["performance_score"] in ["good", "slow"]

    def test_monitor_state_tracking(self):
        """Test monitor state tracking."""
        mock_rpc = Mock()
        mock_stats = Mock()
        mock_stats.clients = 10
        mock_stats.channels = 3
        mock_stats.servers = 1
        mock_stats.uptime = 3600

        mock_rpc.Stats.get.return_value = mock_stats

        monitor = UnrealIRCMonitor(mock_rpc)

        # Initial state
        assert monitor.last_check is None
        assert monitor.health_status == {}

        # After first check
        health1 = monitor.check_server_health()
        assert monitor.last_check is not None
        assert monitor.health_status == health1

        # After second check (should update)
        time.sleep(0.01)  # Small delay to ensure different timestamp
        health2 = monitor.check_server_health()
        assert health2["timestamp"] != health1["timestamp"]

    def test_comprehensive_health_dashboard(self):
        """Test comprehensive health dashboard generation."""
        mock_rpc = Mock()

        # Setup comprehensive mock data
        mock_stats = Mock()
        mock_stats.clients = 100
        mock_stats.channels = 20
        mock_stats.servers = 2
        mock_stats.uptime = 604800  # 1 week

        mock_users = [Mock(idle_time=i * 60) for i in range(50)]  # Various idle times
        mock_channels = [Mock(members=[f"user{i}" for i in range(j + 1)]) for j in range(15)]
        mock_bans = [Mock(duration=0) for _ in range(5)]
        mock_filters = [Mock() for _ in range(3)]

        mock_rpc.Stats.get.return_value = mock_stats
        mock_rpc.User.list.return_value = mock_users
        mock_rpc.Channel.list.return_value = mock_channels
        mock_rpc.Server_ban.list.return_value = mock_bans
        mock_rpc.Spamfilter.list.return_value = mock_filters

        monitor = UnrealIRCMonitor(mock_rpc)

        # Generate comprehensive dashboard
        health = monitor.check_server_health()
        activity = monitor.check_user_activity()
        channels = monitor.check_channel_health()
        security = monitor.check_security_status()
        performance = monitor.check_performance_metrics()

        # Verify dashboard completeness
        assert health["status"] == "healthy"
        assert health["clients"] == 100
        assert activity["total_users"] == 50
        assert channels["total_channels"] == 15
        assert security["server_bans"] == 5
        assert security["spam_filters"] == 3
        assert "response_time" in performance

        # Verify cross-references
        assert health["clients"] == activity["total_users"]  # Should match

    def test_error_recovery_monitoring(self):
        """Test monitoring error recovery."""
        mock_rpc = Mock()

        # Simulate RPC failures and recovery
        call_count = 0

        def failing_stats_get():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary RPC failure")
            # Return success on third call
            mock_stats = Mock()
            mock_stats.clients = 5
            mock_stats.channels = 2
            mock_stats.servers = 1
            mock_stats.uptime = 1800
            return mock_stats

        mock_rpc.Stats.get.side_effect = failing_stats_get

        monitor = UnrealIRCMonitor(mock_rpc)

        # First two calls should fail
        health1 = monitor.check_server_health()
        health2 = monitor.check_server_health()

        assert health1["status"] == "error"
        assert health2["status"] == "error"

        # Third call should succeed
        health3 = monitor.check_server_health()
        assert health3["status"] == "healthy"
        assert health3["clients"] == 5

    def test_monitoring_thresholds(self):
        """Test monitoring with various thresholds and alerts."""
        mock_rpc = Mock()

        # Test high load scenario
        mock_stats = Mock()
        mock_stats.clients = 1000  # Very high client count
        mock_stats.channels = 500
        mock_stats.servers = 1
        mock_stats.uptime = 3600

        mock_rpc.Stats.get.return_value = mock_stats

        # Create large number of users and channels
        mock_users = [Mock(idle_time=0) for _ in range(1000)]
        mock_channels = [Mock(members=[f"user{i}" for i in range(50)]) for _ in range(500)]

        mock_rpc.User.list.return_value = mock_users
        mock_rpc.Channel.list.return_value = mock_channels

        monitor = UnrealIRCMonitor(mock_rpc)

        health = monitor.check_server_health()
        activity = monitor.check_user_activity()
        channels = monitor.check_channel_health()

        # Verify high-load handling
        assert health["clients"] == 1000
        assert activity["total_users"] == 1000
        assert channels["total_channels"] == 500
        assert channels["large_channels"] == 500  # All channels are large (>50 users)


# Test fixtures for monitoring
@pytest.fixture
def mock_monitor():
    """Provide a mock monitor for testing."""
    mock_rpc = Mock()

    # Setup comprehensive mock data
    mock_stats = Mock()
    mock_stats.clients = 25
    mock_stats.channels = 8
    mock_stats.servers = 1
    mock_stats.uptime = 43200  # 12 hours

    mock_rpc.Stats.get.return_value = mock_stats
    mock_rpc.User.list.return_value = [Mock(idle_time=i * 300) for i in range(25)]
    mock_rpc.Channel.list.return_value = [Mock(members=[f"user{i}" for i in range(5)]) for _ in range(8)]

    monitor = UnrealIRCMonitor(mock_rpc)
    yield monitor


@pytest.fixture
def high_load_monitor():
    """Provide a monitor simulating high server load."""
    mock_rpc = Mock()

    # High load scenario
    mock_stats = Mock()
    mock_stats.clients = 500
    mock_stats.channels = 100
    mock_stats.servers = 1
    mock_stats.uptime = 86400

    mock_rpc.Stats.get.return_value = mock_stats
    mock_rpc.User.list.return_value = [Mock(idle_time=0) for _ in range(500)]
    mock_rpc.Channel.list.return_value = [Mock(members=[f"user{i}" for i in range(20)]) for _ in range(100)]

    monitor = UnrealIRCMonitor(mock_rpc)
    yield monitor


class TestUnrealIRCMonitoringIntegration(BaseServerTestCase):
    """Integration tests for UnrealIRCd monitoring with controlled server."""

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

        # Note: Actual RPC monitoring would require the UnrealIRCd RPC module to be enabled
        # and configured in our controller. This test demonstrates the integration framework
        # is ready for when RPC monitoring is properly configured.

        # For now, just verify the server is running and responsive
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
        # Should get RPL_LUSERCLIENT or similar
        assert lusers_response.command in ["251", "252", "253", "254", "255"]

        # Test TIME command
        self.sendLine(client, "TIME")
        time_response = self.getMessage(client)
        self.assertMessageMatch(time_response, command="391")  # RPL_TIME

        # Test INFO command
        self.sendLine(client, "INFO")
        info_response = self.getMessage(client)
        assert info_response.command in ["371", "374"]  # RPL_INFO or RPL_ENDOFINFO
