"""IRC message parsing utilities.

Adapted from irctest's message parser for IRC protocol testing.
"""


class Message:
    """Represents an IRC message."""

    def __init__(self, command: str, params: list[str], prefix: str | None = None, tags: dict[str, str] | None = None):
        self.command = command
        self.params = params
        self.prefix = prefix
        self.tags = tags or {}

    @classmethod
    def parse(cls, line: str) -> "Message":
        """Parse an IRC message from a raw line."""
        if not line.strip():
            raise ValueError("Empty message")

        original_line = line
        tags: dict[str, str] = {}

        # Handle message tags (IRCv3)
        if line.startswith("@"):
            tags_end = line.find(" ")
            if tags_end == -1:
                raise ValueError(f"Invalid message tags: {original_line}")

            tags_str = line[1:tags_end]
            line = line[tags_end + 1 :]

            # Parse individual tags
            for tag in tags_str.split(";"):
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    # Unescape tag value
                    value = value.replace("\\:", ";").replace("\\s", " ").replace("\\\\", "\\")
                    tags[key] = value
                else:
                    tags[tag] = ""

        # Handle prefix
        prefix = None
        if line.startswith(":"):
            prefix_end = line.find(" ")
            if prefix_end == -1:
                raise ValueError(f"Invalid message prefix: {original_line}")

            prefix = line[1:prefix_end]
            line = line[prefix_end + 1 :]

        # Parse command and parameters
        parts = line.split()
        if not parts:
            raise ValueError(f"No command found: {original_line}")

        command = parts[0].upper()

        # Parse parameters
        params = []
        i = 1
        while i < len(parts):
            param = parts[i]
            if param.startswith(":"):
                # Last parameter (trailing parameter)
                trailing = " ".join(parts[i:])
                params.append(trailing[1:])  # Remove the leading :
                break
            else:
                params.append(param)
            i += 1

        return cls(command=command, params=params, prefix=prefix, tags=tags)

    def __str__(self) -> str:
        """Convert message back to IRC protocol format."""
        parts = []

        # Add tags
        if self.tags:
            tag_parts = []
            for key, value in self.tags.items():
                # Escape tag value
                escaped_value = value.replace("\\", "\\\\").replace(";", "\\:").replace(" ", "\\s")
                if escaped_value:
                    tag_parts.append(f"{key}={escaped_value}")
                else:
                    tag_parts.append(key)
            parts.append("@" + ";".join(tag_parts))

        # Add prefix
        if self.prefix:
            parts.append(f":{self.prefix}")

        # Add command
        parts.append(self.command)

        # Add parameters
        if self.params:
            for i, param in enumerate(self.params):
                if i == len(self.params) - 1 and (" " in param or param.startswith(":")):
                    # Last parameter with spaces or starting with :
                    parts.append(f":{param}")
                else:
                    parts.append(param)

        return " ".join(parts)

    def __repr__(self) -> str:
        return f"Message(command={self.command!r}, params={self.params!r}, prefix={self.prefix!r}, tags={self.tags!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return False
        return (
            self.command == other.command
            and self.params == other.params
            and self.prefix == other.prefix
            and self.tags == other.tags
        )
