"""Adapter isolation verification test (CP10).

**Validates: Requirements 8.1, 8.2, 8.3**

Property CP10: No Cross-Adapter Import
  For any module in adapters/discord/, adapters/irc/, or adapters/xmpp/,
  that module shall not import from any other adapter package.  Adapter
  isolation must be enforced — all cross-adapter communication through
  Bus only.

This is a static-analysis test using Python's ``ast`` module to parse
every ``.py`` file in each adapter package and assert that no import
statement references another adapter package.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Root of the adapter source tree.
_ADAPTERS_ROOT = Path(__file__).resolve().parents[2] / "src" / "bridge" / "adapters"

# The three adapter packages we enforce isolation on.
_ADAPTER_PACKAGES = ("discord", "irc", "xmpp")

# Fully-qualified module prefixes that each adapter must NOT import from.
_FORBIDDEN_PREFIXES: dict[str, list[str]] = {
    "discord": ["bridge.adapters.irc", "bridge.adapters.xmpp"],
    "irc": ["bridge.adapters.discord", "bridge.adapters.xmpp"],
    "xmpp": ["bridge.adapters.discord", "bridge.adapters.irc"],
}

# Also catch relative-style bare names like "adapters.irc" (without the
# leading "bridge." prefix) and short forms used in ``from ... import``.
_FORBIDDEN_RELATIVE_PREFIXES: dict[str, list[str]] = {
    "discord": ["adapters.irc", "adapters.xmpp"],
    "irc": ["adapters.discord", "adapters.xmpp"],
    "xmpp": ["adapters.discord", "adapters.irc"],
}


def _collect_py_files(adapter_dir: Path) -> list[Path]:
    """Return all ``.py`` files under *adapter_dir*, recursively."""
    return sorted(adapter_dir.rglob("*.py"))


def _extract_imports(source: str) -> list[str]:
    """Parse *source* and return all imported module names.

    Handles both ``import X`` and ``from X import Y`` forms.
    """
    tree = ast.parse(source)
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _check_adapter_isolation(
    adapter_name: str,
) -> list[tuple[str, str, str]]:
    """Return a list of violations ``(file, imported_module, forbidden_prefix)``."""
    adapter_dir = _ADAPTERS_ROOT / adapter_name
    if not adapter_dir.is_dir():
        return []

    forbidden = _FORBIDDEN_PREFIXES[adapter_name] + _FORBIDDEN_RELATIVE_PREFIXES[adapter_name]

    violations: list[tuple[str, str, str]] = []
    for py_file in _collect_py_files(adapter_dir):
        source = py_file.read_text(encoding="utf-8")
        for module in _extract_imports(source):
            for prefix in forbidden:
                if module == prefix or module.startswith(prefix + "."):
                    rel = py_file.relative_to(_ADAPTERS_ROOT)
                    violations.append((str(rel), module, prefix))
    return violations


class TestAdapterIsolation:
    """**Validates: Requirements 8.1, 8.2, 8.3**"""

    def test_discord_does_not_import_irc_or_xmpp(self) -> None:
        """CP10: Discord adapter has no imports from IRC or XMPP adapters.

        **Validates: Requirement 8.1**
        """
        violations = _check_adapter_isolation("discord")
        assert violations == [], "Discord adapter imports from other adapter packages:\n" + "\n".join(
            f"  {f}: imports {m} (forbidden prefix: {p})" for f, m, p in violations
        )

    def test_irc_does_not_import_discord_or_xmpp(self) -> None:
        """CP10: IRC adapter has no imports from Discord or XMPP adapters.

        **Validates: Requirement 8.2**
        """
        violations = _check_adapter_isolation("irc")
        assert violations == [], "IRC adapter imports from other adapter packages:\n" + "\n".join(
            f"  {f}: imports {m} (forbidden prefix: {p})" for f, m, p in violations
        )

    def test_xmpp_does_not_import_discord_or_irc(self) -> None:
        """CP10: XMPP adapter has no imports from Discord or IRC adapters.

        **Validates: Requirement 8.3**
        """
        violations = _check_adapter_isolation("xmpp")
        assert violations == [], "XMPP adapter imports from other adapter packages:\n" + "\n".join(
            f"  {f}: imports {m} (forbidden prefix: {p})" for f, m, p in violations
        )
