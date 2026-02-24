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
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        assert target in dispatcher._targets

    def test_unregister_target(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        dispatcher.unregister(target)
        assert target not in dispatcher._targets

    def test_unregister_nonexistent_target_is_safe(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.unregister(target)  # never registered — should not raise

    def test_dispatch_to_accepting_target(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(target.received_events) == 1
        assert target.received_events[0] == ("discord", evt)

    def test_dispatch_not_to_rejecting_target(self):
        dispatcher = Dispatcher()
        target = MockTarget(accept_filter=lambda s, e: False)
        dispatcher.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(target.received_events) == 0

    def test_dispatch_to_multiple_targets(self):
        dispatcher = Dispatcher()
        target1 = MockTarget()
        target2 = MockTarget()
        dispatcher.register(target1)
        dispatcher.register(target2)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(target1.received_events) == 1
        assert len(target2.received_events) == 1

    def test_dispatch_handles_push_event_exception(self):
        class FailingTarget:
            def accept_event(self, source, evt):
                return True

            def push_event(self, source, evt):
                raise RuntimeError("push failed")

        dispatcher = Dispatcher()
        working = MockTarget()
        dispatcher.register(FailingTarget())
        dispatcher.register(working)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(working.received_events) == 1

    def test_dispatch_handles_accept_event_exception(self):
        """accept_event raising should not prevent other targets from receiving."""

        class ExplodingTarget:
            def accept_event(self, source, evt):
                raise RuntimeError("accept failed")

            def push_event(self, source, evt):
                pass

        dispatcher = Dispatcher()
        working = MockTarget()
        dispatcher.register(ExplodingTarget())
        dispatcher.register(working)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(working.received_events) == 1

    def test_dispatch_passes_source_to_push_event(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        _, evt = message_in("irc", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("irc", evt)
        source, _ = target.received_events[0]
        assert source == "irc"

    def test_dispatch_with_no_targets_is_safe(self):
        dispatcher = Dispatcher()
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)  # no error

    def test_dispatch_multiple_events_received_in_order(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        events = []
        for i in range(5):
            _, evt = message_in("discord", "ch1", "u1", "User", f"msg {i}", f"id{i}")
            events.append(evt)
            dispatcher.dispatch("discord", evt)
        assert [e for _, e in target.received_events] == events

    def test_same_target_registered_twice_receives_event_twice(self):
        dispatcher = Dispatcher()
        target = MockTarget()
        dispatcher.register(target)
        dispatcher.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        dispatcher.dispatch("discord", evt)
        assert len(target.received_events) == 2


class TestBus:
    """Test event bus."""

    def test_bus_wraps_dispatcher(self):
        bus = Bus()
        target = MockTarget()
        bus.register(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)
        assert len(target.received_events) == 1

    def test_bus_unregister(self):
        bus = Bus()
        target = MockTarget()
        bus.register(target)
        bus.unregister(target)
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)
        assert len(target.received_events) == 0

    def test_bus_unregister_nonexistent_is_safe(self):
        bus = Bus()
        target = MockTarget()
        bus.unregister(target)  # never registered — should not raise

    def test_bus_adapters_property_reflects_registered_targets(self):
        bus = Bus()
        t1, t2 = MockTarget(), MockTarget()
        bus.register(t1)
        bus.register(t2)
        assert t1 in bus._adapters
        assert t2 in bus._adapters
        assert len(bus._adapters) == 2

    def test_bus_adapters_property_updates_after_unregister(self):
        bus = Bus()
        target = MockTarget()
        bus.register(target)
        bus.unregister(target)
        assert target not in bus._adapters

    def test_bus_publish_with_no_targets_is_safe(self):
        bus = Bus()
        _, evt = message_in("discord", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("discord", evt)  # no error

    def test_bus_publish_passes_source_correctly(self):
        bus = Bus()
        target = MockTarget()
        bus.register(target)
        _, evt = message_in("xmpp", "ch1", "u1", "User", "Hello", "msg1")
        bus.publish("xmpp", evt)
        source, _ = target.received_events[0]
        assert source == "xmpp"

    def test_bus_publish_multiple_events_all_received(self):
        bus = Bus()
        target = MockTarget()
        bus.register(target)
        for i in range(10):
            _, evt = message_in("discord", "ch1", "u1", "User", f"msg {i}", f"id{i}")
            bus.publish("discord", evt)
        assert len(target.received_events) == 10
