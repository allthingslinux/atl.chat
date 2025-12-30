---
labels:
- Stage-Obsolete
- Statistics
summary: Implementation of the Prometheus protocol
...

Description
===========

This module implements the Prometheus reporting protocol, allowing you
to collect statistics directly from Prosody into Prometheus.

See the [Prometheus documentation][prometheusconf] on the format for
more information.

[prometheusconf]: https://prometheus.io/docs/instrumenting/exposition_formats/

::: {.alert .alert-info}
**Note:** For use with Prosody 0.12 or later we recommend the bundled
[mod_http_openmetrics](https://prosody.im/doc/modules/mod_http_openmetrics)
instead. This module (mod_prometheus) will continue to be available in the
community repository for use with older Prosody versions.
:::

Configuration
=============

mod\_prometheus itself doesn’t have any configuration option, but it
requires Prosody’s [internal statistics
provider](https://prosody.im/doc/statistics#built-in_providers) to be
enabled.  You may also want to change the default collection interval
to the one your statistics consumer is using. See below for more information.

```lua
statistics = "internal"
statistics_interval = 15 -- in seconds
```

::: {.alert .alert-warning}
**NOTE:** Make sure to put the statistics variables in the global section of
the configuration, **not** in a `VirtualHost` or `Component` section.  You can
use `prosodyctl check` if you are unsure and want to check your configuration.
:::

See also the documentation of Prosody’s [HTTP
server](https://prosody.im/doc/http), since Prometheus is an HTTP
protocol that is how you can customise its URL.  The default one being
http://localhost:5280/metrics

Scrape interval vs statistics_interval
--------------------------------------

The `statistics_interval` should be set to `"manual"` on trunk if and only
if you have a single Prometheus instance scraping Prosody. This will allow
the internal statistics gathering to run optimally.

If you have multiple instances scraping Prosody, set `statistics_interval`
to the scrape interval of Prometheus to avoid errors in rate calculations
and similar.

Future work will allow the use of `"manual"` with multiple Prometheus
instances and varying scrape intervals (stay tuned).

Compatibility
=============

  ------- -------------
  0.12    Works (but replaced by [mod_http_openmetrics](https://prosody.im/doc/modules/mod_http_openmetrics))
  0.11    Works
  0.10    Works
  0.9     Does not work
  ------- -------------
