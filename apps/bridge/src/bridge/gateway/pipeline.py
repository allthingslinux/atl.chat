"""Content transformation pipeline (Design §D6).

Provides a composable pipeline of TransformStep functions that process
message content during relay.  The pipeline short-circuits on ``None``
(any step can drop a message by returning ``None``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from bridge.core.constants import ProtocolOrigin

# Re-export under the design-document name for convenience.
ProtocolName = ProtocolOrigin


class TransformStep(Protocol):
    """A single content-transformation callable."""

    def __call__(self, content: str, ctx: TransformContext) -> str | None: ...


@dataclass
class TransformContext:
    """Carries metadata through the pipeline for each message relay."""

    origin: ProtocolName
    target: ProtocolName
    is_edit: bool = False
    reply_to_id: str | None = None
    spoiler: bool = False
    spoiler_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """Ordered sequence of :class:`TransformStep` functions.

    Steps are executed in declaration order.  If any step returns ``None``
    the pipeline short-circuits immediately and ``transform`` returns ``None``.
    """

    def __init__(self, steps: list[TransformStep]) -> None:
        self._steps = list(steps)

    def transform(self, content: str, ctx: TransformContext) -> str | None:
        """Run all steps.  Returns ``None`` when any step signals *drop*."""
        result: str | None = content
        for step in self._steps:
            result = step(result, ctx)
            if result is None:
                return None
        return result
