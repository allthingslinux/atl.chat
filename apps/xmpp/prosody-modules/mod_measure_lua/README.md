This module provides two [metrics][doc:statistics]:

`lua_heap_bytes`
:   Bytes of memory as reported by `collectgarbage("count")`{.lua}

`lua_info`
:   Provides the current Lua version as a label

``` openmetrics
# HELP lua_info Lua runtime version
# UNIT lua_info
# TYPE lua_info gauge
lua_info{version="Lua 5.4"} 1
# HELP lua_heap_bytes Memory used by objects under control of the Lua
garbage collector
# UNIT lua_heap_bytes bytes
# TYPE lua_heap_bytes gauge
lua_heap_bytes 8613218
```
