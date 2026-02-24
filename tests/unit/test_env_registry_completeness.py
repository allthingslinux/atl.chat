"""Property test for env registry completeness.

**Validates: Requirements 11.1, 11.2, 11.3, 11.5**

Property 14: Env Registry Completeness
Parse `.env.example` and assert every variable in the required set is present
with a non-empty value or a `change_me_` placeholder.
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# The complete set of variables that must be present in .env.example
REQUIRED_VARS: set[str] = {
    # Requirement 1: Bridge XMPP Component JID Registration
    "BRIDGE_XMPP_COMPONENT_JID",
    "BRIDGE_XMPP_COMPONENT_SECRET",
    "BRIDGE_XMPP_COMPONENT_SERVER",
    "BRIDGE_XMPP_COMPONENT_PORT",
    # Requirement 3: IRC Environment Variable Standardization
    "IRC_SERVER",
    "IRC_PORT",
    # Requirement 4: Prosody Account Provisioning
    "PROSODY_REST_URL",
    "PROSODY_REST_USERNAME",
    "PROSODY_REST_PASSWORD",
    # Requirement 5: Atheme JSON-RPC URL
    "IRC_ATHEME_JSONRPC_URL",
    # Requirement 6: UnrealIRCd RPC Credentials
    "IRC_UNREAL_JSONRPC_URL",
    "IRC_UNREAL_RPC_USER",
    "IRC_UNREAL_RPC_PASSWORD",
    # Requirement 7: XMPP Domain Single Source of Truth
    "XMPP_DOMAIN",
    # Requirement 8: Bridge Portal Connection Variables
    "BRIDGE_PORTAL_BASE_URL",
    "BRIDGE_PORTAL_TOKEN",
    # Requirement 9: IRC Services Password (dead vars removed)
    "IRC_SERVICES_PASSWORD",
    # Requirement 11: Bridge nick
    "BRIDGE_IRC_NICK",
}

# Variables that must NOT be present (dead/removed)
FORBIDDEN_VARS: set[str] = {
    "ATHEME_SEND_PASSWORD",
    "ATHEME_RECEIVE_PASSWORD",
}


def parse_env_example(path: Path) -> dict[str, str]:
    """Parse a .env.example file into a dict of variable name -> value.

    Handles:
    - Comments (lines starting with #)
    - Blank lines
    - KEY=value pairs (value may be empty, quoted, or contain ${...} references)
    """
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


@pytest.fixture(scope="module")
def env_example_path(project_root: Path) -> Path:
    path = project_root / ".env.example"
    assert path.exists(), f".env.example not found at {path}"
    return path


@pytest.fixture(scope="module")
def env_vars(env_example_path: Path) -> dict[str, str]:
    return parse_env_example(env_example_path)


class TestEnvRegistryCompleteness:
    """Property 14: Env Registry Completeness."""

    def test_all_required_vars_present(self, env_vars: dict[str, str]) -> None:
        """Every variable in the required set must be present in .env.example."""
        missing = REQUIRED_VARS - env_vars.keys()
        assert not missing, f"Missing required variables in .env.example: {sorted(missing)}"

    def test_no_forbidden_vars_present(self, env_vars: dict[str, str]) -> None:
        """Dead variables must not appear in .env.example (Requirements 9.1, 9.2)."""
        present_forbidden = FORBIDDEN_VARS & env_vars.keys()
        assert not present_forbidden, f"Forbidden (dead) variables found in .env.example: {sorted(present_forbidden)}"

    def test_required_vars_have_non_empty_values(self, env_vars: dict[str, str]) -> None:
        """Every required variable must have a non-empty value or a change_me_ placeholder
        (Requirement 11.5)."""
        empty_vars = [var for var in REQUIRED_VARS if var in env_vars and not env_vars[var]]
        assert not empty_vars, f"Required variables have empty values in .env.example: {sorted(empty_vars)}"

    def test_xmpp_domain_is_atl_chat(self, env_vars: dict[str, str]) -> None:
        """XMPP_DOMAIN must be atl.chat (Requirement 7.1)."""
        assert env_vars.get("XMPP_DOMAIN") == "atl.chat", (
            f"XMPP_DOMAIN should be 'atl.chat', got '{env_vars.get('XMPP_DOMAIN')}'"
        )

    def test_prosody_domain_not_user_facing(self, env_vars: dict[str, str]) -> None:
        """PROSODY_DOMAIN must not be a user-facing variable (Requirement 7.2)."""
        assert "PROSODY_DOMAIN" not in env_vars, (
            "PROSODY_DOMAIN should not appear as a user-facing variable in .env.example"
        )

    def test_irc_server_matches_expected(self, env_vars: dict[str, str]) -> None:
        """IRC_SERVER must be irc.atl.chat (Requirement 3.1)."""
        assert env_vars.get("IRC_SERVER") == "irc.atl.chat"

    def test_irc_port_matches_expected(self, env_vars: dict[str, str]) -> None:
        """IRC_PORT must be 6697 (Requirement 3.2)."""
        assert env_vars.get("IRC_PORT") == "6697"

    def test_xmpp_component_jid_matches_expected(self, env_vars: dict[str, str]) -> None:
        """BRIDGE_XMPP_COMPONENT_JID must be bridge.atl.chat (Requirement 1.1)."""
        assert env_vars.get("BRIDGE_XMPP_COMPONENT_JID") == "bridge.atl.chat"

    def test_xmpp_component_port_matches_expected(self, env_vars: dict[str, str]) -> None:
        """BRIDGE_XMPP_COMPONENT_PORT must be 5347 (Requirement 1.4)."""
        assert env_vars.get("BRIDGE_XMPP_COMPONENT_PORT") == "5347"

    def test_portal_base_url_matches_expected(self, env_vars: dict[str, str]) -> None:
        """BRIDGE_PORTAL_BASE_URL must be https://portal.atl.tools (Requirement 8.1)."""
        assert env_vars.get("BRIDGE_PORTAL_BASE_URL") == "https://portal.atl.tools"

    def test_irc_atheme_jsonrpc_url_matches_expected(self, env_vars: dict[str, str]) -> None:
        """IRC_ATHEME_JSONRPC_URL must be http://atl-irc-server:8081/jsonrpc (Requirement 5.1)."""
        assert env_vars.get("IRC_ATHEME_JSONRPC_URL") == "http://atl-irc-server:8081/jsonrpc"

    def test_irc_unreal_jsonrpc_url_matches_expected(self, env_vars: dict[str, str]) -> None:
        """IRC_UNREAL_JSONRPC_URL must be https://irc.atl.chat:8600/api (Requirement 6.1)."""
        assert env_vars.get("IRC_UNREAL_JSONRPC_URL") == "https://irc.atl.chat:8600/api"

    def test_prosody_rest_url_matches_expected(self, env_vars: dict[str, str]) -> None:
        """PROSODY_REST_URL must be http://atl-xmpp-server:5280 (Requirement 4.5)."""
        assert env_vars.get("PROSODY_REST_URL") == "http://atl-xmpp-server:5280"

    def test_prosody_rest_username_matches_expected(self, env_vars: dict[str, str]) -> None:
        """PROSODY_REST_USERNAME must be admin@atl.chat (Requirement 4.6)."""
        assert env_vars.get("PROSODY_REST_USERNAME") == "admin@atl.chat"

    def test_secret_vars_have_change_me_placeholder(self, env_vars: dict[str, str]) -> None:
        """Secret variables must use change_me_ placeholders (Requirement 11.5)."""
        secret_vars = {
            "BRIDGE_XMPP_COMPONENT_SECRET",
            "PROSODY_REST_PASSWORD",
            "BRIDGE_PORTAL_TOKEN",
        }
        for var in secret_vars:
            value = env_vars.get(var, "")
            assert value.startswith("change_me_"), f"{var} should have a 'change_me_' placeholder, got '{value}'"


# ---------------------------------------------------------------------------
# Property-based test: for any subset of required vars, all must be present
# ---------------------------------------------------------------------------


@given(sampled_vars=st.lists(st.sampled_from(sorted(REQUIRED_VARS)), min_size=1, unique=True))
@settings(max_examples=50)
def test_property_required_vars_always_present(
    sampled_vars: list[str],
    project_root: Path,
) -> None:
    """Property 14: For any subset of required variables, all must be present in .env.example.

    **Validates: Requirements 11.1, 11.2, 11.3, 11.5**
    """
    env_example_path = project_root / ".env.example"
    env_vars = parse_env_example(env_example_path)

    missing = [v for v in sampled_vars if v not in env_vars]
    assert not missing, f"Required variables missing from .env.example: {missing}"

    empty = [v for v in sampled_vars if v in env_vars and not env_vars[v]]
    assert not empty, f"Required variables have empty values in .env.example: {empty}"
