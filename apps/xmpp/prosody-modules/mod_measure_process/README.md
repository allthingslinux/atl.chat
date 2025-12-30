---
labels:
- Statistics
summary: Measure process resource use metrics (cpu, memory, file descriptors)
---

Description
===========

This module exposes process resource use metrics similar to those exposed by
default when using a Prometheus client library. Specifically, the following
metrics are exposed:

- CPU use
- Resident set and virtual memory size
- Number of open file descriptors and their limit

This module uses the new OpenMetrics API and thus requires a recent version
of Prosody trunk (0.12+).

Compatibility
=============

  ------- -------------
  trunk   Works
  0.11    Does not work
  ------- -------------
