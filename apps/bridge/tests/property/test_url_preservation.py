"""Property-based tests for URL preservation (CP2).

**Validates: Requirement 1.1**

Property CP2: URL Preservation
  For any content containing URLs and for any origin and target protocol,
  every URL present in the original content shall also be present in the
  converted content.  URLs must never be modified by formatting conversion.
"""

from __future__ import annotations

from bridge.formatting.converter import ProtocolName, convert
from bridge.formatting.primitives import URL_RE
from hypothesis import given, settings
from hypothesis import strategies as st

# All protocol names.
_protocols = st.sampled_from(["discord", "irc", "xmpp"])

# Strategy for URL-safe path segments (alphanumeric + common path chars).
_path_segment = st.from_regex(r"[a-zA-Z0-9_\-]{1,20}", fullmatch=True)

# Strategy for generating a realistic URL.
_url = st.builds(
    lambda segments: "https://example.com/" + "/".join(segments),
    st.lists(_path_segment, min_size=1, max_size=3),
)

# Plain surrounding text — avoid formatting markers that could interfere.
_FORMATTING_MARKERS = frozenset("*_~`|\x02\x03\x0f\x11\x16\x1d\x1e\x1f")

_plain_word = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="".join(_FORMATTING_MARKERS) + "<>[](){}",
    ),
    min_size=0,
    max_size=30,
).filter(lambda t: "\n" not in t and "\r" not in t)


@st.composite
def _content_with_url(draw: st.DrawFn) -> tuple[str, str]:
    """Generate content that embeds a URL between plain text fragments.

    Returns (full_content, embedded_url).
    """
    url = draw(_url)
    prefix = draw(_plain_word)
    suffix = draw(_plain_word)
    # Ensure spaces separate the URL from surrounding text so parsers
    # don't accidentally merge them with adjacent characters.
    content = f"{prefix} {url} {suffix}".strip()
    return content, url


class TestURLPreservation:
    """CP2: URLs survive conversion across all protocol pairs.

    **Validates: Requirement 1.1**
    """

    @given(data=_content_with_url(), origin=_protocols, target=_protocols)
    @settings(max_examples=200)
    def test_url_present_after_conversion(
        self,
        data: tuple[str, str],
        origin: ProtocolName,
        target: ProtocolName,
    ) -> None:
        """Every URL in the original content is present in the converted content.

        **Validates: Requirement 1.1**
        """
        content, url = data
        converted = convert(content, origin, target)

        # The original URL must appear verbatim in the converted output.
        assert url in converted, (
            f"URL lost during {origin}→{target} conversion: url={url!r}, content={content!r}, converted={converted!r}"
        )

    @given(data=_content_with_url(), origin=_protocols, target=_protocols)
    @settings(max_examples=200)
    def test_all_urls_extracted_are_preserved(
        self,
        data: tuple[str, str],
        origin: ProtocolName,
        target: ProtocolName,
    ) -> None:
        """All URLs found by URL_RE in the original are also found in the converted output.

        **Validates: Requirement 1.1**
        """
        content, _ = data
        original_urls = set(URL_RE.findall(content))
        converted = convert(content, origin, target)
        converted_urls = set(URL_RE.findall(converted))

        missing = original_urls - converted_urls
        assert not missing, (
            f"URLs lost during {origin}→{target} conversion: "
            f"missing={missing!r}, content={content!r}, converted={converted!r}"
        )
