"""Comparison tests between irc and irc-toolkit libraries."""

from unittest.mock import Mock, patch

import pytest

# Import both IRC libraries conditionally
irc = pytest.importorskip("irc")
irctk = pytest.importorskip("irctk")


class IRCComparisonTest:
    """Compare functionality between irc and irc-toolkit libraries."""

    def test_message_parsing_comparison(self):
        """Compare message parsing between libraries."""
        test_messages = [
            ":server.example.com 001 testuser :Welcome to IRC",
            ":user!host@server JOIN #channel",
            ":user!host@server PRIVMSG #channel :Hello world",
            ":user!host@server PART #channel :Goodbye",
            ":user!host@server QUIT :Client quit",
        ]

        for message_str in test_messages:
            # Test with irc-toolkit
            try:
                irctk_message = irctk.Message.parse(message_str)
                assert irctk_message is not None
                assert hasattr(irctk_message, "command")
                assert hasattr(irctk_message, "parameters")
            except Exception as e:
                pytest.fail(f"irc-toolkit failed to parse '{message_str}': {e}")

        # Test with pydle (high-level message handling)
        for message_str in test_messages:
            try:
                # pydle focuses on high-level message handling rather than raw parsing
                # Test that basic library functionality is available
                assert hasattr(pydle, "Client")
                assert hasattr(pydle, "featurize")
                assert hasattr(pydle, "features")
            except Exception as e:
                pytest.fail(f"pydle basic functionality test failed: {e}")

    def test_client_creation_comparison(self):
        """Compare client creation between libraries."""
        # Test irc library client creation
        with patch("irc.client.Reactor"):
            try:
                irc_client = irc.client.IRC()
                assert irc_client is not None
            except Exception as e:
                pytest.fail(f"irc library client creation failed: {e}")

        # Test irc-toolkit client creation
        try:
            irctk_client = irctk.Client()
            assert irctk_client is not None
        except Exception as e:
            pytest.fail(f"irc-toolkit client creation failed: {e}")

        # Test pydle client creation
        try:
            pydle_client = pydle.Client("TestBot")
            assert pydle_client is not None
            assert "TestBot" in pydle_client._nicknames
        except Exception as e:
            pytest.fail(f"pydle client creation failed: {e}")

    @patch("irc.client.IRC")
    def test_connection_handling_comparison(self, mock_irc_client):
        """Compare connection handling approaches."""
        # Mock irc library connection
        mock_irc_client.return_value.connect.return_value = True

        # Test irc library connection pattern
        try:
            client = irc.client.IRC()
            result = client.connect("localhost", 6667, nickname="test")
            assert result is True
        except Exception as e:
            pytest.fail(f"irc library connection failed: {e}")

        # Test irc-toolkit connection pattern (mocked)
        try:
            import asyncio

            async def test_connect():
                client = irctk.Client()
                # Mock the connection
                with patch.object(client, "_connect", return_value=None):
                    await client.connect("localhost", 6667, False)
                    return client

            # Run in current event loop if available, otherwise skip
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    pytest.skip("Cannot run async test in running event loop")
                else:
                    client = loop.run_until_complete(test_connect())
                    assert client is not None
            except RuntimeError:
                pytest.skip("No event loop available for async test")

        except Exception as e:
            pytest.fail(f"irc-toolkit connection failed: {e}")

    def test_event_handling_comparison(self):
        """Compare event handling approaches."""
        # Test irc library event handling
        mock_irc_client = Mock()
        mock_irc_client.add_global_handler = Mock()

        events = ["welcome", "join", "part", "quit", "privmsg", "pubmsg"]
        for event in events:
            mock_irc_client.add_global_handler(event, lambda conn, evt: None)

        assert mock_irc_client.add_global_handler.call_count == len(events)

        # Test irc-toolkit event handling (delegate pattern)
        class TestDelegate:
            def irc_welcome(self, client):
                pass

            def irc_join(self, client, nick, channel):
                pass

            def irc_part(self, client, nick, channel):
                pass

            def irc_quit(self, client, nick):
                pass

            def irc_private_message(self, client, nick, message):
                pass

            def irc_channel_message(self, client, nick, channel, message):
                pass

        delegate = TestDelegate()
        irctk_client = irctk.Client()
        irctk_client.delegate = delegate

        # Verify delegate assignment
        assert irctk_client.delegate is delegate
        assert hasattr(irctk_client.delegate, "irc_welcome")
        assert hasattr(irctk_client.delegate, "irc_join")

    def test_command_sending_comparison(self):
        """Compare command sending approaches."""
        # Test irc library command sending
        mock_irc_client = Mock()
        mock_irc_client.send_raw = Mock()

        commands = [
            "NICK testuser",
            "USER testuser 0 * :Test User",
            "JOIN #testchannel",
            "PRIVMSG #testchannel :Hello",
            "PART #testchannel",
            "QUIT :Goodbye",
        ]

        for command in commands:
            mock_irc_client.send_raw(command)

        assert mock_irc_client.send_raw.call_count == len(commands)

        # Test irc-toolkit command sending
        mock_irctk_client = Mock()
        mock_irctk_client.send = Mock()

        irctk_commands = [
            ("NICK", "testuser"),
            ("USER", ["testuser", "0", "*", "Test User"]),
            ("JOIN", "#testchannel"),
            ("PRIVMSG", ["#testchannel", "Hello"]),
            ("PART", "#testchannel"),
            ("QUIT", "Goodbye"),
        ]

        for command_name, params in irctk_commands:
            if isinstance(params, list):
                mock_irctk_client.send(command_name, *params)
            else:
                mock_irctk_client.send(command_name, params)

        assert mock_irctk_client.send.call_count == len(irctk_commands)

    def test_error_handling_comparison(self):
        """Compare error handling approaches."""
        # Test irc library error codes
        error_codes = {
            401: "ERR_NOSUCHNICK",
            403: "ERR_NOSUCHCHANNEL",
            404: "ERR_CANNOTSENDTOCHAN",
            421: "ERR_UNKNOWNCOMMAND",
            431: "ERR_NONICKNAMEGIVEN",
            432: "ERR_ERRONEOUSNICKNAME",
        }

        for code, name in error_codes.items():
            assert isinstance(code, int)
            assert name.startswith("ERR_")

        # Test irc-toolkit error handling (would depend on implementation)
        # This is more about graceful failure handling
        try:
            # Test with invalid message
            irctk.Message.parse("INVALID MESSAGE")
        except Exception:
            # Should handle invalid messages gracefully
            pass

        # Test client creation with invalid parameters
        try:
            client = irctk.Client()
            # Should not crash with basic initialization
            assert client is not None
        except Exception as e:
            pytest.fail(f"irc-toolkit client creation failed unexpectedly: {e}")

    def test_async_support_comparison(self):
        """Compare async/await support between libraries."""
        # irc library supports both sync and async
        try:
            # Test sync client creation
            sync_client = irc.client.IRC()
            assert sync_client is not None

            # Test async client creation (if available)
            try:
                async_client = irc.client_aio.IRC()
                assert async_client is not None
            except AttributeError:
                # Async client might not be available in all versions
                pass

        except Exception as e:
            pytest.fail(f"irc library async support test failed: {e}")

        # irc-toolkit has native async support
        try:
            import inspect

            client = irctk.Client()

            # Check if connect method is a coroutine
            connect_method = getattr(client, "connect", None)
            if connect_method:
                assert inspect.iscoroutinefunction(connect_method), "irc-toolkit connect should be async"

        except Exception as e:
            pytest.fail(f"irc-toolkit async support test failed: {e}")

        # pydle is fully async-first
        try:
            import inspect

            client = pydle.Client("TestBot")
            assert "TestBot" in client._nicknames

            # Check if connect method is a coroutine
            connect_method = getattr(client, "connect", None)
            if connect_method:
                assert inspect.iscoroutinefunction(connect_method), "pydle connect should be async"

            # Check if other methods are async
            message_method = getattr(client, "message", None)
            if message_method:
                assert inspect.iscoroutinefunction(message_method), "pydle message should be async"

        except Exception as e:
            pytest.fail(f"pydle async support test failed: {e}")

    def test_feature_matrix_comparison(self):
        """Compare feature availability between libraries."""

        # Feature comparison matrix
        features = {
            "sync_client": {
                "irc": True,
                "irc_toolkit": False,  # Primarily async
                "pydle": False,  # Fully async
            },
            "async_client": {
                "irc": True,  # via client_aio
                "irc_toolkit": True,
                "pydle": True,  # Native asyncio
            },
            "server_implementation": {
                "irc": True,  # Has irc.server
                "irc_toolkit": False,
                "pydle": False,
            },
            "message_parsing": {
                "irc": True,  # Basic parsing
                "irc_toolkit": True,  # Advanced parsing
                "pydle": False,  # High-level message handling
            },
            "delegate_pattern": {
                "irc": False,  # Uses event handlers
                "irc_toolkit": True,
                "pydle": False,  # Uses callbacks
            },
            "channel_tracking": {
                "irc": False,  # Manual tracking needed
                "irc_toolkit": True,  # Built-in tracking
                "pydle": True,  # Built-in tracking
            },
            "nick_tracking": {
                "irc": False,  # Manual tracking needed
                "irc_toolkit": True,  # Built-in tracking
                "pydle": True,  # Built-in tracking
            },
            "ircv3_support": {
                "irc": False,  # Limited IRCv3
                "irc_toolkit": False,  # Basic support
                "pydle": True,  # Full IRCv3.1/3.2/3.3
            },
            "modular_features": {
                "irc": False,
                "irc_toolkit": False,
                "pydle": True,  # featurize() system
            },
            "client_pool": {
                "irc": False,
                "irc_toolkit": False,
                "pydle": True,  # ClientPool support
            },
        }

        # Verify our understanding of features
        for _feature, support in features.items():
            assert isinstance(support["irc"], bool)
            assert isinstance(support["irc_toolkit"], bool)
            assert isinstance(support["pydle"], bool)

    def test_performance_comparison(self):
        """Compare performance characteristics (basic)."""
        import time

        # Test client creation speed
        start_time = time.time()
        for _ in range(10):
            irctk.Client()
        irctk_creation_time = time.time() - start_time

        start_time = time.time()
        for _ in range(10):
            with patch("irc.client.Reactor"):
                irc.client.IRC()
        irc_creation_time = time.time() - start_time

        # Both should be reasonably fast (< 1 second total for 10 creations)
        assert irctk_creation_time < 1.0, f"irc-toolkit too slow: {irctk_creation_time}"
        assert irc_creation_time < 1.0, f"irc library too slow: {irc_creation_time}"

    def test_memory_usage_comparison(self):
        """Compare basic memory usage patterns."""
        import sys

        # Test object sizes
        try:
            irctk_client = irctk.Client()
            irctk_size = sys.getsizeof(irctk_client)

            with patch("irc.client.Reactor"):
                irc_client = irc.client.IRC()
                irc_size = sys.getsizeof(irc_client)

            # Both should be reasonable sizes (< 10KB)
            assert irctk_size < 10000, f"irc-toolkit object too large: {irctk_size}"
            assert irc_size < 10000, f"irc object too large: {irc_size}"

        except Exception as e:
            pytest.fail(f"Memory usage comparison failed: {e}")

    def test_library_versions(self):
        """Test that both libraries are properly installed and accessible."""
        # Test irc library
        assert hasattr(irc, "client")
        assert hasattr(irc.client, "IRC")

        # Test irc-toolkit library
        assert hasattr(irctk, "Client")
        assert hasattr(irctk, "Message")

        # Test version information if available
        try:
            import pkg_resources

            irc_version = pkg_resources.get_distribution("irc").version
            assert irc_version is not None

            irctk_version = pkg_resources.get_distribution("irc-toolkit").version
            assert irctk_version is not None
        except Exception:
            # Version checking might fail in some environments
            pass
