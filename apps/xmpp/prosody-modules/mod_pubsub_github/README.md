---
labels:
- 'Stage-Beta'
summary: Publish Github commits over pubsub
---

## Introduction

This module accepts Github web hooks and publishes them to a local
pubsub component for XMPP clients to subscribe to.

Entries are pushed as Atom payloads.

It may also work with Gitlab.

## Configuration

Load the module on a pubsub component:

``` {.lua}
Component "pubsub.example.com" "pubsub"
    modules_enabled = { "pubsub_github" }
    github_secret = "NP7bZooYSLKze96TQMpFW5ov"
```

The URL for Github to post to would be either:

-   `http://pubsub.example.com:5280/pubsub_github`
-   `https://pubsub.example.com:5281/pubsub_github`

The module also takes the following config options:

  Name                    Default             Description
  ----------------------- ------------------- ------------------------------------------------------------
  `github_node`           `"github"`{.lua}    The pubsub node to publish commits on.
  `github_secret`         **Required**        Shared secret used to sign HTTP requests.
  `github_node_prefix`    `"github/"`{.lua}
  `github_node_mapping`   *not set*           Field in repository object to use as node instead of `github_node`
  `github_actor`          *superuser*         Which actor to do the publish as (used for access control)

More advanced example

``` {.lua}
Component "pubsub.example.com" "pubsub"
    modules_enabled = { "pubsub_github" }
    github_actor = "github.com"
    github_node_mapping = "name" --> github_node_prefix .. "repo"
    -- github_node_mapping = "full_name" --> github_node_prefix .. "owner/repo"
    github_secret = "sekr1t"
```

If your HTTP host doesn't match the pubsub component's address, you will
need to inform Prosody. For more info see Prosody's [HTTP server
documentation](https://prosody.im/doc/http#virtual_hosts).

## Compatibility

  ------ -------------
  0.10   Should work
  0.9    Works
  ------ -------------
