"""Property test for bridge compose env var coverage.

**Validates: Requirement 2.5**

Property 2: Bridge Compose Passes All Required Env Vars
Parse `bridge.yaml` and assert all 8 required env vars appear in the
`atl-bridge` service environment block.
"""

from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

REQUIRED_BRIDGE_ENV_VARS: list[str] = [
    "BRIDGE_DISCORD_TOKEN",
    "BRIDGE_PORTAL_BASE_URL",
    "BRIDGE_PORTAL_TOKEN",
    "BRIDGE_XMPP_COMPONENT_JID",
    "BRIDGE_XMPP_COMPONENT_SECRET",
    "BRIDGE_XMPP_COMPONENT_SERVER",
    "BRIDGE_XMPP_COMPONENT_PORT",
    "BRIDGE_IRC_NICK",
]


def parse_bridge_yaml(path: Path) -> dict:
    """Parse bridge.yaml and return the parsed dict."""
    return yaml.safe_load(path.read_text())


def get_bridge_env_vars(bridge_data: dict) -> set[str]:
    """Extract env var names from the atl-bridge service environment block.

    Handles both list form (``- VAR_NAME``) and dict form (``VAR_NAME: value``).
    """
    service = bridge_data.get("services", {}).get("atl-bridge", {})
    env_block = service.get("environment", [])

    if isinstance(env_block, dict):
        return set(env_block.keys())

    # List form: entries may be "VAR_NAME" or "VAR_NAME=value"
    result = set()
    for entry in env_block:
        name = entry.split("=", 1)[0]
        result.add(name)
    return result


@pytest.fixture(scope="module")
def bridge_yaml_path(project_root: Path) -> Path:
    path = project_root / "infra" / "compose" / "bridge.yaml"
    assert path.exists(), f"bridge.yaml not found at {path}"
    return path


@pytest.fixture(scope="module")
def bridge_data(bridge_yaml_path: Path) -> dict:
    return parse_bridge_yaml(bridge_yaml_path)


@pytest.fixture(scope="module")
def bridge_env_vars(bridge_data: dict) -> set[str]:
    return get_bridge_env_vars(bridge_data)


class TestBridgeComposeEnvCoverage:
    """Property 2: Bridge Compose Passes All Required Env Vars."""

    def test_atl_bridge_service_exists(self, bridge_data: dict) -> None:
        """The atl-bridge service must be defined in bridge.yaml."""
        services = bridge_data.get("services", {})
        assert "atl-bridge" in services, "atl-bridge service not found in bridge.yaml"

    def test_all_required_env_vars_present(self, bridge_env_vars: set[str]) -> None:
        """All 8 required env vars must appear in the atl-bridge environment block."""
        missing = set(REQUIRED_BRIDGE_ENV_VARS) - bridge_env_vars
        assert not missing, (
            f"Missing required env vars in atl-bridge environment block: {sorted(missing)}"
        )

    def test_image_is_set(self, bridge_data: dict) -> None:
        """The atl-bridge service must specify the correct image."""
        service = bridge_data["services"]["atl-bridge"]
        assert service.get("image") == "ghcr.io/allthingslinux/bridge:latest"

    def test_depends_on_irc_and_xmpp(self, bridge_data: dict) -> None:
        """atl-bridge must depend on both atl-irc-server and atl-xmpp-server."""
        service = bridge_data["services"]["atl-bridge"]
        depends_on = service.get("depends_on", {})
        assert "atl-irc-server" in depends_on, "Missing depends_on: atl-irc-server"
        assert "atl-xmpp-server" in depends_on, "Missing depends_on: atl-xmpp-server"

    def test_depends_on_uses_service_healthy(self, bridge_data: dict) -> None:
        """depends_on conditions must be service_healthy."""
        service = bridge_data["services"]["atl-bridge"]
        depends_on = service.get("depends_on", {})
        for dep_name in ("atl-irc-server", "atl-xmpp-server"):
            condition = depends_on.get(dep_name, {}).get("condition")
            assert condition == "service_healthy", (
                f"{dep_name} condition should be 'service_healthy', got '{condition}'"
            )

    def test_config_volume_mounted(self, bridge_data: dict) -> None:
        """config.yaml must be mounted read-only into /app/config.yaml."""
        service = bridge_data["services"]["atl-bridge"]
        volumes = service.get("volumes", [])
        assert any("/app/config.yaml:ro" in v for v in volumes), (
            "config.yaml volume not mounted as read-only at /app/config.yaml"
        )

    def test_healthcheck_defined(self, bridge_data: dict) -> None:
        """A healthcheck must be defined for the atl-bridge service."""
        service = bridge_data["services"]["atl-bridge"]
        assert "healthcheck" in service, "No healthcheck defined for atl-bridge"

    def test_network_atl_chat(self, bridge_data: dict) -> None:
        """atl-bridge must be on the atl-chat network."""
        service = bridge_data["services"]["atl-bridge"]
        networks = service.get("networks", [])
        assert "atl-chat" in networks, "atl-bridge not connected to atl-chat network"


# ---------------------------------------------------------------------------
# Property-based test: for any subset of required vars, all must be present
# ---------------------------------------------------------------------------

@given(
    sampled_vars=st.lists(
        st.sampled_from(REQUIRED_BRIDGE_ENV_VARS), min_size=1, unique=True
    )
)
@settings(max_examples=50)
def test_property_bridge_env_vars_always_present(
    sampled_vars: list[str],
    project_root: Path,
) -> None:
    """Property 2: For any subset of required env vars, all must appear in bridge.yaml.

    **Validates: Requirement 2.5**
    """
    bridge_yaml_path = project_root / "infra" / "compose" / "bridge.yaml"
    bridge_data = parse_bridge_yaml(bridge_yaml_path)
    env_vars = get_bridge_env_vars(bridge_data)

    missing = [v for v in sampled_vars if v not in env_vars]
    assert not missing, (
        f"Required env vars missing from atl-bridge environment block: {missing}"
    )
