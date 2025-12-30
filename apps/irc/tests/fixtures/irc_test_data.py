"""IRC-specific test data and fixtures."""

from typing import Any

# Sample IRC server configurations for testing
IRC_SERVER_CONFIGS = {
    "basic": {
        "host": "localhost",
        "port": 6697,
        "ssl_port": 6697,
        "network": "TestNet",
        "description": "Basic test IRC server",
    },
    "ssl_only": {
        "host": "localhost",
        "port": 6697,
        "ssl": True,
        "network": "SSLTestNet",
        "description": "SSL-only test IRC server",
    },
    "custom": {
        "host": "irc.example.com",
        "port": 7000,
        "ssl_port": 7001,
        "network": "CustomNet",
        "description": "Custom test configuration",
    },
}

# Sample IRC messages for testing
IRC_TEST_MESSAGES = {
    "welcome": ":irc.example.com 001 testuser :Welcome to the Test IRC Network",
    "join": ":testuser!user@host JOIN #testchannel",
    "part": ":testuser!user@host PART #testchannel :Goodbye",
    "privmsg": ":testuser!user@host PRIVMSG targetuser :Hello there!",
    "pubmsg": ":testuser!user@host PRIVMSG #testchannel :Hello everyone!",
    "quit": ":testuser!user@host QUIT :Client quit",
    "nick": ":testuser!user@host NICK newnick",
    "topic": ":testuser!user@host TOPIC #testchannel :New topic",
    "kick": ":oper!user@host KICK #testchannel baduser :Bad behavior",
    "mode": ":oper!user@host MODE #testchannel +o testuser",
    "ping": "PING :irc.example.com",
    "pong": "PONG :irc.example.com",
    "version": ":testuser!user@host VERSION",
    "time": ":testuser!user@host TIME",
    "info": ":testuser!user@host INFO",
}

# IRC command sequences for testing
IRC_COMMAND_SEQUENCES = {
    "basic_connection": [
        "NICK testuser",
        "USER testuser 0 * :Test User",
        "JOIN #testchannel",
        "PRIVMSG #testchannel :Hello world!",
        "PART #testchannel",
        "QUIT :Goodbye",
    ],
    "channel_operations": [
        "JOIN #testchannel",
        "TOPIC #testchannel :Test topic",
        "MODE #testchannel +n",  # No external messages
        "PRIVMSG #testchannel :Testing...",
        "PART #testchannel",
    ],
    "private_messaging": [
        "PRIVMSG otheruser :Hello!",
        "PRIVMSG otheruser :How are you?",
        "NOTICE otheruser :This is a notice",
    ],
}

# IRC server responses for testing
IRC_SERVER_RESPONSES = {
    "version": [
        ":irc.example.com 351 testuser UnrealIRCd-6.1.0. iowrsxOaAbceijklmntuv",
        ":irc.example.com 351 testuser iowrsxOaAbceijklmntuv :End of VERSION",
    ],
    "time": [":irc.example.com 391 testuser irc.example.com 1640995200 1640995200 :Wed Dec 31 2021 23:59:59 UTC"],
    "info": [
        ":irc.example.com 371 testuser :Test IRC Server",
        ":irc.example.com 371 testuser :Running UnrealIRCd",
        ":irc.example.com 374 testuser :End of INFO",
    ],
    "motd": [
        ":irc.example.com 375 testuser :- irc.example.com Message of the Day -",
        ":irc.example.com 372 testuser :- Welcome to Test IRC Server",
        ":irc.example.com 376 testuser :End of /MOTD command",
    ],
}

# Test user configurations
IRC_TEST_USERS = [
    {
        "nickname": "testuser1",
        "username": "test1",
        "realname": "Test User 1",
        "host": "localhost",
        "modes": ["i", "w"],  # invisible, wallops
    },
    {
        "nickname": "testuser2",
        "username": "test2",
        "realname": "Test User 2",
        "host": "localhost",
        "modes": ["r"],  # registered
    },
    {
        "nickname": "operuser",
        "username": "oper",
        "realname": "Test Operator",
        "host": "localhost",
        "modes": ["o", "O"],  # operator, local operator
    },
]

# Test channel configurations
IRC_TEST_CHANNELS = [
    {
        "name": "#testchannel",
        "topic": "Test Channel for IRC Testing",
        "modes": ["n", "t"],  # no external messages, topic protection
        "users": ["testuser1", "testuser2"],
    },
    {
        "name": "#private",
        "topic": "Private Test Channel",
        "modes": ["p", "s"],  # private, secret
        "users": ["testuser1"],
    },
    {
        "name": "&local",
        "topic": "Local Test Channel",
        "modes": ["n"],
        "users": ["operuser", "testuser1"],
    },
]

# IRC capability negotiation for testing
IRC_CAPABILITIES = [
    "multi-prefix",
    "extended-join",
    "account-notify",
    "away-notify",
    "chghost",
    "invite-notify",
    "sasl",
    "tls",
]


def get_irc_config(config_name: str) -> dict[str, Any]:
    """Get IRC server configuration by name."""
    return IRC_SERVER_CONFIGS.get(config_name, IRC_SERVER_CONFIGS["basic"])


def get_irc_message(message_type: str) -> str:
    """Get sample IRC message by type."""
    return IRC_TEST_MESSAGES.get(message_type, "")


def get_command_sequence(sequence_name: str) -> list[str]:
    """Get IRC command sequence by name."""
    return IRC_COMMAND_SEQUENCES.get(sequence_name, [])


def get_server_responses(response_type: str) -> list[str]:
    """Get IRC server responses by type."""
    return IRC_SERVER_RESPONSES.get(response_type, [])


def generate_irc_nickname(base: str = "testuser") -> str:
    """Generate a unique IRC nickname for testing."""
    import time

    return f"{base}_{int(time.time() * 1000) % 10000}"


def generate_irc_channel(base: str = "test") -> str:
    """Generate a unique IRC channel name for testing."""
    import time

    return f"#{base}_{int(time.time() * 1000) % 10000}"
