---
labels:
- 'Stage-Beta'
summary: Manually specify SRV records
...

Introduction
============

This Prosody plugin lets you manually override SRV records used for a
remote host.

Usage
=====

Simply add `"srvinjection"` to your `modules_enabled` list to enable.
Then add the `srvinjection` option to the global section.

Configuration
=============

The `srvinjection` option can be used as follows:

    srvinjection = {
      ["example.com"] = {"localhost", 5000};
      ["jabber.org"] = {"localhost", 5001};
    };

The format for individual items is
`["remote-hostname"] = {"srv-hostname", srv-port};`.

The special remote hostname `"*"` can be used as a wildcard:

        srvinjection = { ["*"] = {"xmpp-server.l.google.com", 5269} } -- Use Google's XMPP server for all hostnames

Reloading
=========

The module can be reloaded via the telnet console. Edit the config file
to make any updates.

You can reload the configuration from disk:

    config:reload()

And then reload the module to apply the configuration changes:

    module:reload("srvinjection", "*")

Compatibility
=============

  ----- -------
  0.8   Works
  0.7   Works
  0.6   Works
  ----- -------

How it works
============

The module replaces the `lookup` function of the `net.adns` module with
its own. The original is set back when the module is unloaded.
