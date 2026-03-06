"""Property-based tests for IRC casefold idempotence (CP15).

**Validates: Requirement 2.3**

Property CP15: IRC Casefold Idempotence
  irc_casefold(irc_casefold(s, mode), mode) == irc_casefold(s, mode) for all modes.
"""

from __future__ import annotations

from bridge.formatting.primitives import irc_casefold
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategy: arbitrary text strings covering the full Unicode range.
# We include the IRC-special characters ([], \, ~, {}, |, ^) via the
# default text() alphabet, so Hypothesis will naturally exercise the
# translate tables.
_strings = st.text(min_size=0, max_size=200)

# All three casemapping modes defined by the IRC CASEMAPPING spec.
_modes = st.sampled_from(["ascii", "rfc1459", "rfc1459-strict"])


class TestIrcCasefoldIdempotence:
    """**Validates: Requirement 2.3**"""

    @given(s=_strings, mode=_modes)
    @settings(max_examples=200)
    def test_casefold_is_idempotent(self, s: str, mode: str) -> None:
        """CP15: Applying irc_casefold twice yields the same result as once.

        **Validates: Requirement 2.3**
        """
        once = irc_casefold(s, mode)
        twice = irc_casefold(once, mode)
        assert twice == once, (
            f"irc_casefold is not idempotent for mode={mode!r}, s={s!r}: once={once!r}, twice={twice!r}"
        )
