"""Pytest fixtures and config."""

import sys
import warnings

# ---------------------------------------------------------------------------
# Suppress unawaited-coroutine RuntimeWarnings from AsyncMock GC.
#
# Python's _warn_unawaited_coroutine emits these when the garbage collector
# finalises AsyncMock coroutine objects that were never awaited.  This is a
# known CPython / unittest.mock interaction on 3.12+ and is harmless in tests.
# ---------------------------------------------------------------------------
_orig_warn = warnings.warn


def _filtered_warn(message, category=UserWarning, stacklevel=1, source=None, **kw):
    text = str(message)
    if category is RuntimeWarning and "was never awaited" in text:
        if "AsyncMockMixin" in text or "wrapper" in text:
            return
    _orig_warn(message, category=category, stacklevel=stacklevel + 1, source=source, **kw)


warnings.warn = _filtered_warn  # type: ignore[assignment]

# Suppress the PytestUnraisableExceptionWarning wrapper that pytest emits
# when it catches unawaited-coroutine warnings during GC finalization.
if "pytest" in sys.modules:
    import pytest

    warnings.filterwarnings(
        "ignore",
        message=r".*coroutine '.*' was never awaited.*",
        category=pytest.PytestUnraisableExceptionWarning,
    )
