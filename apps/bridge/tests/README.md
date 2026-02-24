# Bridge Testing

Testing framework inspired by [dpytest](https://github.com/CraftSpider/dpytest) for testing the bridge without real protocol connections.

## How It Works

Like dpytest, we **mock at the adapter level** rather than connecting to real services:

1. **MockAdapter** - Fake adapters that capture events without Discord/IRC/XMPP connections
2. **BridgeTestHarness** - Sets up the event bus, router, relay, and mock adapters
3. **Simulation helpers** - Inject events as if they came from real protocols

## Architecture

```
Test Code
    ↓ simulate_discord_message()
MockDiscordAdapter → Bus → Relay → Bus → MockIRCAdapter
                                      ↓
                                  Captured in sent_messages[]
```

The real adapters (Discord, IRC, XMPP) are replaced with mocks that:
- Accept events through the same `accept_event`/`push_event` interface
- Capture outbound messages instead of sending them
- Never connect to real services

## Example Test

```python
@pytest.mark.asyncio
async def test_discord_to_irc_message(harness: BridgeTestHarness):
    await harness.start()

    # Simulate Discord message
    harness.simulate_discord_message(
        channel_id="123456789",
        author_id="user123",
        author_display="TestUser",
        content="Hello from Discord!",
    )

    # Verify IRC received it
    assert len(harness.irc.sent_messages) == 1
    msg = harness.irc.sent_messages[0]
    assert msg.content == "Hello from Discord!"

    await harness.stop()
```

## What Gets Tested

✅ **Tested:**
- Event routing logic (bus → relay → adapters)
- Message transformation (MessageIn → MessageOut)
- Channel mapping (Discord ↔ IRC ↔ XMPP)
- Event filtering (messages don't echo to origin)

❌ **Not Tested:**
- Real Discord/IRC/XMPP protocol behavior
- Network issues, rate limits, authentication
- Webhook creation, IRC puppet management

## Running Tests

```bash
uv run pytest tests/test_bridge_flow.py -v
```

## Adding Tests

1. Create test function with `harness` fixture
2. Use `harness.simulate_*_message()` to inject events
3. Check `harness.{discord,irc,xmpp}.sent_messages` for outputs
4. Use `harness.clear()` between test cases if needed

## Why This Approach?

- **Fast** - No real connections, runs in milliseconds
- **Reliable** - No flaky network issues
- **Isolated** - Tests bridge logic only
- **Safe** - Can't accidentally spam real channels

This is **not self-botting** - we never connect to Discord. It's standard unit testing with dependency injection.
