---
labels:
...

Introduction
============

mod\_net\_dovecotauth is a server implementation of the Dovecot
authentication protocol. It allows you to authenticate e.g. Postfix
against your Prosody installation.

Due to missing support for virtal hosts in this protocol, only one host
can be supported.

Configuration
=============

Install and add to modules\_enabled like any other module.

    dovecotauth_host = "example.com" -- Must be a defined VirtualHost

Compatibility
=============

Works with 0.9
