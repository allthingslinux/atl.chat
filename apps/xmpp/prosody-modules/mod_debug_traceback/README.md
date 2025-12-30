---
labels:
- 'Stage-Alpha'
summary: Generate tracebacks on-demand
---

# Introduction

This module writes out a traceback to a file when a chosen signal (by default
`SIGUSR1`) is received. It can be useful to diagnose cases where Prosody is
unresponsive.

# Configuration

`debug_traceback_filename`
:   The name of the file to write the traceback to. Some variables
    are supported, see [mod_log_ringbuffer] docs for more info. Defaults
    to `{paths.data}/traceback-{pid}-{count}.log`.

`debug_traceback_signal`
:   The name of the signal to listen for. Defaults to `SIGUSR1`.

# Compatibility

Prosody 0.12 or later.
