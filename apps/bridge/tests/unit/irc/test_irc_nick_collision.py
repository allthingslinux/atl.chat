"""Tests for IRC puppet nick collision handling (Requirements 20.1, 20.2, 20.3).

Verifies that ERR_NICKNAMEINUSE (433) and ERR_ERRONEUSNICKNAME (432) are
handled with suffix escalation and re-sanitization.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from bridge.adapters.irc.handlers import (
    _sanitize_nick_for_retry,
    generate_collision_nick,
    handle_nick_collision,
)

# ---------------------------------------------------------------------------
# generate_collision_nick — unit tests
# ---------------------------------------------------------------------------


class TestGenerateCollisionNick:
    """Unit tests for nick collision suffix generation."""

    def test_first_attempt_adds_d_suffix(self) -> None:
        assert generate_collision_nick("alice", 0) == "alice[d]"

    def test_second_attempt_adds_1_suffix(self) -> None:
        assert generate_collision_nick("alice", 1) == "alice[1]"

    def test_third_attempt_adds_2_suffix(self) -> None:
        assert generate_collision_nick("alice", 2) == "alice[2]"

    def test_truncates_base_to_fit_max_len(self) -> None:
        long_nick = "a" * 25
        result = generate_collision_nick(long_nick, 0, max_len=23)
        assert len(result) <= 23
        assert result.endswith("[d]")

    def test_out_of_range_attempt_returns_truncated_base(self) -> None:
        result = generate_collision_nick("alice", 99, max_len=23)
        assert result == "alice"

    def test_negative_attempt_returns_truncated_base(self) -> None:
        result = generate_collision_nick("alice", -1, max_len=23)
        assert result == "alice"


# ---------------------------------------------------------------------------
# _sanitize_nick_for_retry — unit tests
# ---------------------------------------------------------------------------


class TestSanitizeNickForRetry:
    """Unit tests for nick re-sanitization on ERR_ERRONEUSNICKNAME."""

    def test_removes_forbidden_chars(self) -> None:
        assert _sanitize_nick_for_retry("al!ce@#") == "alce"

    def test_empty_result_becomes_user(self) -> None:
        assert _sanitize_nick_for_retry("!@#$") == "user"

    def test_clean_nick_unchanged(self) -> None:
        assert _sanitize_nick_for_retry("alice") == "alice"

    def test_removes_spaces(self) -> None:
        assert _sanitize_nick_for_retry("al ice") == "alice"


# ---------------------------------------------------------------------------
# handle_nick_collision — integration tests
# ---------------------------------------------------------------------------


class TestHandleNickCollision:
    """Integration tests for the nick collision handler."""

    @pytest.mark.asyncio
    async def test_433_tries_first_suffix(self) -> None:
        client = MagicMock()
        client.nickname = "alice"
        client._server_nicklen = 23
        client._nick_collision_attempts = 0
        client.set_nick = AsyncMock()

        message = MagicMock()
        message.params = ["*", "alice", "Nickname is already in use"]

        await handle_nick_collision(client, message, error_code=433)

        client.set_nick.assert_called_once_with("alice[d]")

    @pytest.mark.asyncio
    async def test_433_escalates_suffixes(self) -> None:
        client = MagicMock()
        client.nickname = "alice"
        client._server_nicklen = 23
        client._nick_collision_attempts = 1
        client.set_nick = AsyncMock()

        message = MagicMock()
        message.params = ["*", "alice[d]", "Nickname is already in use"]

        await handle_nick_collision(client, message, error_code=433)

        client.set_nick.assert_called_once_with("alice[1]")

    @pytest.mark.asyncio
    async def test_433_exhausted_retries_stops(self) -> None:
        client = MagicMock()
        client.nickname = "alice"
        client._server_nicklen = 23
        client._nick_collision_attempts = 5  # max retries
        client.set_nick = AsyncMock()

        message = MagicMock()
        message.params = ["*", "alice[4]", "Nickname is already in use"]

        await handle_nick_collision(client, message, error_code=433)

        client.set_nick.assert_not_called()

    @pytest.mark.asyncio
    async def test_432_resanitizes_nick(self) -> None:
        client = MagicMock()
        client.nickname = "al!ce"
        client._server_nicklen = 23
        client._nick_collision_attempts = 0
        client.set_nick = AsyncMock()

        message = MagicMock()
        message.params = ["*", "al!ce", "Erroneous nickname"]

        await handle_nick_collision(client, message, error_code=432)

        client.set_nick.assert_called_once_with("alce")

    @pytest.mark.asyncio
    async def test_432_already_clean_no_retry(self) -> None:
        client = MagicMock()
        client.nickname = "alice"
        client._server_nicklen = 23
        client._nick_collision_attempts = 0
        client.set_nick = AsyncMock()

        message = MagicMock()
        message.params = ["*", "alice", "Erroneous nickname"]

        await handle_nick_collision(client, message, error_code=432)

        # Same nick after sanitization — no retry
        client.set_nick.assert_not_called()
