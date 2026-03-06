"""Tests for IRC adapter isolation — no cross-adapter imports (Requirement 8.2).

Verifies that no module in adapters/irc/ imports from adapters.discord or
adapters.xmpp.
"""

from __future__ import annotations

import ast
import pathlib

_IRC_ADAPTER_DIR = pathlib.Path(__file__).resolve().parent.parent / "src" / "bridge" / "adapters" / "irc"

# Forbidden import prefixes
_FORBIDDEN_PREFIXES = (
    "bridge.adapters.discord",
    "bridge.adapters.xmpp",
)


def _collect_imports(filepath: pathlib.Path) -> list[tuple[str, int]]:
    """Parse a Python file and return all imported module names with line numbers."""
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))
    return imports


class TestIRCAdapterIsolation:
    """Verify no cross-adapter imports exist in the IRC adapter package."""

    def test_no_discord_or_xmpp_imports(self) -> None:
        violations: list[str] = []

        for py_file in sorted(_IRC_ADAPTER_DIR.glob("*.py")):
            if py_file.name == "__pycache__":
                continue
            for module_name, lineno in _collect_imports(py_file):
                for prefix in _FORBIDDEN_PREFIXES:
                    if module_name.startswith(prefix):
                        violations.append(f"{py_file.name}:{lineno} imports {module_name}")

        assert violations == [], "Cross-adapter imports found in IRC adapter:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
