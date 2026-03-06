"""Unit tests for gateway.pipeline — Pipeline, TransformContext, TransformStep."""

from __future__ import annotations

from bridge.gateway.pipeline import Pipeline, TransformContext


class TestTransformContext:
    """TransformContext fields are accessible and have correct defaults."""

    def test_required_fields(self) -> None:
        ctx = TransformContext(origin="discord", target="irc")
        assert ctx.origin == "discord"
        assert ctx.target == "irc"

    def test_default_values(self) -> None:
        ctx = TransformContext(origin="irc", target="xmpp")
        assert ctx.is_edit is False
        assert ctx.reply_to_id is None
        assert ctx.spoiler is False
        assert ctx.spoiler_reason is None
        assert ctx.raw == {}

    def test_optional_fields(self) -> None:
        ctx = TransformContext(
            origin="xmpp",
            target="discord",
            is_edit=True,
            reply_to_id="msg-123",
            spoiler=True,
            spoiler_reason="plot twist",
            raw={"stanza_id": "abc"},
        )
        assert ctx.is_edit is True
        assert ctx.reply_to_id == "msg-123"
        assert ctx.spoiler is True
        assert ctx.spoiler_reason == "plot twist"
        assert ctx.raw == {"stanza_id": "abc"}


class TestPipeline:
    """Pipeline executes steps in order and short-circuits on None."""

    def test_runs_steps_in_order(self) -> None:
        """Steps execute sequentially; each receives the previous output."""
        log: list[str] = []

        def step_a(content: str, ctx: TransformContext) -> str:
            log.append("a")
            return content + "[a]"

        def step_b(content: str, ctx: TransformContext) -> str:
            log.append("b")
            return content + "[b]"

        ctx = TransformContext(origin="discord", target="irc")
        result = Pipeline([step_a, step_b]).transform("hello", ctx)

        assert result == "hello[a][b]"
        assert log == ["a", "b"]

    def test_short_circuits_on_none(self) -> None:
        """When a step returns None, later steps are never called."""
        log: list[str] = []

        def step_pass(content: str, ctx: TransformContext) -> str:
            log.append("pass")
            return content

        def step_drop(content: str, ctx: TransformContext) -> None:
            log.append("drop")

        def step_never(content: str, ctx: TransformContext) -> str:
            log.append("never")
            return content

        ctx = TransformContext(origin="irc", target="xmpp")
        result = Pipeline([step_pass, step_drop, step_never]).transform("hi", ctx)

        assert result is None
        assert log == ["pass", "drop"]

    def test_empty_pipeline_returns_content(self) -> None:
        """A pipeline with no steps returns the original content."""
        ctx = TransformContext(origin="discord", target="xmpp")
        assert Pipeline([]).transform("unchanged", ctx) == "unchanged"

    def test_single_step(self) -> None:
        def upper(content: str, ctx: TransformContext) -> str:
            return content.upper()

        ctx = TransformContext(origin="xmpp", target="irc")
        assert Pipeline([upper]).transform("hello", ctx) == "HELLO"

    def test_step_can_read_context(self) -> None:
        """Steps can inspect and mutate the shared TransformContext."""

        def set_spoiler(content: str, ctx: TransformContext) -> str:
            ctx.spoiler = True
            return content

        def check_spoiler(content: str, ctx: TransformContext) -> str:
            if ctx.spoiler:
                return f"||{content}||"
            return content

        ctx = TransformContext(origin="discord", target="discord")
        result = Pipeline([set_spoiler, check_spoiler]).transform("secret", ctx)

        assert result == "||secret||"
        assert ctx.spoiler is True
