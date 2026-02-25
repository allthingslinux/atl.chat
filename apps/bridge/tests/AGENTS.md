# Tests

> Scope: `tests/` directory. Inherits root [AGENTS.md](../AGENTS.md).

778-test pytest suite covering all bridge components.

## Quick Facts

- **Runner:** pytest with `asyncio-mode=auto` (no `@pytest.mark.asyncio` needed)
- **File pattern:** `test_*.py`
- **Infrastructure:** `harness.py`, `mocks.py`, `conftest.py`

## Infrastructure

| File | Purpose |
|------|---------|
| `harness.py` | `BridgeTestHarness` — wires real Bus + Relay + mock adapters; `simulate_discord_message`, `simulate_irc_message`, `simulate_xmpp_message` helpers |
| `mocks.py` | `MockAdapter`, `MockDiscordAdapter`, `MockIRCAdapter`, `MockXMPPAdapter` — capture received events for assertion |
| `conftest.py` | Shared pytest fixtures |

Use `BridgeTestHarness` for any test that needs a real Bus + Relay wired together. Use mock adapters directly for unit tests that only need event capture.

## Test Files

| File | What it covers |
|------|----------------|
| `test_bridge_flow.py` | End-to-end message flow through the full stack |
| `test_relay.py` | Core relay routing: Discord→IRC, IRC→Discord, XMPP paths |
| `test_relay_extended.py` | Content filtering, edit/delete/reaction/typing relay |
| `test_bus.py` | Bus dispatch, per-adapter exception isolation |
| `test_gateway.py` | Gateway integration (Bus + Relay + Router together) |
| `test_router.py` | `ChannelRouter` mapping lookups, `load_from_config`, edge cases |
| `test_events.py` | Event dataclasses, factory functions, `Dispatcher` |
| `test_config.py` | Config loading, dotenv overlay, all `Config` properties |
| `test_identity.py` | `PortalClient` HTTP calls, `IdentityResolver` TTL cache |
| `test_identity_extended.py` | Extended identity resolution scenarios |
| `test_discord_adapter.py` | Discord adapter: webhooks, raw events, reactions, typing, outbound queue |
| `test_irc_adapter.py` | `IRCAdapter`: connect, send, edit, delete, reactions, typing, puppet routing |
| `test_irc_adapter_extended.py` | Extended IRC adapter scenarios |
| `test_irc_client.py` | `IRCClient`: `on_connect`, `on_message`, IRCv3 caps, REDACT, TAGMSG |
| `test_irc_puppet.py` | `IRCPuppetManager`: create, idle timeout, keep-alive pinger, pre-join commands |
| `test_irc_msgid.py` | `MessageIDTracker`, `ReactionTracker`: store, bidirectional lookup, TTL expiry, reaction removal |
| `test_irc_message_split_utf8.py` | UTF-8 message splitting edge cases |
| `test_irc_threading.py` | IRC reply threading via `+draft/reply` |
| `test_irc_exceptions.py` | IRC error handling and reconnect backoff |
| `test_xmpp_adapter.py` | `XMPPAdapter`: inbound/outbound, reactions, typing, delete |
| `test_xmpp_component.py` | `XMPPComponent`: XEPs, corrections, retractions, avatar sync |
| `test_xmpp_component_outbound.py` | XMPP outbound message flow |
| `test_xmpp_features.py` | XMPP XEP features (0308, 0424, 0444, 0461, 0382) |
| `test_xmpp_msgid.py` | `XMPPMessageIDTracker`: store, bidirectional lookup, room JID, TTL expiry |
| `test_formatting.py` | `discord_to_irc`, `irc_to_discord`, `split_irc_message` |
| `test_message_formatting.py` | Extended formatting: edge cases, Unicode, control codes |
| `test_file_transfers.py` | XMPP HTTP Upload (XEP-0363) + IBB (XEP-0047) fallback |
| `test_presence_events.py` | Join/Part/Quit relay across protocols |
| `test_message_replies.py` | Reply threading Discord↔IRC↔XMPP |
| `test_message_ordering.py` | Concurrent message ordering |
| `test_message_verification.py` | Content integrity checks |
| `test_avatar_sync.py` | Avatar URL propagation and vCard-temp sync |
| `test_edge_cases.py` | Boundary conditions and unusual inputs |
| `test_error_handling.py` | Exception paths and recovery |
| `test_httpx_exceptions.py` | Portal API HTTP error handling (4xx, 5xx, timeouts) |
| `test_retry_logic.py` | Tenacity retry/backoff behaviour |
| `test_performance.py` | Throughput and latency benchmarks |
| `test_property_based.py` | Hypothesis property-based tests |
| `test_main.py` | Entry point, signal handling, config reload |

## Conventions

- All async tests work without `@pytest.mark.asyncio` — `asyncio-mode=auto` is set in `pyproject.toml`.
- Mock `asyncio.create_task` with `side_effect=lambda coro: coro.close() or MagicMock()` to avoid `RuntimeWarning: coroutine never awaited`.
- Use `BridgeTestHarness` for integration-style tests that need a real Bus + Relay wired together.
- Do not commit `.only` / `skip` markers.

## Commands

- `just test` — all tests
- `just test -k foo` — run tests matching `foo`
- `uv run pytest tests -v` — verbose output
- `uv run pytest tests --cov --cov-report=html` — with coverage

## Related

- [Bridge AGENTS.md](../AGENTS.md)
- [src/bridge/adapters/AGENTS.md](../src/bridge/adapters/AGENTS.md)
- [src/bridge/gateway/AGENTS.md](../src/bridge/gateway/AGENTS.md)
- [src/bridge/formatting/AGENTS.md](../src/bridge/formatting/AGENTS.md)
