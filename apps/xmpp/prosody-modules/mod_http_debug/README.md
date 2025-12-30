---
summary: HTTP module returning info about requests for debugging
---

This module returns some info about HTTP requests as Prosody sees them
from an endpoint like `http://xmpp.example.net:5281/debug`.  This can be
used to validate [reverse-proxy configuration][doc:http] and similar use
cases.

# Example

```
$ curl -sSf  https://xmpp.example.net:5281/debug | json_pp
{
   "body" : "",
   "headers" : {
      "accept" : "*/*",
      "host" : "xmpp.example.net:5281",
      "user_agent" : "curl/7.74.0"
   },
   "httpversion" : "1.1",
   "id" : "jmFROQKoduU3",
   "ip" : "127.0.0.1",
   "method" : "GET",
   "path" : "/debug",
   "secure" : true,
   "url" : {
      "path" : "/debug"
   }
}
```

# Configuration

HTTP Methods handled can be configured via the `http_debug_methods`
setting. By default, the most common methods are already enabled.

```lua
http_debug_methods = { "GET"; "HEAD"; "DELETE"; "OPTIONS"; "PATCH"; "POST"; "PUT" };
```
