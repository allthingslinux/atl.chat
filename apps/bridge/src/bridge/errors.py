"""Re-export from core.errors (AUDIT §2 Phase 6)."""

from bridge.core.errors import BridgeConfigurationError, BridgeError

__all__ = ["BridgeConfigurationError", "BridgeError"]
