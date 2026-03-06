"""Property-based tests for remote nick format template (CP24).

**Validates: Requirement 23.1**

Property CP24: Remote Nick Format Template
  For any nick and protocol values and for any remote_nick_format template
  containing ``{nick}``, the formatted output shall contain the original
  nick value.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st


def format_remote_nick(nick: str, protocol: str, template: str) -> str:
    """Pure-function mirror of the production format_remote_nick logic.

    See: adapters/irc/outbound.py ``format_remote_nick``.
    Accepts the template explicitly so we can test without config coupling.
    """
    effective = template or "<{nick}> "
    try:
        return effective.format(nick=nick, protocol=protocol)
    except (KeyError, ValueError):
        return f"<{nick}> "


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Arbitrary nick strings (non-empty to be meaningful)
_NICK = st.text(min_size=1, max_size=50)

# Protocol identifiers
_PROTOCOL = st.sampled_from(["discord", "irc", "xmpp"])

# Templates that contain {nick} — the property only holds for templates
# that actually include the nick placeholder.
_TEMPLATE_WITH_NICK = st.from_regex(r"[^{}]*\{nick\}[^{}]*", fullmatch=True).filter(lambda t: "{nick}" in t)


# ---------------------------------------------------------------------------
# CP24 Property 1: Default template output contains the nick
# ---------------------------------------------------------------------------


class TestDefaultTemplateContainsNick:
    """With the default template ``<{nick}> ``, output always contains nick.

    **Validates: Requirement 23.1**
    """

    @given(nick=_NICK, protocol=_PROTOCOL)
    @settings(max_examples=200)
    def test_default_template_contains_nick(
        self,
        nick: str,
        protocol: str,
    ) -> None:
        """Default template ``<{nick}> `` always embeds the nick value."""
        result = format_remote_nick(nick, protocol, template="<{nick}> ")
        assert nick in result, f"Expected nick {nick!r} in result {result!r}"


# ---------------------------------------------------------------------------
# CP24 Property 2: Any template containing {nick} produces output with nick
# ---------------------------------------------------------------------------


class TestCustomTemplateContainsNick:
    """For any template containing ``{nick}``, output contains the nick.

    **Validates: Requirement 23.1**
    """

    @given(nick=_NICK, protocol=_PROTOCOL, template=_TEMPLATE_WITH_NICK)
    @settings(max_examples=200)
    def test_custom_template_contains_nick(
        self,
        nick: str,
        protocol: str,
        template: str,
    ) -> None:
        """Any template with ``{nick}`` placeholder embeds the nick value.

        **Validates: Requirement 23.1**
        """
        result = format_remote_nick(nick, protocol, template=template)
        assert nick in result, f"Expected nick {nick!r} in result {result!r} (template={template!r})"


# ---------------------------------------------------------------------------
# CP24 Property 3: Fallback on invalid template still contains nick
# ---------------------------------------------------------------------------


class TestFallbackContainsNick:
    """When the template is invalid (triggers KeyError/ValueError), the
    fallback ``<{nick}> `` is used and still contains the nick.

    **Validates: Requirement 23.1**
    """

    @given(nick=_NICK, protocol=_PROTOCOL)
    @settings(max_examples=200)
    def test_invalid_template_fallback_contains_nick(
        self,
        nick: str,
        protocol: str,
    ) -> None:
        """Invalid template triggers fallback which still embeds the nick.

        **Validates: Requirement 23.1**
        """
        # Template with an unknown placeholder triggers KeyError
        bad_template = "<{nick}> {unknown_var}"
        result = format_remote_nick(nick, protocol, template=bad_template)
        assert nick in result, f"Expected nick {nick!r} in fallback result {result!r}"
        # Fallback should be exactly "<nick> "
        assert result == f"<{nick}> "

    @given(nick=_NICK, protocol=_PROTOCOL)
    @settings(max_examples=200)
    def test_empty_template_uses_default(
        self,
        nick: str,
        protocol: str,
    ) -> None:
        """Empty/None template falls back to default and contains nick.

        **Validates: Requirement 23.1**
        """
        result = format_remote_nick(nick, protocol, template="")
        assert nick in result, f"Expected nick {nick!r} in result {result!r}"
        assert result == f"<{nick}> "
