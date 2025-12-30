---
summary: JSON Log Sink
---

Conifiguration
==============

Here we log to `/var/log/prosody/prosody.json`:

``` {.lua}
log = {
  -- your other log sinks
  info = "/var/log/prosody/prosody.log"
  -- add this:
  { to = "json", filename = "/var/log/prosody/prosody.json" };
}
```

## UDP

Alternatively, it can send logs via UDP:

```lua
log = {
  { to = "json", udp_host = "10.1.2.3", udp_port = "9999" };
}
```

Format
======

JSON log files consist of a series of `\n`-separated JSON objects,
suitable for mangling with tools like
[`jq`](https://stedolan.github.io/jq/).

Example (with whitespace and indentation for readability):

``` {.json}
{
   "args" : [],
   "datetime" : "2019-11-03T13:38:28Z",
   "level" : "info",
   "message" : "Client connected",
   "source" : "c2s55f267f5b9d0"
}
{
   "args" : [
      "user@example.net"
   ],
   "datetime" : "2019-11-03T13:38:28Z",
   "level" : "debug",
   "message" : "load_roster: asked for: %s",
   "source" : "rostermanager"
}
```

`datetime`
:   [XEP-0082]-formatted timestamp.

`source`
:   Log source, usually a module or a connected session.

`level`
:   `debug`, `info`, `warn` or `error`

`message`
:   The log message in `printf` format. Combine with `args` to get the
    final message.

`args`
:   Array of extra arguments, corresponding to `printf`-style `%s`
    formatting in the `message`.

Formatted message
-----------------

If desired, at the obvious expense of performance, the formatted version of
the string can be included in the JSON object by specifying the `formatted_as`
key in the logger config:

``` {.lua}
log = {
  -- ... other sinks ...
  { to = "json", formatted_as = "msg_formatted", filename = "/var/log/prosody/prosody.json" };
}

```

This will expose the formatted message in the JSON as separate `msg_formatted`
key. It is possible to override existing keys using this (for example, the
`message` key), but not advisible.
