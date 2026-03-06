# Tests

> Scope: `tests/` directory. Inherits root [AGENTS.md](../AGENTS.md).

1729-test pytest suite covering all bridge components.

## Quick Facts

- **Runner:** pytest with `asyncio-mode=auto` (no `@pytest.mark.asyncio` needed)
- **File pattern:** `test_*.py`
- **Infrastructure:** `harness.py`, `mocks.py`, `conftest.py`

## Infrastructure

| File | Purpose |
|------|---------|
| `harness.py` | `BridgeTestHarness` -- wires real Bus + Relay + mock adapters; `simulate_discord_message`, `simulate_irc_message`, `simulate_xmpp_message` helpers |
| `mocks.py` | `MockAdapter`, `MockDiscordAdapter`, `MockIRCAdapter`, `MockXMPPAdapter` -- capture received events for assertion |
| `conftest.py` | Shared pytest fixtures |

## Test Organization

```
tests/
├── unit/                # Isolated component tests
│   ├── discord/         # Discord adapter handlers, echo suppression, voice messages
│   ├── irc/             # IRC adapter, client, puppet, nick collision, CTCP, charset, away
│   ├── xmpp/            # XMPP echo suppression, MUC status codes, retraction fallback
│   ├── formatting/      # Converter, primitives, IRC codes, markdown, XMPP styling, splitter, XML strip
│   ├── gateway/         # Pipeline, pipeline steps
│   ├── identity/        # Sanitize (ensure_valid_username, sanitize_nick)
│   ├── tracking/        # BidirectionalTTLMap
│   ├── config/          # Config loading and validation
│   └── misc/            # Miscellaneous unit tests
├── property/            # Hypothesis property-based tests (24 correctness properties)
│   ├── test_ttl_map_properties.py          # CP1-CP5: BidirectionalTTLMap
│   ├── test_formatting_roundtrip.py        # CP2: Formatting roundtrip
│   ├── test_parse_emit_parse.py            # CP13: Parse-emit-parse roundtrip
│   ├── test_splitter_properties.py         # CP3: IRC message splitting
│   ├── test_irc_casefold_properties.py     # CP14: IRC casefold
│   ├── test_router_bijectivity_properties.py # CP6: Router bijectivity
│   ├── test_pipeline_shortcircuit_properties.py # CP7: Pipeline short-circuit
│   ├── test_spoiler_roundtrip_properties.py # CP11: Spoiler roundtrip
│   ├── test_content_filter_properties.py   # CP12: Content filter
│   ├── test_xml_strip_properties.py        # CP17: XML character stripping
│   ├── test_edit_suffix_properties.py      # CP23: Edit suffix
│   ├── test_webhook_username_properties.py # CP8: Webhook username validity
│   ├── test_nick_sanitization_properties.py # CP9: Nick sanitization
│   ├── test_config_roundtrip_properties.py # CP16: Config roundtrip
│   ├── test_discord_event_filter_properties.py # CP18: Discord event filtering
│   ├── test_xmpp_correction_chaining_properties.py # CP20: XEP-0308 correction chaining
│   ├── test_xmpp_reaction_model_properties.py # CP19: XMPP reaction model
│   ├── test_irc_spoiler_detection_properties.py # CP22: IRC spoiler detection
│   ├── test_adapter_isolation_properties.py # CP24: Adapter isolation
│   ├── test_url_preservation.py            # URL preservation across conversions
│   ├── test_same_protocol_identity.py      # Same-protocol identity
│   ├── test_remote_nick_format_properties.py # Remote nick formatting
│   └── test_property_based.py              # Legacy property tests
├── integration/         # Cross-component integration tests
│   └── test_echo_suppression_integration.py
└── offensive/           # Adversarial tests
    ├── test_injection.py        # Injection attack vectors
    ├── test_overflow.py         # Buffer overflow / large input
    ├── test_race_conditions.py  # Concurrency edge cases
    └── test_unicode_edge.py     # Unicode edge cases (ZWS, RTL, PUA, surrogates)
```

## Conventions

- All async tests work without `@pytest.mark.asyncio` -- `asyncio-mode=auto` is set in `pyproject.toml`.
- Mock `asyncio.create_task` with `side_effect=lambda coro: coro.close() or MagicMock()` to avoid `RuntimeWarning: coroutine never awaited`.
- Use `BridgeTestHarness` for integration-style tests that need a real Bus + Relay wired together.
- Do not commit `.only` / `skip` markers.

## Commands

- `just bridge test` -- all tests (from monorepo root)
- `just bridge test -k foo` -- run tests matching `foo`
- `uv run pytest tests -v` -- verbose output
- `uv run pytest tests --cov --cov-report=html` -- with coverage

## Related

- [Bridge AGENTS.md](../AGENTS.md)
- [src/bridge/adapters/AGENTS.md](../src/bridge/adapters/AGENTS.md)
- [src/bridge/gateway/AGENTS.md](../src/bridge/gateway/AGENTS.md)
- [src/bridge/formatting/AGENTS.md](../src/bridge/formatting/AGENTS.md)
- [src/bridge/tracking/AGENTS.md](../src/bridge/tracking/AGENTS.md)
- [src/bridge/identity/AGENTS.md](../src/bridge/identity/AGENTS.md)
- [src/bridge/config/AGENTS.md](../src/bridge/config/AGENTS.md)
