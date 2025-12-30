---
labels:
- "Stage-Beta"
summary: "Turn forgejo/github/gitlab webhooks into atom-in-pubsub"
rockspec:
  build:
    modules:
      mod_pubsub_forgejo.templates: templates.lib.lua
      mod_pubsub_forgejo.format: format.lib.lua
---

# Introduction

This module accepts Forgejo webhooks and publishes them to a local
pubsub component as Atom entries for XMPP clients to subscribe to.
Such entries can be viewed with a pubsub-compatible XMPP client such as
[movim](https://movim.eu/) or [libervia](https://libervia.org/), or turned
into chat messages with a bot (cf last section of this document).
It is a more customisable `mod_pubsub_github`.

It should also work with other forges such as github and gitlab (to be tested).

# Configuration

## Basic setup

Load the module on a pubsub component:

```{.lua}
Component "pubsub.example.com" "pubsub"
    modules_enabled = { "pubsub_forgejo" }
    forgejo_secret = "something-very-secret"  -- copy this in the Forgejo web UI
```

The "Target URL" to configure in the Forgejo web UI should be either:

- `http://pubsub.example.com:5280/pubsub_forgejo`
- `https://pubsub.example.com:5281/pubsub_forgejo`

If your HTTP host doesn't match the pubsub component's address, you will
need to inform Prosody. For more info see Prosody's [HTTP server
documentation](https://prosody.im/doc/http#virtual_hosts).

## Advanced setup

### Publishing settings

#### Pubsub actor

By default, `forgejo_actor` is unset; this results in nodes being created by the prosody superuser.
Change this if you set up access control and you know what you are doing.

#### Pubsub node

By default, all events are published in the same pubsub node named "forgejo".
This can be changed by setting `forgejo_node` to a different value.

Another option is to used different nodes based on which repository emitted the webhook.
This is useful if you configured the webhook at the user (or organisation) level instead of repository-level.
To set this up, define `forgejo_node_prefix` and `forgejo_node_mapping`.
`forgejo_node_mapping` must be a key in the the webhook "repository" payload, e.g., "full*name". Example: with `forge_node_prefix = "forgejo---"` and `forgejo_node_mapping = "full_name"`, webhooks emitted by the repository \_repo-name* in the _org-name_ organisation will be published in the node _forgejo---org-name/repo-name_.

### Customizing the atom entry

#### Pushes with no commits

By default, pushes without commits (i.e., pushing tags) are ignored, because it leads
to weird entries like "romeo pushed 0 commit(s) to repo".
This behaviour can be changed by setting `forgejo_skip_commitless_push = false`.

#### Atom entry templates

By default, 3 webhooks events are handled (push, pull_request and release),
and the payload is turned into a atom entry by
using [util.interpolation](https://prosody.im/doc/developers/util/interpolation) templates.
The default templates can be viewed in the source of this module, in the `templates.lib.lua`
file.

You can customise them using by setting `forgejo_templates`, which is merged with the default
templates.
In this table, keys are forgejo event names (`x-forgejo-template` request header).
Values of this table are tables too, where keys are atom elements and values are the templates
passed to [util.interpolation](https://prosody.im/doc/developers/util/interpolation).

A few filters are provided:

- `|shorten` strips the last 32 characters: useful to get a short commit hash
- `|firstline` only keeps the first line: useful to get a commit "title"
- `|branch` strips the first 12 characters: useful to get a branch name from `data.ref`
- `|tag` strips the first 11 characters: useful to get a tag name from `data.ref`

Example:

```{.lua}
forgejo_templates = {
	pull_request = nil,  -- suppress handling of `pull_request` events
	release = {          -- data is the JSON payload of the webhook
		title = "{data.sender.username} {data.action} a release for {data.repository.name}",
		content = "{data.release.name}",
		id = "release-{data.release.tag_name}",
		link = "{data.release.html_url}"
	}
}
```

Examples payloads are provided in the `webhook-examples`

# Publishing in a MUC

You can use a bot that listen to pubsub events and converts them to MUC messages.
MattJ's [riddim](https://matthewwild.co.uk/projects/riddim/) is well suited for that.

Example config, single pubsub node:

```{.lua}
jid = "forgejo-bot@example.com"
password = "top-secret-stuff"
room = "room@rooms.example.com"
autojoin = room

pubsub2room = {
  "pubsub.example.com#forgejo" = {
    room = room,
    template = "${title}\n${content}\n${link@href}"
  }
}
```

Example with several nodes:

```{.lua}
local nodes = {"forgejo---org/repo1", "forgejo---org/repo2"}
pubsub2room = {}

for _, node in ipairs(slidge_repos) do
  pubsub2room = ["pubsub.example.com#" .. node] = {
    room = room,
    template = "${title}\n${content}\n${link@href}"
  }
end
```

# TODO

- Default templates for all event types
- (x)html content

# Compatibility

Works with prosody 0.12
