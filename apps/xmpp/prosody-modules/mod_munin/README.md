---
labels:
- 'Stage-Beta'
- 'Statistics'
summary: Implementation of the Munin node protocol
...

Summary
=======

This module implements the Munin reporting protocol, allowing you to
collect statistics directly from Prosody into Munin.

Configuration
=============

There is only one recommended option, `munin_node_name`, which specifies
the name that Prosody will identify itself by to the Munin server. You
may want to set this to the same hostname as in the [SRV record][doc:dns]
for the machine.

```lua
modules_enabled = {
    -- your other modules
    "munin",
}

munin_node_name = "xmpp.example.com"
```

You will also want to enable statistics collection by setting:

```lua
statistics_interval = 300 -- every 5 minutes, same as munin
```

## Summary

All these must be in [the global section][doc:configure#overview].

  Option                  Type     Default
  ----------------------- -------- ---------------------------
  munin\_node\_name       string   `"localhost"`
  munin\_ignored\_stats   set      `{ }`
  munin\_ports            set      `{ 4949 }`
  munin\_interfaces       set      `{ "0.0.0.0", "::" }`[^1]

[^1]: Varies depending on availability of IPv4 and IPv6

## Ports and interfaces


`mod_munin` listens on port `4949` on all local interfaces by default.
This can be changed with the standard [port and network configuration][doc:ports]:


``` lua
-- defaults:
munin_ports = { 4949 }
munin_interfaces = { "::", "0.0.0.0" }
```

If you already have a `munin-node` instance running, you can set a
different port to avoid the conflict.

## Configuring Munin

Simply add `munin_node_name` surrounded by brackets to `/etc/munin/munin.conf`:

``` ini
[xmpp.example.com]
address xmpp.example.com
port 4949
```

You can leave out `address` if it equal to the name in brackets, and
leave out the `port` if it is the default (`4949`).

Setting `address` to an IP address may sometimes be useful as the Munin
collection server is not delayed by DNS lookups in case of network
issues.

If you set a different port, or if the hostname to connect to is
different from this hostname, make sure to add `port` and/or `address`
options.

See [Munin documentation][muninconf] for more information.

Compatibility
=============

**Requires** Prosody 0.10 or above

[muninconf]: http://guide.munin-monitoring.org/en/stable-2.0/reference/munin.conf.html
