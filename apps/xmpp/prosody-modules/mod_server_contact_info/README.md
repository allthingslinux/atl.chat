---
labels:
- 'Stage-Alpha'
summary: Backported mod_server_contact_info for Prosody 0.12
...

## Overview

In February 2024 we improved the internal API to allow multiple modules to
publish information about the server, this includes mod_pubsub_serverinfo.

Although Prosody 0.12 comes with its own mod_server_contact_info, this version
uses the new API so that 0.12 users can hopefully use mod_pubsub_serverinfo
and other modules which use the new API.

To use it, you must ensure that your Prosody 0.12 deployment is loading *both*
mod_server_contact_info **and** mod_server_info community modules.

Configuration of contact addresses is the same, whatever version of the module
you use. See the official documentation on [Prosody's mod_server_contact_info](https://prosody.im/doc/modules/mod_server_contact_info)
page.

## Compatibility

This module should be compatible with Prosody 0.12, and will fail to load in
later versions (which already provide the same functionality without community
modules).
