This module allows advertising a machine-readable document were outages,
planned or otherwise, may be reported.

See [XEP-0455: Service Outage Status] for further details, including
the format of the outage status document.

```lua
modules_enabled = {
    -- other modules
    "service_outage_status",
}

outage_status_urls = {
    "https://uptime.example.net/status.json",
}
```

The outage status document should be hosted on a separate server to
ensure availability even if the XMPP server is unreachable.
