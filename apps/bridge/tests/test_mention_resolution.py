"""Tests for @nick mention resolution to Discord user IDs."""

from __future__ import annotations

from unittest.mock import MagicMock

from bridge.formatting.mention_resolution import resolve_mentions


def test_resolve_mentions_none_guild_returns_unchanged() -> None:
    """When guild is None, content is returned unchanged."""
    assert resolve_mentions("@alice hello", None) == "@alice hello"


def test_resolve_mentions_empty_content_returns_unchanged() -> None:
    """When content is empty, returns unchanged."""
    guild = MagicMock()
    guild.members = []
    assert resolve_mentions("", guild) == ""


def test_resolve_mentions_resolves_nick_to_user_id() -> None:
    """@nick is replaced with <@userId> when member matches by nick."""
    member = MagicMock()
    member.id = 12345
    member.nick = "alice"
    member.display_name = "Alice"
    member.name = "alice_user"

    guild = MagicMock()
    guild.members = [member]

    result = resolve_mentions("Hey @alice check this", guild)
    assert result == "Hey <@12345> check this"


def test_resolve_mentions_resolves_display_name() -> None:
    """@identifier matches display_name case-insensitively."""
    member = MagicMock()
    member.id = 99999
    member.nick = None
    member.display_name = "BobTheBuilder"
    member.name = "bob"

    guild = MagicMock()
    guild.members = [member]

    result = resolve_mentions("Hi @bobthebuilder", guild)
    assert result == "Hi <@99999>"


def test_resolve_mentions_resolves_username() -> None:
    """@identifier matches name (Discord username)."""
    member = MagicMock()
    member.id = 77777
    member.nick = None
    member.display_name = "Charlie"
    member.name = "charlie_discord"

    guild = MagicMock()
    guild.members = [member]

    result = resolve_mentions("Ping @charlie_discord", guild)
    assert result == "Ping <@77777>"


def test_resolve_mentions_skips_everyone() -> None:
    """@everyone is not resolved (stays literal)."""
    guild = MagicMock()
    guild.members = []

    result = resolve_mentions("@everyone hello", guild)
    assert result == "@everyone hello"


def test_resolve_mentions_skips_here() -> None:
    """@here is not resolved (stays literal)."""
    guild = MagicMock()
    guild.members = []

    result = resolve_mentions("@here check this", guild)
    assert result == "@here check this"


def test_resolve_mentions_unknown_nick_unchanged() -> None:
    """Unknown @nick stays as-is when no matching member."""
    guild = MagicMock()
    guild.members = []

    result = resolve_mentions("Hey @nobody", guild)
    assert result == "Hey @nobody"


def test_resolve_mentions_skips_inside_backticks() -> None:
    """@nick inside inline code is not resolved."""
    member = MagicMock()
    member.id = 11111
    member.nick = "dev"
    member.display_name = "Dev"
    member.name = "dev"

    guild = MagicMock()
    guild.members = [member]

    result = resolve_mentions("Use `@dev` in config", guild)
    assert result == "Use `@dev` in config"


def test_resolve_mentions_skips_inside_code_block() -> None:
    """@nick inside ``` code block is not resolved."""
    member = MagicMock()
    member.id = 22222
    member.nick = "admin"
    member.display_name = "Admin"
    member.name = "admin"

    guild = MagicMock()
    guild.members = [member]

    result = resolve_mentions("```\n@admin\n```", guild)
    assert result == "```\n@admin\n```"


def test_resolve_mentions_multiple_mentions() -> None:
    """Multiple @nicks are resolved."""
    alice = MagicMock()
    alice.id = 100
    alice.nick = "alice"
    alice.display_name = "Alice"
    alice.name = "alice"

    bob = MagicMock()
    bob.id = 200
    bob.nick = "bob"
    bob.display_name = "Bob"
    bob.name = "bob"

    guild = MagicMock()
    guild.members = [alice, bob]

    result = resolve_mentions("@alice and @bob", guild)
    assert result == "<@100> and <@200>"


def test_resolve_mentions_case_insensitive() -> None:
    """Matching is case-insensitive."""
    member = MagicMock()
    member.id = 33333
    member.nick = "CaseUser"
    member.display_name = "CaseUser"
    member.name = "caseuser"

    guild = MagicMock()
    guild.members = [member]

    assert resolve_mentions("@caseuser", guild) == "<@33333>"
    assert resolve_mentions("@CaseUser", guild) == "<@33333>"
    assert resolve_mentions("@CASEUSER", guild) == "<@33333>"
