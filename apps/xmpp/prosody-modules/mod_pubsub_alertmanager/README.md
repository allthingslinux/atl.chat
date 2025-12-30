---
labels:
- 'Stage-Alpha'
summary: Alertmanager webhook receiver for pubsub
---

# Introduction

This module lets
[Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
publish alerts to [pubsub][doc:pubsub] via
[webhooks](https://prometheus.io/docs/alerting/latest/configuration/#webhook_config).

# Setup

The relevant pubsub nodes must be created and configured somehow.
Because the request IP address is used to publish, the `publisher`
affiliation should be given to the IP address Alertmanager sends
webhooks from.

# Configuration

## Prometheus

A Prometheus `rule_files` might contain something along these lines:

``` yaml
groups:
- name: Stuff
  rules:
  - alert: Down
    expr: up == 0
    for: 5m
    annotations:
      title: 'Stuff is down!'
    labels:
      severity: 'critical'
```

## Alertmanager
On the Alertmanager site the webhook configuration may look something
like this:

``` yaml
receivers:
- name: pubsub
  webhook_configs:
  - url: http://pubsub.localhost:5280/pubsub_alertmanager
```

And then finally some Alertmanager routes would point at that receiver:

``` yaml
route:
  receiver: pubsub
```

## Prosody

On the Prosody side, apart from creating and configuring the node(s)
that will be used, configure your pubsub service like this:

``` lua
Component "pubsub.example.com" "pubsub"
modules_enabled = {
    "pubsub_alertmanager",
}

-- optional extra settings:
alertmanager_body_template = [[
*ALARM!* {annotations.title?Alert} is {status}
Since {startsAt}{endsAt& until {endsAt}}
Labels: {labels%
  {idx}: {item}}
Annotations: {annotations%
  {idx}: {item}}
]]

alertmanager_node_template = "alerts/{alert.labels.severity}"
```

If no node template is given, either an optional part after
"pubsub_alertmanager" in the HTTP path is used as node, or the string
"alerts". Here, an alerts would be published to different nodes based on
the 'severity' label, so e.g. `alerts/critical` in this example.

## All Options

Available configuration options:

`alertmanager_body_template`
:   Template for the textual representation of alerts.

`alertmanager_node_template`
:   Template for the pubsub node name, defaults to `"{path?alerts}"`

`alertmanager_path_configs`
:   Per-path configuration variables (see below).

### Per-path configuration

It's possible to override configuration options based on the path suffix. For
example, if a request is made to `http://prosody/pubsub_alertmanager/foo` the
path suffix is `foo`. You can then supply the following configuration:

``` lua
alertmanager_path_configs = {
    foo = {
        node_template = "alerts/{alert.labels.severity}";
        publisher = "user@example.net";
    };
}
```
