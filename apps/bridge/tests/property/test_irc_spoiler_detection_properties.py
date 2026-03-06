"""Property-based tests for IRC fg==bg spoiler detection (CP22).

**Validates: Requirement 1.11**

Property CP22: IRC Foreground-Equals-Background Spoiler Detection
  For any IRC content containing a color code where the foreground color
  equals the background color, the IRC Parser shall flag the corresponding
  text as spoiler in the pipeline context.

IRC color code format:
  - ``\\x03`` starts a color code
  - ``\\x03FG`` sets foreground only (0-15)
  - ``\\x03FG,BG`` sets foreground and background (0-15 each)
  - When FG == BG, the text is "hidden" (same color as background)
"""

from __future__ import annotations

from bridge.formatting.irc_codes import COLOR, RESET, detect_irc_spoilers
from bridge.gateway.pipeline import TransformContext
from bridge.gateway.steps import unwrap_spoiler
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid IRC color numbers: 0-15
_irc_color = st.integers(min_value=0, max_value=15)

# Safe text body: letters/digits only, avoids control codes and formatting.
_safe_word = st.from_regex(r"[a-zA-Z0-9]{1,10}", fullmatch=True)
_safe_text = st.lists(_safe_word, min_size=1, max_size=5).map(" ".join)

# Distinct fg/bg pair (fg != bg)
_distinct_colors = st.tuples(_irc_color, _irc_color).filter(lambda t: t[0] != t[1])


def _fmt_color(fg: int, bg: int | None = None) -> str:
    """Format an IRC color code string ``\\x03FG[,BG]``."""
    if bg is not None:
        return f"{COLOR}{fg:02d},{bg:02d}"
    return f"{COLOR}{fg:02d}"


# ---------------------------------------------------------------------------
# CP22 Property: fg==bg detected as spoiler
# ---------------------------------------------------------------------------


class TestIrcSpoilerDetection:
    """CP22: IRC content with fg==bg color code is flagged as spoiler.

    **Validates: Requirement 1.11**
    """

    @given(color=_irc_color, text=_safe_text)
    @settings(max_examples=200)
    def test_fg_eq_bg_detected_by_detect_irc_spoilers(
        self,
        color: int,
        text: str,
    ) -> None:
        """detect_irc_spoilers returns non-empty ranges for fg==bg content.

        **Validates: Requirement 1.11**
        """
        content = f"{_fmt_color(color, color)}{text}{RESET}"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) > 0, f"detect_irc_spoilers missed fg==bg spoiler: color={color}, content={content!r}"
        # The detected range should cover the entire text body
        total_detected = sum(end - start for start, end in ranges)
        assert total_detected == len(text), (
            f"Spoiler range length mismatch: expected {len(text)}, got {total_detected} from ranges={ranges}"
        )

    @given(color=_irc_color, text=_safe_text)
    @settings(max_examples=200)
    def test_fg_eq_bg_sets_spoiler_flag_in_pipeline(
        self,
        color: int,
        text: str,
    ) -> None:
        """unwrap_spoiler sets ctx.spoiler=True for IRC fg==bg content.

        **Validates: Requirement 1.11**
        """
        content = f"{_fmt_color(color, color)}{text}{RESET}"
        ctx = TransformContext(origin="irc", target="discord")
        unwrap_spoiler(content, ctx)
        assert ctx.spoiler is True, (
            f"Pipeline spoiler flag not set for fg==bg IRC content: color={color}, content={content!r}"
        )

    @given(colors=_distinct_colors, text=_safe_text)
    @settings(max_examples=200)
    def test_fg_neq_bg_not_detected_as_spoiler(
        self,
        colors: tuple[int, int],
        text: str,
    ) -> None:
        """detect_irc_spoilers returns empty for fg!=bg content.

        **Validates: Requirement 1.11**
        """
        fg, bg = colors
        content = f"{_fmt_color(fg, bg)}{text}{RESET}"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) == 0, (
            f"detect_irc_spoilers false positive for fg!=bg: fg={fg}, bg={bg}, content={content!r}, ranges={ranges}"
        )

    @given(colors=_distinct_colors, text=_safe_text)
    @settings(max_examples=200)
    def test_fg_neq_bg_does_not_set_spoiler_flag(
        self,
        colors: tuple[int, int],
        text: str,
    ) -> None:
        """unwrap_spoiler does NOT set ctx.spoiler for fg!=bg IRC content.

        **Validates: Requirement 1.11**
        """
        fg, bg = colors
        content = f"{_fmt_color(fg, bg)}{text}{RESET}"
        ctx = TransformContext(origin="irc", target="discord")
        unwrap_spoiler(content, ctx)
        assert ctx.spoiler is False, (
            f"Pipeline spoiler flag incorrectly set for fg!=bg: fg={fg}, bg={bg}, content={content!r}"
        )

    @given(color=_irc_color, text=_safe_text)
    @settings(max_examples=200)
    def test_fg_only_not_detected_as_spoiler(
        self,
        color: int,
        text: str,
    ) -> None:
        """fg-only color codes (no bg) are NOT spoilers.

        **Validates: Requirement 1.11**
        """
        content = f"{_fmt_color(color)}{text}{RESET}"
        ranges = detect_irc_spoilers(content)
        assert len(ranges) == 0, (
            f"detect_irc_spoilers false positive for fg-only: color={color}, content={content!r}, ranges={ranges}"
        )
