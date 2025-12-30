Over the years, some servers stop working for various reasons, and leave
behind broken roster subscriptions that trigger failing s2s connections.
This module allows cleaning up such cases by unsubscribing local users
from their contacts on those servers. Also works for typos and the like.
Use with care.

```lua
Component "gmail.com" "unsubscriber"
modules_disabled = { "s2s" }
```
