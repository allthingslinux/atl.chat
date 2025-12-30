---
summary: Yet another MUC reliability module
rockspec:
  dependencies:
  - mod_track_muc_joins
labels:
- Stage-Alpha
...


This module reacts to [server-to-server][doc:s2s] connections closing by
performing [XEP-0410: MUC Self-Ping] from the server side after a short delay to check if
users are still connected to MUCs they have joined according
[mod_track_muc_joins].  If it can't be confirmed that the user is still
joined then their client devices are notified about this allowing them
to re-join.

# Installing

```
prosodyctl install mod_ping_muc
```

# Configuring

Enable as a regular module in
[`modules_enabled`][doc:modules_enabled] globally or under a
`VirtualHost`:

```lua
modules_enabled = {
	-- other modules etc
	"track_muc_joins",
	"ping_muc",
}
```

The delay after which pings are sent can be adjusted with the setting `ping_muc_delay`,
from the default `60` (seconds).

# Client facing protocol

If the module determines that the client has dropped out a MUC,
it sends it [a stanza to indicate this](https://xmpp.org/extensions/xep-0045.html#service-error-kick):

``` xml
<presence type="unavailable" id="random123" from="room@muc.host/nickname" to="user@example.net/resource">
  <x xmlns="http://jabber.org/protocol/muc#user">
    <item affiliation="none" role="none">
      <reason>Connection to remote server lost</reason>
    </item>
    <status code="110"/>
    <status code="330"/>
  </x>
</presence>
```

The `reason` message may vary.

Upon receiving this, the client may attempt to [rejoin](https://xmpp.org/extensions/xep-0045.html#enter).

# Compatibility

Requires Prosody 0.12.x or trunk
