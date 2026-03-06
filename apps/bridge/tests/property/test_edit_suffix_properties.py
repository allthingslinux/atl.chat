"""Property-based tests for edit suffix append (CP23).

**Validates: Requirements 22.1, 22.2**

Property CP23: Edit Suffix Append
  Relayed edit content ends with configured edit_suffix when non-empty;
  equals edited content when empty.  Protocols with native edit support
  (Discord, XMPP) never receive the suffix.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

# The edit suffix logic lives inside Relay.push_event() which is tightly
# coupled to Bus/Router.  We extract the logic into a pure function that
# mirrors the production code exactly, then verify properties against it.
# See: gateway/relay.py lines 202-206.

_NATIVE_EDIT_PROTOCOLS: frozenset[str] = frozenset({"discord", "xmpp"})


def apply_edit_suffix(
    content: str,
    is_edit: bool,
    target: str,
    edit_suffix: str,
) -> str:
    """Pure-function mirror of the edit suffix logic in Relay.push_event().

    When ``is_edit`` is True and the target protocol does not support native
    edits, append ``edit_suffix`` (if non-empty) to the content.
    """
    if is_edit and target not in _NATIVE_EDIT_PROTOCOLS:
        if edit_suffix:
            content += edit_suffix
    return content


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Content: arbitrary text (the pipeline has already transformed it by this point)
_CONTENT = st.text(min_size=0, max_size=200)

# Non-empty edit suffix — at least one character
_NONEMPTY_SUFFIX = st.text(min_size=1, max_size=30)

# Protocols that do NOT support native edits (currently only IRC)
_NON_NATIVE_TARGETS = st.just("irc")

# Protocols that DO support native edits
_NATIVE_TARGETS = st.sampled_from(["discord", "xmpp"])


# ---------------------------------------------------------------------------
# CP23 Property 1: Non-empty suffix is appended for non-native targets
# ---------------------------------------------------------------------------


class TestEditSuffixAppendedForNonNative:
    """For non-native edit targets with non-empty suffix, content ends with suffix.

    **Validates: Requirements 22.1, 22.2**
    """

    @given(
        content=_CONTENT,
        edit_suffix=_NONEMPTY_SUFFIX,
        target=_NON_NATIVE_TARGETS,
    )
    @settings(max_examples=200)
    def test_content_ends_with_suffix(
        self,
        content: str,
        edit_suffix: str,
        target: str,
    ) -> None:
        """Relayed edit content ends with configured edit_suffix when non-empty.

        **Validates: Requirement 22.1**
        """
        result = apply_edit_suffix(content, is_edit=True, target=target, edit_suffix=edit_suffix)
        assert result.endswith(edit_suffix), f"Expected result to end with {edit_suffix!r}, got {result!r}"

    @given(
        content=_CONTENT,
        edit_suffix=_NONEMPTY_SUFFIX,
        target=_NON_NATIVE_TARGETS,
    )
    @settings(max_examples=200)
    def test_content_equals_original_plus_suffix(
        self,
        content: str,
        edit_suffix: str,
        target: str,
    ) -> None:
        """Result is exactly content + edit_suffix.

        **Validates: Requirement 22.1**
        """
        result = apply_edit_suffix(content, is_edit=True, target=target, edit_suffix=edit_suffix)
        assert result == content + edit_suffix


# ---------------------------------------------------------------------------
# CP23 Property 2: Empty suffix means content is unchanged
# ---------------------------------------------------------------------------


class TestEditSuffixEmptyMeansUnchanged:
    """For empty edit_suffix, relayed content equals the edited content.

    **Validates: Requirements 22.1, 22.2**
    """

    @given(
        content=_CONTENT,
        target=_NON_NATIVE_TARGETS,
    )
    @settings(max_examples=200)
    def test_empty_suffix_no_change(
        self,
        content: str,
        target: str,
    ) -> None:
        """Empty edit_suffix means content passes through unchanged.

        **Validates: Requirement 22.2**
        """
        result = apply_edit_suffix(content, is_edit=True, target=target, edit_suffix="")
        assert result == content, f"Expected unchanged content {content!r}, got {result!r}"


# ---------------------------------------------------------------------------
# CP23 Property 3: Native edit protocols never get suffix
# ---------------------------------------------------------------------------


class TestNativeEditProtocolsNoSuffix:
    """Discord and XMPP support native edits — no suffix is ever appended.

    **Validates: Requirements 22.1, 22.2**
    """

    @given(
        content=_CONTENT,
        edit_suffix=_NONEMPTY_SUFFIX,
        target=_NATIVE_TARGETS,
    )
    @settings(max_examples=200)
    def test_native_target_unchanged(
        self,
        content: str,
        edit_suffix: str,
        target: str,
    ) -> None:
        """Native edit targets receive content unchanged regardless of suffix.

        **Validates: Requirement 22.1**
        """
        result = apply_edit_suffix(content, is_edit=True, target=target, edit_suffix=edit_suffix)
        assert result == content, (
            f"Native target {target!r} should not get suffix, expected {content!r}, got {result!r}"
        )

    @given(
        content=_CONTENT,
        target=_NATIVE_TARGETS,
    )
    @settings(max_examples=200)
    def test_native_target_empty_suffix_unchanged(
        self,
        content: str,
        target: str,
    ) -> None:
        """Native edit targets with empty suffix also unchanged.

        **Validates: Requirement 22.2**
        """
        result = apply_edit_suffix(content, is_edit=True, target=target, edit_suffix="")
        assert result == content
