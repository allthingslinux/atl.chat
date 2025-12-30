---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: IMAP authentication module
rockspec:
  build:
    modules:
      mod_auth_imap: auth_imap/mod_auth_imap.lua
      mod_auth_imap.sasl_imap: auth_imap/sasl_imap.lib.lua
...

Introduction
============

This is a Prosody authentication plugin which uses a generic IMAP server
as the backend.

Configuration
=============

  option                            type      default
  --------------------------------- --------- --------------------------------
  imap\_auth\_host                  string    localhost
  imap\_auth\_port                  number    nil
  imap\_auth\_realm                 string    Same as the sasl\_realm option
  imap\_auth\_service\_name         string    nil
  auth\_append\_host                boolean   false
  auth\_imap\_verify\_certificate   boolean   true
  auth\_imap\_ssl                   table     A SSL/TLS config
