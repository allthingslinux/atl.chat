---
labels:
- 'Statistics'
...

This module provides **public** access to Prosodys
[internal statistics][doc:statistics] trough the
[XEP-0039: Statistics Gathering] protocol. This is a simple protocol
that returns triplets of name, unit and value for each know statistic
collected by Prosody. The names used are the internal names assigned by
modules or statsmanager, names from the registry are **not** used.

# Configuration

Enabled as usual by adding to [`modules_enabled`][doc:modules_enabled]:

```lua
-- Enable Prosodys internal statistics gathering
statistics = "internal"

-- and enable the module
modules_enabled = {
    -- other modules
    "stats39";
}
```

# Usage


## Example

Statistics can be queried from the XML console of clients that have one:

```xml
C:
<iq type="get" to="example.com" id="dTMERjt5">
  <query xmlns="http://jabber.org/protocol/stats"/>
</iq>

S:
<iq type="result" to="example.com" id="dTMERjt5">
  <query xmlns="http://jabber.org/protocol/stats">
    <stat name="cpu.clock:amount" value="0.212131"/>
    <stat name="cpu.percent:amount" value="0"/>
    <stat name="memory.allocated:amount" value="8.30259e+06"/>
    <stat name="memory.allocated_mmap:amount" value="401408"/>
    <stat name="memory.lua:amount" value="6.21347e+06"/>
    <stat name="memory.returnable:amount" value="13872"/>
    <stat name="memory.rss:amount" value="2.03858e+07"/>
    <stat name="memory.total:amount" value="6.53885e+07"/>
    <stat name="memory.unused:amount" value="14864"/>
    <stat name="memory.used:amount" value="8.28773e+06"/>
    <stat name="/*/mod_c2s/connections:amount" value="0"/>
    <stat name="/*/mod_c2s/ipv6:amount" value="0"/>
    <stat name="/*/mod_s2s/connections:amount" value="0"/>
    <stat name="/*/mod_s2s/ipv6:amount" value="0"/>
    <stat name="stats.collection:duration" unit="seconds" value="0.000125647"/>
    <stat name="stats.processing:duration" unit="seconds" value="0"/>
  </query>
</iq>
```

# Compatibly

  Prosody version   Works
  ----------------- -------
  0.9.x             No
  0.10.x            Yes
  0.11.x            Yes
  Trunk[^1]         No

[^1]: Does not work with trunk since the [change to
    OpenMetrics](https://hg.prosody.im/trunk/rev/5f15ab7c6ae5)
