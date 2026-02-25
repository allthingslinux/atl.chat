"""Bridge domain exceptions (AUDIT §2.K, §2.F drc)."""

from __future__ import annotations


class BridgeError(Exception):
    """Base for bridge domain errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, object] | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.original_error = original_error


class BridgeConfigurationError(BridgeError):
    """Config validation or load failure."""
