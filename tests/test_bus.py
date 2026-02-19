"""Test event bus and dispatcher."""


from bridge.events import Dispatcher, message_in
from bridge.gateway.bus import Bus


class MockTarget:
    """Mock event target for testing."""

    def __init__(self, accept_filter=None):
        self.received_events = []
        self.accept_filter = accept_filter or (lambda s, e: True)

    def accept_event(self, source: str, evt: object) -> bool:
        return self.accept_filter(source, evt)

    def push_event(self, source: str, evt: object) -> None:
        self.received_events.append((source, evt))


class TestDispatcher:
    """Test event dispatcher."""

    def test_register_target(self):
        # Arrange
        dispatcher = Dispatcher()
        target = MockTarget()

        # Act
        dispatcher.register(target)

        # Assert
        assert target in dispatcher._targets

    def test_unregister_target(self):
        # Arrange
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)

        # Act
        dispatcher.unregister(target)

        # Assert
        assert target not in dispatcher._targets

    def test_dispatch_to_accepting_target(self):
        # Arrange
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")

        # Act
        dispatcher.dispatch("discord", evt)

        # Assert
        assert len(target.received_events) == 1
        assert target.received_events[0] == ("discord", evt)

    def test_dispatch_not_to_rejecting_target(self):
        # Arrange
        dispatcher = Dispatcher()
        target = MockTarget(accept_filter=lambda s, e: False)
        dispatcher.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")

        # Act
        dispatcher.dispatch("discord", evt)

        # Assert
        assert len(target.received_events) == 0

    def test_dispatch_to_multiple_targets(self):
        # Arrange
        dispatcher = Dispatcher()
        target1 = MockTarget()
        target2 = MockTarget()
        dispatcher.register(target1)
        dispatcher.register(target2)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")

        # Act
        dispatcher.dispatch("discord", evt)

        # Assert
        assert len(target1.received_events) == 1
        assert len(target2.received_events) == 1

    def test_dispatch_handles_target_exception(self):
        # Arrange
        class FailingTarget:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                raise RuntimeError("Target failed")

        dispatcher = Dispatcher()
        failing = FailingTarget()
        working = MockTarget()
        dispatcher.register(failing)
        dispatcher.register(working)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")

        # Act
        dispatcher.dispatch("discord", evt)

        # Assert - working target still receives event
        assert len(working.received_events) == 1


class TestBus:
    """Test event bus."""

    def test_bus_wraps_dispatcher(self):
        # Arrange
        bus = Bus()
        target = MockTarget()

        # Act
        bus.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(target.received_events) == 1

    def test_bus_unregister(self):
        # Arrange
        bus = Bus()
        target = MockTarget()
        bus.register(target)

        # Act
        bus.unregister(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)

        # Assert
        assert len(target.received_events) == 0
