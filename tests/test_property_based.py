"""Property-based tests using hypothesis."""

import pytest
from hypothesis import given, strategies as st

from bridge.events import message_in, MessageIn


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
        from bridge.gateway.bus import Bus
        from bridge.events import message_in

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
        from bridge.gateway.bus import Bus
        from bridge.events import message_in

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
