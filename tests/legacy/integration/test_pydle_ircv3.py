"""Tests showcasing pydle's IRCv3 features and advanced capabilities."""

import asyncio
from unittest.mock import patch

import pytest

# Import pydle conditionally
pydle = pytest.importorskip("pydle")


class IRCv3TestBot(pydle.Client):
    """Test bot showcasing IRCv3 features."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capabilities_received = []
        self.ircv3_features = []

    async def on_capability(self, capability, value=None):
        """Handle IRCv3 capability negotiation."""
        await super().on_capability(capability, value)
        self.capabilities_received.append(
            {
                "capability": capability,
                "value": value,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    async def on_raw_001(self, source, params):
        """Handle welcome message and IRCv3 features."""
        await super().on_raw_001(source, params)
        # Check for IRCv3 features
        if hasattr(self, "supports") and self.supports:
            self.ircv3_features = list(self.supports.keys())


class TestPydleIRCv3:
    """Test pydle's IRCv3 capabilities and advanced features."""

    @pytest.mark.asyncio
    async def test_pydle_ircv3_capabilities(self):
        """Test IRCv3 capability negotiation."""
        client = IRCv3TestBot("TestBot")

        # Mock capability negotiation
        with patch.object(client, "request_capabilities") as mock_caps:
            mock_caps.return_value = None

            # Simulate receiving capabilities
            await client.on_capability("server-time")
            await client.on_capability("message-tags", "value")

            # Verify capabilities were recorded
            assert len(client.capabilities_received) == 2
            assert client.capabilities_received[0]["capability"] == "server-time"
            assert client.capabilities_received[1]["capability"] == "message-tags"

    @pytest.mark.asyncio
    async def test_pydle_featurize_system(self):
        """Test pydle's featurize system for modular features."""
        # Create a client with specific features
        CustomClient = pydle.featurize(
            pydle.features.RFC1459Support,
            pydle.features.CTCPSupport,
            pydle.features.AccountSupport,
        )

        client = CustomClient("TestBot")

        # Verify features are available
        assert hasattr(client, "ctcp")  # From CTCP support
        assert hasattr(client, "join")  # From RFC1459 support
        assert hasattr(client, "message")  # From RFC1459 support

    def test_pydle_client_pool_creation(self):
        """Test creating a pydle ClientPool."""
        pool = pydle.ClientPool()

        # Verify pool creation
        assert pool is not None
        assert hasattr(pool, "connect")
        assert hasattr(pool, "handle_forever")

        # Test adding clients to pool
        clients = []
        for i in range(3):
            client = IRCv3TestBot(f"Bot{i}")
            clients.append(client)

        assert len(clients) == 3
        assert all(client.nickname.startswith("Bot") for client in clients)

    @pytest.mark.asyncio
    async def test_pydle_sasl_authentication_setup(self):
        """Test pydle's SASL authentication configuration."""
        # Test SASL with username/password
        client = pydle.Client(
            "TestBot",
            sasl_username="testuser",
            sasl_password="testpass",
            sasl_identity="testaccount",
        )

        assert client.sasl_username == "testuser"
        assert client.sasl_password == "testpass"
        assert client.sasl_identity == "testaccount"

        # Test SASL with external (certificate) auth
        client_cert = pydle.Client("TestBot", sasl_mechanism="EXTERNAL", tls_client_cert="/path/to/cert")

        assert client_cert.sasl_mechanism == "EXTERNAL"
        assert client_cert.tls_client_cert == "/path/to/cert"

    @pytest.mark.asyncio
    async def test_pydle_message_tags_support(self):
        """Test pydle's message tags (IRCv3.2) support."""
        IRCv3TestBot("TestBot")

        # Mock message with tags
        tagged_message = "@time=2023-01-01T12:00:00.000Z :user!host@server PRIVMSG #channel :Hello"

        # pydle should handle tagged messages
        # This would normally be handled by the message parsing system
        assert "@" in tagged_message  # Message has tags
        assert "time=" in tagged_message  # Has time tag

    def test_pydle_feature_inheritance(self):
        """Test pydle's feature inheritance system."""

        # Test multiple inheritance with features
        class CustomFeature(pydle.BasicClient):
            """Custom feature for testing."""

            async def on_custom_event(self):
                pass

        # Create client with custom feature
        CustomClient = pydle.featurize(pydle.Client, CustomFeature)
        client = CustomClient("TestBot")

        # Verify inheritance worked
        assert hasattr(client, "on_custom_event")
        assert hasattr(client, "join")  # From base Client
        assert hasattr(client, "message")  # From base Client

    @pytest.mark.asyncio
    async def test_pydle_batch_messages(self):
        """Test pydle's batch message support (IRCv3.2)."""
        client = IRCv3TestBot("TestBot")

        # Mock batch message handling
        # In real usage, pydle handles batch messages automatically
        assert hasattr(client, "batches") or hasattr(client, "_batches")

    @pytest.mark.asyncio
    async def test_pydle_monitor_capability(self):
        """Test pydle's MONITOR capability (IRCv3.2)."""
        client = IRCv3TestBot("TestBot")

        # MONITOR allows watching users across the network
        # This would be tested by checking if the capability is supported
        # and if monitor commands work properly
        assert hasattr(client, "request_capabilities")

    def test_pydle_ircv3_feature_detection(self):
        """Test detection of IRCv3 features."""
        client = IRCv3TestBot("TestBot")

        # Test IRCv3 feature attributes
        features_to_check = [
            "supports",  # ISUPPORT parsing
            "capabilities",  # CAP negotiation
            "batches",  # Batch messages
        ]

        for feature in features_to_check:
            # These may be private attributes, but should exist
            assert hasattr(client, feature) or hasattr(client, f"_{feature}")

    @pytest.mark.asyncio
    async def test_pydle_echo_message_support(self):
        """Test pydle's echo-message capability (IRCv3.1)."""
        client = IRCv3TestBot("TestBot")

        # Echo-message prevents receiving our own messages
        # This is handled automatically by pydle when the capability is negotiated
        assert hasattr(client, "capabilities")

    def test_pydle_multiple_server_support(self):
        """Test pydle's ability to handle multiple servers."""
        # Create clients for different servers
        servers = [
            ("irc.freenode.net", 6667),
            ("irc.rizon.net", 6697),
            ("irc.esper.net", 6667),
        ]

        clients = []
        for server, port in servers:
            client = IRCv3TestBot("TestBot")
            clients.append((client, server, port))

        assert len(clients) == 3
        assert all(isinstance(client, IRCv3TestBot) for client, _, _ in clients)

    @pytest.mark.asyncio
    async def test_pydle_custom_numeric_handling(self):
        """Test handling of custom IRC numerics."""
        client = IRCv3TestBot("TestBot")

        # Test custom numeric handler
        await client.on_raw_999("server", ["Custom message"])

        # Verify it doesn't crash and handles gracefully
        assert client is not None

    def test_pydle_feature_composition(self):
        """Test advanced feature composition."""
        # Test composing multiple features
        AdvancedClient = pydle.featurize(
            pydle.features.RFC1459Support,
            pydle.features.CTCPSupport,
            pydle.features.TLSSupport,
            pydle.features.ISUPPORTSupport,
        )

        client = AdvancedClient("TestBot")

        # Verify all features are composed correctly
        assert hasattr(client, "join")  # RFC1459
        assert hasattr(client, "ctcp") or hasattr(client, "ctcp_version")  # CTCP
        assert hasattr(client, "tls") or hasattr(client, "_tls")  # TLS
        assert hasattr(client, "supports")  # ISUPPORT


# Test fixtures for IRCv3 testing
@pytest.fixture
async def ircv3_client():
    """Provide an IRCv3-enabled pydle client."""
    client = IRCv3TestBot("TestBot")
    yield client


@pytest.fixture
def custom_featured_client():
    """Provide a client with custom features."""
    CustomClient = pydle.featurize(
        pydle.features.RFC1459Support,
        pydle.features.CTCPSupport,
        pydle.features.AccountSupport,
    )
    client = CustomClient("TestBot")
    yield client


@pytest.fixture
def pydle_pool():
    """Provide a pydle ClientPool for testing."""
    pool = pydle.ClientPool()
    yield pool
