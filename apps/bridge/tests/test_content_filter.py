"""Unit tests for pre-compiled content filter functions.

Tests _build_content_filters(), rebuild_content_filters(), and _content_matches_filter()
from bridge.gateway.relay.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

from __future__ import annotations

import re
from unittest.mock import patch

from bridge.gateway.relay import (
    _build_content_filters,
    _content_matches_filter,
    rebuild_content_filters,
)


class TestBuildContentFilters:
    """Tests for _build_content_filters() — Requirement 6.1, 6.3."""

    def test_valid_patterns_compile(self):
        """Valid regex strings produce compiled re.Pattern objects."""
        result = _build_content_filters([r"spam", r"\bblocked\b", r"^!command"])
        assert len(result) == 3
        assert all(isinstance(p, re.Pattern) for p in result)

    def test_compiled_patterns_match_correctly(self):
        """Compiled patterns match the same strings as raw re.search."""
        patterns = [r"spam", r"\bblocked\b", r"^!cmd"]
        compiled = _build_content_filters(patterns)

        # "spam" matches substring
        assert compiled[0].search("this is spam")
        assert not compiled[0].search("clean message")

        # word-boundary "blocked"
        assert compiled[1].search("you are blocked here")
        assert not compiled[1].search("unblockedpath")

        # anchored "!cmd"
        assert compiled[2].search("!cmd do something")
        assert not compiled[2].search("run !cmd")

    def test_empty_pattern_list_returns_empty(self):
        """An empty input list produces an empty compiled list."""
        result = _build_content_filters([])
        assert result == []

    def test_invalid_regex_skipped_others_still_compile(self):
        """Invalid regex patterns are skipped; valid ones still compile."""
        result = _build_content_filters([r"[invalid", r"good", r"(unclosed"])
        assert len(result) == 1
        assert result[0].search("good")

    def test_all_invalid_returns_empty(self):
        """If every pattern is invalid, the result is an empty list."""
        result = _build_content_filters([r"[bad", r"(also bad"])
        assert result == []

    def test_invalid_regex_logs_warning(self, capfd):
        """Invalid patterns produce a loguru warning (captured via stderr)."""
        with patch("bridge.gateway.relay.logger") as mock_logger:
            _build_content_filters([r"[invalid"])
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "[invalid" in str(call_args)


class TestRebuildContentFilters:
    """Tests for rebuild_content_filters() — Requirement 6.1."""

    def test_rebuild_populates_compiled_filters(self):
        """rebuild_content_filters reads cfg.content_filter_regex and compiles them."""
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"spam", r"ads"]
            rebuild_content_filters()

        # After rebuild, _content_matches_filter should use the new patterns
        import bridge.gateway.relay as relay_mod

        assert len(relay_mod._compiled_filters) == 2
        assert relay_mod._compiled_filters[0].search("spam")
        assert relay_mod._compiled_filters[1].search("ads")

    def test_rebuild_with_empty_config(self):
        """rebuild_content_filters with empty list clears compiled filters."""
        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = []
            rebuild_content_filters()

        import bridge.gateway.relay as relay_mod

        assert relay_mod._compiled_filters == []

    def test_rebuild_replaces_previous_filters(self):
        """Calling rebuild twice replaces the old compiled filters."""
        import bridge.gateway.relay as relay_mod

        with patch("bridge.gateway.relay.cfg") as mock_cfg:
            mock_cfg.content_filter_regex = [r"old_pattern"]
            rebuild_content_filters()
            assert len(relay_mod._compiled_filters) == 1

            mock_cfg.content_filter_regex = [r"new_a", r"new_b"]
            rebuild_content_filters()
            assert len(relay_mod._compiled_filters) == 2
            assert relay_mod._compiled_filters[0].search("new_a")


class TestContentMatchesFilter:
    """Tests for _content_matches_filter() with pre-compiled patterns — Requirement 6.2, 6.4."""

    def test_matches_first_pattern(self):
        compiled = _build_content_filters([r"spam", r"ads"])
        with patch("bridge.gateway.relay._compiled_filters", compiled):
            assert _content_matches_filter("this is spam") is True

    def test_matches_second_pattern(self):
        compiled = _build_content_filters([r"spam", r"ads"])
        with patch("bridge.gateway.relay._compiled_filters", compiled):
            assert _content_matches_filter("click these ads") is True

    def test_no_match_returns_false(self):
        compiled = _build_content_filters([r"spam", r"ads"])
        with patch("bridge.gateway.relay._compiled_filters", compiled):
            assert _content_matches_filter("hello world") is False

    def test_empty_filters_never_matches(self):
        with patch("bridge.gateway.relay._compiled_filters", []):
            assert _content_matches_filter("anything") is False

    def test_empty_content_no_match(self):
        compiled = _build_content_filters([r"spam"])
        with patch("bridge.gateway.relay._compiled_filters", compiled):
            assert _content_matches_filter("") is False

    def test_uses_precompiled_not_raw_search(self):
        """Verify _content_matches_filter iterates pre-compiled Pattern objects."""
        pat = re.compile(r"test_pattern")
        with patch("bridge.gateway.relay._compiled_filters", [pat]):
            assert _content_matches_filter("this has test_pattern inside") is True
            assert _content_matches_filter("no match here") is False


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

import bridge.gateway.relay as relay_mod
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategy: generate simple, always-valid regex patterns built from safe atoms.
# We avoid arbitrary strings to prevent re.error from invalid regex.
_SAFE_LITERALS = st.sampled_from(["spam", "ads", "hello", "world", "foo", "bar", "test", "block", "drop"])
_WORD_BOUNDARY = _SAFE_LITERALS.map(lambda w: rf"\b{w}\b")
_ANCHORED_START = _SAFE_LITERALS.map(lambda w: f"^{w}")
_CHAR_CLASS = st.sampled_from([r"[a-z]+", r"[0-9]+", r"[A-Za-z]+", r"\d+", r"\w+"])

_VALID_PATTERN = st.one_of(_SAFE_LITERALS, _WORD_BOUNDARY, _ANCHORED_START, _CHAR_CLASS)


class TestContentFilterEquivalenceProperty:
    """Property 3: Content filter equivalence.

    **Validates: Requirement 6.4**

    For any content string and any list of valid regex patterns,
    _content_matches_filter with pre-compiled patterns returns the same
    boolean as iterating with re.search(pat, s) for each raw pattern.
    """

    @given(
        patterns=st.lists(_VALID_PATTERN, min_size=0, max_size=10),
        content=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=300)
    def test_precompiled_matches_raw_search(self, patterns: list[str], content: str):
        """Pre-compiled _content_matches_filter equals manual re.search iteration.

        **Validates: Requirement 6.4**
        """
        # Reference implementation: iterate raw patterns with re.search
        expected = any(re.search(pat, content) for pat in patterns)

        # System under test: compile via _build_content_filters, then match
        compiled = _build_content_filters(patterns)
        saved = relay_mod._compiled_filters
        try:
            relay_mod._compiled_filters = compiled
            actual = _content_matches_filter(content)
        finally:
            relay_mod._compiled_filters = saved

        assert actual == expected
