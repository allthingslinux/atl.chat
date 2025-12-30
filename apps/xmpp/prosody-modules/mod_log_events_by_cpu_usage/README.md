This module logs events where more than a certain amount of CPU time was
spent.

``` lua
log_cpu_threshold = 0.01 -- in seconds, so this is 10 milliseconds
```

Uses the Lua
[`os.clock()`](http://www.lua.org/manual/5.2/manual.html#pdf-os.clock)
function to estimate CPU usage.
