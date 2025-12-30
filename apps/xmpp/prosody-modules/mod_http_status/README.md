Prosody 0.12 added an API allowing modules to report their status. This
module allows reading these statuses via HTTP for use in monitoring.

```
$ curl http://prosody.localhost:5280/status
{
   "example.com" : {
      "c2s" : {
         "message" : "Loaded",
         "type" : "core"
      }
   }
}
```

# Configuration


By default only access via localhost is allowed. This can be adjusted with `http_status_allow_ips`. The following example shows the default:

```
http_status_allow_ips = { "::1"; "127.0.0.1" }
```

Access can also be granted to one IP range via CIDR notation:

```
http_status_allow_cidr = "172.17.2.0/24"
```

The default for `http_status_allow_cidr` is empty.
