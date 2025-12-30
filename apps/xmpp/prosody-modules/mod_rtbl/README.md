---
summary: 
rockspec:
  dependencies:
  - mod_pubsub_subscription
labels:
- Stage-Alpha
...

This module allows other modules to subscribe to real-time blocklists using
pubsub (XEP-0060). As entries are added and removed from the blocklist, it
notifies other modules so they can perform appropriate actions.

# Configuring

This module does not do anything on its own. It **should not** be
added directly to your configuration file.

Instead, you might want to look at modules which use mod\_rtbl, such as:

- mod\_anti\_spam
- mod\_muc\_rtbl

# Compatibility

Should work with Prosody >= 0.12.x
