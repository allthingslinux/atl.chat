"""Property-based tests for pipeline spoiler round-trip (CP11).

**Validates: Requirements 4.3, 4.4**

Property CP11: Pipeline Spoiler Round-Trip
  For any content with spoiler markers and for any origin and target protocol
  pair where both support spoilers, transforming the content through
  unwrap→format_convert→wrap shall preserve the spoiler flag and produce
  appropriate spoiler markers in the target output.

All three protocols support spoilers:
  - Discord: ``||text||``
  - IRC: fg==bg color codes (e.g. ``\\x0301,01text\\x0f``)
  - XMPP: XEP-0382 via ``ctx.raw``
"""

from __future__ import annotations

from bridge.formatting.irc_codes import COLOR, RESET
from bridge.gateway.pipeline import TransformContext
from bridge.gateway.steps import format_convert, unwrap_spoiler, wrap_spoiler
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROTOCOLS = ("discord", "irc", "xmpp")

# All 9 origin→target pairs (all protocols support spoilers).
_PROTOCOL_PAIRS = st.sampled_from([(o, t) for o in _PROTOCOLS for t in _PROTOCOLS if o != t])

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Safe word: letters only, avoids formatting markers and control codes.
_safe_word = st.from_regex(r"[a-zA-Z]{1,10}", fullmatch=True)

# Safe text: one or more words separated by spaces.
_safe_text = st.lists(_safe_word, min_size=1, max_size=5).map(" ".join)


def _wrap_spoiler_for_origin(text: str, origin: str) -> tuple[str, dict]:
    """Wrap *text* in spoiler markers appropriate for *origin*.

    Returns ``(content, raw_dict)`` where *raw_dict* carries XMPP stanza
    metadata when the origin is ``"xmpp"``.
    """
    if origin == "discord":
        return f"||{text}||", {}
    if origin == "irc":
        # fg==bg color 1 (black on black)
        return f"{COLOR}01,01{text}{RESET}", {}
    if origin == "xmpp":
        # XEP-0382: spoiler info lives in the stanza, not inline text.
        return text, {"spoiler": True}
    raise ValueError(origin)


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------


def _run_spoiler_pipeline(
    content: str,
    origin: str,
    target: str,
    raw: dict | None = None,
) -> tuple[str | None, TransformContext]:
    """Execute the unwrap→format_convert→wrap sub-pipeline and return the
    result together with the final :class:`TransformContext`.
    """
    ctx = TransformContext(origin=origin, target=target, raw=dict(raw or {}))
    result = unwrap_spoiler(content, ctx)
    result = format_convert(result, ctx)
    result = wrap_spoiler(result, ctx)
    return result, ctx


# ---------------------------------------------------------------------------
# CP11 Property: Spoiler flag preserved through pipeline
# ---------------------------------------------------------------------------


class TestSpoilerRoundTrip:
    """CP11: Spoiler flag is preserved through unwrap→format_convert→wrap
    for protocol pairs that both support spoilers.

    **Validates: Requirements 4.3, 4.4**
    """

    @given(text=_safe_text, pair=_PROTOCOL_PAIRS)
    @settings(max_examples=200)
    def test_spoiler_flag_preserved(self, text: str, pair: tuple[str, str]) -> None:
        """After the spoiler sub-pipeline, ``ctx.spoiler`` is True.

        **Validates: Requirements 4.3, 4.4**
        """
        origin, target = pair
        content, raw = _wrap_spoiler_for_origin(text, origin)
        _result, ctx = _run_spoiler_pipeline(content, origin, target, raw)
        assert ctx.spoiler is True, (
            f"Spoiler flag not set for {origin}→{target}: content={content!r}, result={_result!r}"
        )

    @given(text=_safe_text, pair=_PROTOCOL_PAIRS)
    @settings(max_examples=200)
    def test_discord_target_has_spoiler_markers(
        self,
        text: str,
        pair: tuple[str, str],
    ) -> None:
        """When the target is Discord, the output contains ``||`` markers.

        **Validates: Requirements 4.3, 4.4**
        """
        origin, target = pair
        if target != "discord":
            return  # only check Discord targets
        content, raw = _wrap_spoiler_for_origin(text, origin)
        result, _ctx = _run_spoiler_pipeline(content, origin, target, raw)
        assert result is not None
        assert result.startswith("||") and result.endswith("||"), (
            f"Discord target missing spoiler markers for {origin}→discord: result={result!r}"
        )

    @given(text=_safe_text, pair=_PROTOCOL_PAIRS)
    @settings(max_examples=200)
    def test_irc_target_has_spoiler_color_codes(
        self,
        text: str,
        pair: tuple[str, str],
    ) -> None:
        """When the target is IRC, the output contains fg==bg color codes.

        **Validates: Requirements 4.3, 4.4**
        """
        origin, target = pair
        if target != "irc":
            return
        content, raw = _wrap_spoiler_for_origin(text, origin)
        result, _ctx = _run_spoiler_pipeline(content, origin, target, raw)
        assert result is not None
        assert COLOR in result, f"IRC target missing color codes for {origin}→irc: result={result!r}"
        assert result.endswith(RESET), f"IRC target missing RESET for {origin}→irc: result={result!r}"

    @given(text=_safe_text, pair=_PROTOCOL_PAIRS)
    @settings(max_examples=200)
    def test_xmpp_target_sets_raw_spoiler(
        self,
        text: str,
        pair: tuple[str, str],
    ) -> None:
        """When the target is XMPP, ``ctx.raw["spoiler"]`` is True.

        **Validates: Requirements 4.3, 4.4**
        """
        origin, target = pair
        if target != "xmpp":
            return
        content, raw = _wrap_spoiler_for_origin(text, origin)
        _result, ctx = _run_spoiler_pipeline(content, origin, target, raw)
        assert ctx.raw.get("spoiler") is True, (
            f"XMPP target missing raw spoiler flag for {origin}→xmpp: raw={ctx.raw!r}"
        )
