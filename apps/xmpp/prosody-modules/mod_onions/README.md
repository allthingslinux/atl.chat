---
labels:
- 'Stage-Alpha'
summary: s2s to Tor hidden services
...

Introduction
============

This plugin allows Prosody to connect to other servers that are running
as a Tor hidden service. Running Prosody on a hidden service works
without this module, this module is only necessary to allow Prosody to
federate to hidden XMPP servers.

For general info about creating a hidden service, see
[https://community.torproject.org/onion-services/setup/](https://community.torproject.org/onion-services/setup/).

Usage
=====

This module depends on the bit32 Lua library.

To create a hidden service that can federate with other hidden XMPP
servers, first add a hidden serivce to Tor. It should listen on port
5269 and optionally also on 5222 (if c2s connections to the hidden
service should be allowed).

Use the hostname that Tor gives with a virtualhost:

    VirtualHost "555abcdefhijklmn.onion"
        modules_enabled = { "onions" };

Configuration
=============

  Name                   Description                                           Type      Default value
  ---------------------- ----------------------------------------------------- --------- ---------------
  onions\_socks5\_host   the host to connect to for Tor's SOCKS5 proxy         string    "127.0.0.1"
  onions\_socks5\_port   the port to connect to for Tor's SOCKS5 proxy         integer   9050
  onions\_only           forbid all connection attempts to non-onion servers   boolean   false
  onions\_tor\_all       pass all s2s connections through Tor                  boolean   false
  onions\_map            override the address for a host                       table     {}

By setting `onions_map`, it is possible to override the address used to
connect to a given host with the address of a hidden service. The
configuration of `onions_map` works as follows:

    onions_map = {
        ["jabber.calyxinstitute.org"] = "ijeeynrc6x2uy5ob.onion";
    }

or, to also specify a port:

    onions_map = {
        ["jabber.calyxinstitute.org"] = { host = "ijeeynrc6x2uy5ob.onion", port = 5269 };
    }

Compatibility
=============

  ----- --------------
  0.8   Doesn't work
  0.9   Works
  ----- --------------

Notes
=====

-   `onions_tor_all` does not look up SRV records first. Therefore it
    will fail for many servers.
-   mod\_onions currently does not support connecting to `.onion`
    entries in SRV records.

Security considerations
=======================

-   Running a hidden service on a server together with a normal server
    might expose the hidden service.
-   A hidden service that wants to remain hidden should either disallow
    s2s to non-hidden servers or pass all s2s traffic through Tor
    (setting either `onions_only` or `onions_tor_all`).
