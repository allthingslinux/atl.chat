# Introduction

This module exposes users [microblogging][xep277] on Prosodys built-in HTTP server.

# Usage

With default HTTP settings, the microblog of `user@example.com` would be
seen at `https://example.com:5281/atom/user`.

# Configuration

The module itself has no options. However it uses the access control
mechanisms in PubSub, so users must reconfigure their microblogging node
to allow access, by setting `access_model` to `open`.
E.g. Gajim has UI for this, look for "Personal Events" → "Configure
services".

