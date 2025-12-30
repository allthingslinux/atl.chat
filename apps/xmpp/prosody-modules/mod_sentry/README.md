---
labels:
- 'Stage-Beta'
summary: 'Send errors to a Sentry server'
rockspec:
  build:
    modules:
      mod_sentry.sentry: sentry.lib.lua
---

# Introduction

This module forwards select events to a [Sentry](https://sentry.io/) server.

# Configuration

There is a single configuration option, `sentry`, which should be a table
containing the following parameters (optional unless otherwise stated):

`dsn`
: **Required.** The DSN of the project in Sentry.

`insecure`
: Whether to allow untrusted HTTPS certificates.

`server_name`
: The name of the current server (defaults to the system hostname).

`tags`
: An optional table of tags that will be used as the default for all
  events from this module.

`extra`
: An optional table of custom extra data to attach to all events from
  this module.

Example configuration:

```
sentry = {
    dsn = "https://37iNFnR4tferFhoTPNe8X0@example.com/11";
    tags = {
        environment = "prod";
    };
}
```

## Log forwarding

You can configure log messages to be automatically forwarded to Sentry.
This example will send all "warn" and "error" messages to Sentry, while
sending all "info" and higher messages to syslog:

```
log = {
    info = "*syslog";
    { levels = "warn", to = "sentry" };
}
```

# Developers

In addition to the automatic log forwarder, you can integrate Sentry
forwarding directly into modules using the API.

## API

Usage example:

```
local sentry = module:depends("sentry").new({
	logger = module.name;
});

sentry:event("warning")
	:message("This is a sample warning")
	:send();
```

### Events

Event objects have a number of methods you can call to add data to them.
All methods return the event itself, which means you can chain multiple
calls together for convenience.

After attaching all the data you want to include in the event, simply
call `event:send()` to submit it to the server.

#### set(key, value)

Directly set a property of the event to the given value.

#### tag(name, value)

Set the specified tag to the given value.

May also be called with a table of key/value pairs.

#### extra(name, value)

Sets the specified 'extra' data. May also be called
with a table of key/value pairs.

#### message(text)

Sets the message text associated with the event.

#### set_request(request)

Sets the HTTP request associated with the event.

This is used to indicate what incoming HTTP request
was being processed at the time of the event.

#### add_exception(e)

Accepts an error object (from util.error or any arbitrary value)
and attempts to map it to a Sentry exception.

May be called multiple times on the same event, to represent
nested exceptions (the outermost exception should be added first).

#### add_breadcrumb(timestamp, type, category, message, data)

Add a breadcrumb to the event. A breadcrumb represents any useful
piece of information that led up to the event. See Sentry documentation
for allowable types and categories.

#### add_http_request_breadcrumb(request, message)

Helper to add a breadcrumb representing a HTTP request that was made.

The `message` parameter is an optional human-readable text description
of the request.

#### send()

Sends the event to the Sentry server. Returns a promise that resolves
to the response from the server.
