---
labels:
- 'Stage-Beta'
summary: 'Log to in-memory ringbuffer'
...

Introduction
============

Sometimes debug logs are too verbose for continuous logging to disk. However
occasionally you may be interested in the debug logs when a certain event occurs.

This module allows you to store all logs in a fixed-size buffer in Prosody's memory,
and dump them to a file whenever you want.

# Configuration

First of all, you need to load the module by adding it to your global `modules_enabled`:

``` {.lua}
modules_enabled = {
    ...
    "log_ringbuffer";
    ...
}
```

By default the module will do nothing - you need to configure a log sink, using Prosody's
usual [logging configuration](https://prosody.im/doc/advanced_logging).

``` {.lua}
log = {
    -- Log errors to a file
    error = "/var/log/prosody/prosody.err";

    -- Log debug and higher to a 2MB buffer
    { to = "ringbuffer", size = 1024*1024*2, filename_template = "debug-logs-{pid}-{count}.log", signal = "SIGUSR2" };
}
```

The possible fields of the logging config entry are:

`to`
:   Set this to `"ringbuffer"`.

`levels`
:   The log levels to capture, e.g. `{ min = "debug" }`. By default, all levels are captured.

`size`
:   The size, in bytes, of the buffer. When the buffer fills,
    old data will be overwritten by new data.

`lines`
:   If specified, preserves the latest N complete lines in the
    buffer. The `size` option is ignored when this option is set.

`filename`
:   The name of the file to dump logs to when triggered.

`filename_template`
:   This parameter may optionally be specified instead of `filename. It
    may contain a number of variables, described below. Defaults to
    `"{paths.data}/ringbuffer-logs-{pid}-{count}.log"`.

Only one of the following triggers may be specified:

`signal`
:   A signal that will cause the buffer to be dumped, e.g. `"SIGUSR2"`.
    Do not use any signal that is used by any other Prosody module, to
    avoid conflicts.

`event`
:   Alternatively, the name of a Prosody global event that will trigger
    the logs to be dumped, e.g. `"config-reloaded"`.

## Filename variables

If `filename_template` is specified instead of `filename`, it may contain
any of the following variables in curly braces, e.g. `{pid}`.

`pid`
:   The PID of the current process

`count`
:   A counter that begins at 0 and increments for each dump made by
    the current process.

`time`
:   The unix timestamp at which the dump is made. It can be formatted
    to human-readable local time using `{time|yyyymmdd}` and `{time|hhmmss}`.

`paths`
:   Allows access to Prosody's known filesystem paths, use e.g. `{paths.data}`
    for the path to Prosody's data directory.

The filename does not have to be unique for every dump - if a file with the same
name already exists, it will be appended to.

## Integration with mod_debug_traceback

This module can be used in combination with [mod_debug_traceback] so that debug
logs are dumped at the same time as the traceback. Use the following configuration:

``` {.lua}
log = {
	---
	-- other optional logging config here --
	---

	{
		to = "ringbuffer";
		filename_template = "{paths.data}/traceback-{pid}-{count}.log";
		event = "debug_traceback/triggered";
	};
}
```

If the filename template matches the traceback path, both logs and traceback will
be combined into the same file. Of course separate files can be specified if preferred.

# Compatibility

0.12 and later.
