"""Tests for IRC history replay suppression (Requirement 18.2).

Verifies that messages with server-time timestamps significantly in the past
are discarded on join.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bridge.adapters.irc.handlers import is_history_replay


class TestIsHistoryReplay:
    """Unit tests for the is_history_replay utility."""

    def test_no_time_tag_not_replay(self) -> None:
        assert is_history_replay({}) is False

    def test_recent_timestamp_not_replay(self) -> None:
        now = datetime.now(timezone.utc)
        tags = {"time": now.isoformat()}
        assert is_history_replay(tags) is False

    def test_old_timestamp_is_replay(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=60)
        tags = {"time": old.isoformat()}
        assert is_history_replay(tags) is True

    def test_exactly_30s_not_replay(self) -> None:
        """Messages exactly at the threshold should not be discarded."""
        boundary = datetime.now(timezone.utc) - timedelta(seconds=29)
        tags = {"time": boundary.isoformat()}
        assert is_history_replay(tags) is False

    def test_31s_is_replay(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=31)
        tags = {"time": old.isoformat()}
        assert is_history_replay(tags) is True

    def test_z_suffix_timestamp(self) -> None:
        """IRC servers often use 'Z' suffix for UTC."""
        old = datetime.now(timezone.utc) - timedelta(minutes=5)
        time_str = old.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        tags = {"time": time_str}
        assert is_history_replay(tags) is True

    def test_invalid_timestamp_not_replay(self) -> None:
        tags = {"time": "not-a-timestamp"}
        assert is_history_replay(tags) is False

    def test_empty_time_tag_not_replay(self) -> None:
        tags = {"time": ""}
        assert is_history_replay(tags) is False
