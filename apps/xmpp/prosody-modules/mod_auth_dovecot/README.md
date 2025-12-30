---
labels:
- 'Stage-Alpha'
- 'Type-Auth'
summary: Dovecot authentication module
rockspec:
  build:
    modules:
      mod_auth_dovecot: auth_dovecot/mod_auth_dovecot.lua
      mod_auth_dovecot.sasl_dovecot: auth_dovecot/sasl_dovecot.lib.lua
...

Introduction
============

This is a Prosody authentication plugin which uses Dovecot as the
backend.

Configuration
=============

As with all auth modules, there is no need to add this to
modules\_enabled. Simply add in the global section, or for the relevant
hosts:

    authentication = "dovecot"

These options are used by mod\_auth\_dovecot:

  Name                    Description                               Default value
  ----------------------- ----------------------------------------- -------------------------------
  dovecot\_auth\_socket   Path to the Dovecot auth socket           "/var/run/dovecot/auth-login"
  auth\_append\_host      If true, sends the bare JID as authzid.   false

The Dovecot user and group must have access to connect to this socket.
You can create a new dedicated socket for Prosody too. Add the below to
the *socket listen* section of /etc/dovecot/dovecot.conf, and match the
socket path in Prosody's dovecot\_auth\_socket setting.

    service auth {
        unix_listener /var/spool/prosody/private/auth-client {
            mode = 0660
            user = prosody
            group = prosody
        }
    }

Make sure the socket directories exist and are owned by the Prosody
user.

Note: Dovecot uses UNIX sockets by default. luasocket is compiled with
UNIX socket on debian/ubuntu by default, but is not on many other
platforms. If you run into this issue, you would need to either
recompile luasocket with UNIX socket support, or use Dovecot 2.x's TCP
socket support.

TCP socket support for Dovecot 2.x
----------------------------------

Dovecot 2.x includes TCP socket support. These are the relevant
mod\_auth\_dovecot options:

  Name                  Description               Default value
  --------------------- ------------------------- ----------------------------
  dovecot\_auth\_host   Hostname to connect to.   "127.0.0.1"
  dovecot\_auth\_port   Port to connect to.       *(this value is required)*

Compatibility
=============

  ------- -------
  trunk   Works
  0.8     Works
  ------- -------
