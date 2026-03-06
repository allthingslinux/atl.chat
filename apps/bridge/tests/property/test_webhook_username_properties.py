"""Property-based tests for webhook username validity (CP8).

**Validates: Requirement 14.1**

Property CP8: Webhook Username Validity
  For any input name, ``ensure_valid_username(name)`` shall produce a string
  with length between 2 and 32 characters inclusive.
"""

from __future__ import annotations

from bridge.identity.sanitize import ensure_valid_username
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies — exercise the full input space
# ---------------------------------------------------------------------------

# Arbitrary text: empty, whitespace-only, very long, unicode, control chars
_ARBITRARY_NAMES = st.text(min_size=0, max_size=500)


# ---------------------------------------------------------------------------
# CP8: ensure_valid_username always produces a string of length 2-32
# ---------------------------------------------------------------------------


class TestWebhookUsernameValidity:
    """ensure_valid_username(name) always produces string with length 2-32.

    **Validates: Requirement 14.1**
    """

    @given(name=_ARBITRARY_NAMES)
    @settings(max_examples=200)
    def test_result_is_string(self, name: str) -> None:
        """Result is always a string.

        **Validates: Requirement 14.1**
        """
        result = ensure_valid_username(name)
        assert isinstance(result, str)

    @given(name=_ARBITRARY_NAMES)
    @settings(max_examples=200)
    def test_length_within_bounds(self, name: str) -> None:
        """Result length is always between 2 and 32 inclusive.

        **Validates: Requirement 14.1**
        """
        result = ensure_valid_username(name)
        assert 2 <= len(result) <= 32, (
            f"Expected 2 <= len(result) <= 32, got len={len(result)} for input {name!r} -> {result!r}"
        )
