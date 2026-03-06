"""Property-based tests using hypothesis."""

from bridge.core.events import Dispatcher
from bridge.events import message_in
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPropertyBased:
    """Property-based tests for invariants."""

    @given(st.text(), st.text(), st.text(), st.text(), st.text(), st.text())
    def test_message_in_roundtrip(self, origin, channel_id, author_id, author_display, content, message_id):
        """Property: MessageIn preserves all input data."""
        # Arrange & Act
        _, evt = message_in(
            origin=origin,
            channel_id=channel_id,
            author_id=author_id,
            author_display=author_display,
            content=content,
            message_id=message_id,
        )

        # Assert
        assert evt.origin == origin
        assert evt.channel_id == channel_id
        assert evt.author_id == author_id
        assert evt.author_display == author_display
        assert evt.content == content
        assert evt.message_id == message_id

    @given(st.lists(st.text(min_size=1), min_size=1, max_size=100))
    def test_bus_dispatch_order(self, messages):
        """Property: Events are dispatched in order."""
        from bridge.events import message_in
        from bridge.gateway.bus import Bus

        # Arrange
        bus = Bus()
        received = []

        class OrderTracker:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                received.append(evt.content)

        tracker = OrderTracker()
        bus.register(tracker)

        # Act
        for msg in messages:
            _, evt = message_in("test", "ch1", "u1", "User", msg, f"msg-{msg}")
            bus.publish("test", evt)

        # Assert
        assert received == messages

    @given(st.integers(min_value=0, max_value=1000))
    def test_concurrent_message_handling(self, num_messages):
        """Property: All messages are processed regardless of count."""
        from bridge.events import message_in
        from bridge.gateway.bus import Bus

        # Arrange
        bus = Bus()
        counter = {"count": 0}

        class Counter:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                counter["count"] += 1

        bus.register(Counter())

        # Act
        for i in range(num_messages):
            _, evt = message_in("test", "ch1", "u1", "User", f"msg{i}", f"id{i}")
            bus.publish("test", evt)

        # Assert
        assert counter["count"] == num_messages


class TestDispatcherFaultIsolation:
    """Property 7: Dispatcher fault isolation.

    **Validates: Requirements 3.2**

    For any set of registered targets where one raises an exception,
    all other non-failing targets still receive the event.
    """

    @given(
        num_good_before=st.integers(min_value=0, max_value=10),
        num_good_after=st.integers(min_value=0, max_value=10),
        source=st.text(min_size=1, max_size=20),
        content=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=200)
    def test_fault_isolation(self, num_good_before, num_good_after, source, content):
        """For any set of registered targets where one raises an exception,
        all other non-failing targets still receive the event.

        **Validates: Requirements 3.2**
        """

        received: list[int] = []

        class GoodTarget:
            """A target that accepts all events and records its index."""

            def __init__(self, idx: int) -> None:
                self.idx = idx

            def accept_event(self, source: str, evt: object) -> bool:
                return True

            def push_event(self, source: str, evt: object) -> None:
                received.append(self.idx)

        class FailingTarget:
            """A target that accepts all events but raises on push."""

            def accept_event(self, source: str, evt: object) -> bool:
                return True

            def push_event(self, source: str, evt: object) -> None:
                raise RuntimeError("simulated failure")

        dispatcher = Dispatcher()

        # Register good targets before the failing one
        good_before = [GoodTarget(i) for i in range(num_good_before)]
        for t in good_before:
            dispatcher.register(t)

        # Register the failing target
        dispatcher.register(FailingTarget())

        # Register good targets after the failing one
        good_after = [GoodTarget(num_good_before + i) for i in range(num_good_after)]
        for t in good_after:
            dispatcher.register(t)

        # Dispatch an event
        _, evt = message_in("test", "ch1", "u1", "User", content, "msg1")
        dispatcher.dispatch(source, evt)

        # All non-failing targets should have received the event
        expected = [t.idx for t in good_before] + [t.idx for t in good_after]
        assert received == expected
