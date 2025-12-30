Simple module adding an endpoint meant to be used for health checks.

# Configuration

After installing, enable by adding to [`modules_enabled`][doc:modules_enabled] like many other modules:

``` lua
-- in the global section
modules_enabled = {
    -- Other globally enabled modules here...
    "http_health"; -- add
}
```

## Access control

By default only access via localhost is allowed. This can be adjusted with `http_health_allow_ips`. The following example shows the default:

```
http_health_allow_ips = { "::1"; "127.0.0.1" }
```

Access can also be granted to one IP range via CIDR notation:

```
http_health_allow_cidr = "172.17.2.0/24"
```

The default for `http_health_allow_cidr` is empty.

# Details

Adds a `http://your.prosody.example:5280/health` endpoint that returns either HTTP status code 200 when all appears to be good or 500 when any module
[status][doc:developers:moduleapi#logging-and-status] has been set to `error`.

# See also

- [mod_measure_modules] provides module statues via OpenMetrics
- [mod_http_status] provides all module status details as JSON via HTTP
