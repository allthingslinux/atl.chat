"""Tests for IRC AWAY for offline Discord users (Requirements 24.1, 24.2).

Verifies that set_puppet_away sends the correct AWAY commands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from bridge.adapters.irc.handlers import set_puppet_away


class TestSetPuppetAway:
    """Unit tests for the set_puppet_away utility."""

    @pytest.mark.asyncio
    async def test_set_away_when_offline(self) -> None:
        client = MagicMock()
        client.nickname = "alice_d"
        client.rawmsg = AsyncMock()

        await set_puppet_away(client, is_offline=True)

        client.rawmsg.assert_called_once_with("AWAY", "User is offline on Discord")

    @pytest.mark.asyncio
    async def test_clear_away_when_online(self) -> None:
        client = MagicMock()
        client.nickname = "alice_d"
        client.rawmsg = AsyncMock()

        await set_puppet_away(client, is_offline=False)

        client.rawmsg.assert_called_once_with("AWAY")

    @pytest.mark.asyncio
    async def test_away_error_does_not_raise(self) -> None:
        """AWAY command failure should be handled gracefully."""
        client = MagicMock()
        client.nickname = "alice_d"
        client.rawmsg = AsyncMock(side_effect=Exception("connection lost"))

        # Should not raise
        await set_puppet_away(client, is_offline=True)
