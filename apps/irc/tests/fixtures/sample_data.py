"""Sample data and fixtures for testing."""

from typing import Any

# Sample IRC configuration data
SAMPLE_IRC_CONFIG = {
    "server": {
        "name": "test.irc.server",
        "description": "Test IRC Server",
        "network": "TestNet",
    },
    "listen": [{"port": 6697, "ssl": True}],
    "operators": [{"name": "testop", "password": "$2a$10$hashedpassword", "class": "netadmin"}],
}

# Sample Docker Compose configuration
SAMPLE_DOCKER_CONFIG = {
    "version": "3.8",
    "services": {
        "ircd": {
            "image": "unrealircd:latest",
            "ports": ["6697:6697"],
            "volumes": ["./data:/data"],
            "environment": ["IRC_NETWORK=testnet"],
        },
        "atheme": {
            "image": "atheme:latest",
            "ports": ["8080:8080"],
            "depends_on": ["ircd"],
        },
    },
}

# Sample log entries for testing
SAMPLE_IRC_LOGS = [
    "[2024-01-01 12:00:00] IRC Server starting",
    "[2024-01-01 12:00:01] Loading configuration",
    "[2024-01-01 12:00:02] Server ready on port 6697",
    "[2024-01-01 12:00:05] Client connecting: testuser",
    "[2024-01-01 12:00:06] JOIN #testchannel testuser",
]

# Sample network responses
SAMPLE_HTTP_RESPONSES = {
    "health_check": {"status": "healthy", "uptime": "1d 2h 30m"},
    "server_info": {
        "version": "UnrealIRCd-6.1.0",
        "clients": 42,
        "channels": 15,
        "servers": 1,
    },
}


def get_sample_config(config_type: str) -> dict[str, Any]:
    """Get sample configuration data by type."""
    configs = {
        "irc": SAMPLE_IRC_CONFIG,
        "docker": SAMPLE_DOCKER_CONFIG,
        "logs": SAMPLE_IRC_LOGS,
        "responses": SAMPLE_HTTP_RESPONSES,
    }
    return configs.get(config_type, {})
