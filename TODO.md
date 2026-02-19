# TODO

## Future XEP Implementations

### XEP-0394: Message Markup
**Status:** Deferred - needs investigation

**What it does:**
- Semantic markup for bold, italic, code, quotes, lists
- Uses character position ranges instead of Markdown syntax
- Example: `<span start="6" end="11"><emphasis/></span>` for bold text

**Why deferred:**
- Complex bidirectional conversion between Discord Markdown and positional markup
- Requires parsing `**bold**`, `*italic*`, `` `code` ``, `> quote` and calculating offsets
- Breaks on edits (positions shift)
- Most XMPP clients already render Markdown
- High implementation complexity for marginal UX improvement

**Implementation notes if revisited:**
- Need robust Markdown parser for Discord → XMPP
- Need to reconstruct Markdown from position spans for XMPP → Discord
- Handle nested formatting, Unicode, emojis correctly
- Consider using existing Markdown library (e.g., `markdown-it-py`)
- Test with complex messages (mixed formatting, mentions, links)

**Dependencies:**
- `xep_0030` (Service Discovery)
- `xep_0071` (XHTML-IM) - deprecated, may need alternative approach
