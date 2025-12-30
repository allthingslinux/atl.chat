# Introduction

This module reports [module status priorities][doc:developers:moduleapi#logging-and-status] as metrics, which are a kind of persistent log messages
indicating whether the module is functioning properly.

This concept was introduced in [Prosody 0.12.0][doc:release:0.12.0#api] and is not used extensively yet, primarily for reporting failure to load
modules or e.g. [mod_component] not being connected to its external component yet.

Besides using this to report problems, this metric could also be used to count how many modules are loaded or monitor for when critical modules aren't
loaded at all.

# Configuration

After installing, enable by adding to [`modules_enabled`][doc:modules_enabled] like many other modules:

``` lua
-- in the global section
modules_enabled = {
    -- Other globally enabled modules here...
    "http_openmetrics";
    "measure_modules"; -- add
}
```

# Example OpenMetrics

``` openmetrics
# HELP prosody_module_status Prosody module status
# UNIT prosody_module_status
# TYPE prosody_module_status gauge
prosody_module_status{host="example.org",module="message"} 0
prosody_module_status{host="example.org",module="presence"} 0
prosody_module_status{host="groups.example.org",module="muc"} 0
```

# Details

The priorities are reported as the following values:

0
:   `core` - no problem, nothing to report

1
:   `info` - no problem, but a module had something important to say

2
:   `warn` - something is not right

3
:   `error` - something has gone wrong

Status changes are generally also reported in Prosodys logs, so look there for details.

# See also

- [mod_http_status] provides all module status details as JSON via HTTP
