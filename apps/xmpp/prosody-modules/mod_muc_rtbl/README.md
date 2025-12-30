---
summary: 
rockspec:
  dependencies:
  - mod_rtbl
labels:
- Stage-Alpha
...

This module subscribes to a real-time blocklist using pubsub (XEP-0060). As
entries are added and removed from the blocklist, it immediately updates a
local service-wide ban list.

# Configuring

Load this module on your existing MUC component like so:

```lua
Component "channels.example.com" "muc"
modules_enabled = {
	-- other modules etc
	"muc_rtbl";
}
```

Then you should configure one or more lists you want to subscribe to, supplying
full or partial URIs (the default node is 'muc_bans_sha256' if unspecified):

```lua
muc_rtbls = {
	"rtbl.example";
	-- Equivalent to above
	"xmpp:rtbl.example?;node=muc_bans_sha256";
}
```

If an unaffiliated JID matches an entry found in any of the configured RTBLs,
this module will block:

- Joins
- Group chat messages
- Private messages

from the JID that matched.

# Compatibility

Should work with Prosody >= 0.12.x

# Developers

## Protocol

This version of mod_muc_rtbl assumes that the pubsub node contains one item
per blocked JID. The item id should be the SHA256 hash of the JID to block.
The payload is not currently used, but it is recommend to use a XEP-0377
report element as the payload.
