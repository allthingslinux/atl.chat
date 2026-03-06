"""Message formatting and splitting for cross-protocol bridging."""

from bridge.formatting.converter import convert, strip_formatting
from bridge.formatting.splitter import extract_code_blocks, split_irc_lines, split_irc_message

__all__ = ["convert", "extract_code_blocks", "split_irc_lines", "split_irc_message", "strip_formatting"]
