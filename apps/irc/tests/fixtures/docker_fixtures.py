"""Docker fixtures and utilities for testing using pytest-docker-tools."""

import pytest
from pytest_docker_tools import container, fetch

# Base image fixtures
unrealircd_image = fetch(repository="ircatlchat-unrealircd:latest")
atheme_image = fetch(repository="ircatlchat-atheme:latest")


# Config directory fixture for container configurations
@pytest.fixture(scope="function")
def container_config_dir(tmp_path):
    """Create a temporary directory for container config files."""
    return tmp_path / "container_config"


# UnrealIRCd container fixture
unrealircd_container = container(
    image="{unrealircd_image.id}",
    ports={
        "6667/tcp": None,  # Main IRC port
        "6697/tcp": None,  # TLS port
    },
    environment={
        "UNREALIRCD_CONF": "/tmp/unrealircd.conf",
    },
    volumes={
        "{container_config_dir}": {"bind": "/tmp", "mode": "ro"},
    },
    command=[
        "-t",  # Test configuration
        "-F",  # Don't fork
        "-f",
        "/tmp/unrealircd.conf",
    ],
    scope="function",
)


# Atheme container fixture
atheme_container = container(
    image="{atheme_image.id}",
    ports={
        "8080/tcp": None,  # Services port
    },
    environment={
        "ATHEME_CONF": "/tmp/atheme.conf",
    },
    volumes={
        "{container_config_dir}": {"bind": "/tmp", "mode": "ro"},
    },
    command=[
        "-t",  # Test configuration
        "-F",  # Don't fork
        "-f",
        "/tmp/atheme.conf",
    ],
    scope="function",
)


class DockerControllerMixin:
    """Mixin class to add Docker container support to controllers."""

    def __init__(self, test_config, container_fixture=None):
        super().__init__(test_config)
        self.container = container_fixture

    def get_container_ports(self):
        """Get the mapped ports from the container."""
        if not self.container:
            raise RuntimeError("Container fixture not provided")

        ports = {}
        for port_spec, mapped_ports in self.container.ports.items():
            if mapped_ports:
                ports[port_spec] = mapped_ports[0]  # Take first mapped port
        return ports

    def wait_for_container_ready(self):
        """Wait for the container to be ready (override in subclasses)."""
        # Default implementation - just wait for port
        self.wait_for_port()
