---
depends:
- 'mod\_http'
- 'mod\_muc'
provides:
- http
title: 'mod\_muc\_badge'
---

# Introduction

This module generates a badge for MUC rooms at a HTTP URL like
`https://conference.example.com:5281/muc_badge/room@conference.example.org`
containing the number of occupants.

Inspiration
:   <https://opkode.com/blog/xmpp-chat-badge/>

# Configuration

  Option             Type     Default
  ------------------ -------- --------------------------
  `badge_count`      string   `"%d online"`
  `badge_template`   string   A SVG image (see source)

The template must be valid XML. If it contains `{label}` then this is
replaced by `badge_label`, similarly, `{count}` is substituted by
`badge_count` with `%d` changed to the number of occupants.

Details of the HTTP URL is determined by [standard Prosody HTTP server
configuration][doc:http].

# Example

```lua
Component "conference.example.com" "muc"
modules_enabled = {
    "muc_badge"
}
```
