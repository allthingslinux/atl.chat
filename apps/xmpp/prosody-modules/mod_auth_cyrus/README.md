---
title: Cyrus SASL
rockspec:
  build:
    modules:
      mod_auth_cyrus.sasl_cyrus: sasl_cyrus.lua
---

# Introduction

XMPP uses a standard authentication protocol called 'SASL' to validate
client credentials. Prosody has a built-in SASL library, and uses this
by default to validate credentials against Prosody's internal account
store.

Alternatively Prosody supports using Cyrus SASL, an external SASL
provider which can validate user-supplied credentials against other
sources, such as PAM, LDAP, SQL and more. It also allows the use of
GSSAPI for single-sign-on services.

# Usage

## lua-cyrussasl

To allow Prosody to access Cyrus SASL you need to install lua-cyrussasl.
Information on how to do that on most platforms can be found on our
[dependencies page](/doc/depends). Those running Debian/Ubuntu can
simply:

``` {.code}
 sudo apt-get install lua-cyrussasl
```

On Redhat/CentOS, the [EPEL
repository](https://fedoraproject.org/wiki/EPEL) needs to be enabled,
after which you can install the package:

``` {.code}
 sudo yum install lua-cyrussasl
```

## Configuration

Enable the cyrus backend by adding the following line to your config
file:

``` {.code .lua}
   authentication = "cyrus"
   cyrus_service_name = "xmpp" -- Optional, defaults to "xmpp"
```

Configuring Cyrus SASL itself is currently beyond the scope of this
documentation. If you feel you could contribute a simple how-to, or know
the link of a good one to add below then [let us know](/discuss)
[:smile:]{.icon}

Prosody's Cyrus SASL-related options:

  Option                       Default   Description
  ---------------------------- --------- --------------------------------------------------------------------------------------------------------------
  cyrus_service_name           xmpp      The service name to pass to Cyrus SASL.
  cyrus_service_realm          (auto)    The realm to pass to Cyrus SASL, the virtual host the user is signing into if not specified.
  cyrus_require_provisioning   false     If true then Prosody requires user accounts to exist in Prosody, even if successfully authenticated via SASL
  cyrus_application_name       prosody   The application name to pass to Cyrus SASL. Determines the Cyrus SASL configuration file name.
  cyrus_server_fqdn                      hostname passed to Cyrus

## Troubleshooting

### Permissions

One of the most common issues is Prosody being unable to access the
saslauthd socket (this is obviously only an issue if you are using the
saslauthd daemon), used to communicate with the authentication daemon.
An example error caused by this would be:

``` {.code}
 Got SASL error condition -1: Password verification failed
```

This can be confirmed by trying testsaslauthd as root and then as the
user prosody runs as (typically 'prosody'); the former should succeed
and the latter should fail.

The solution is to make sure that prosody can access the socket
(typically in /var/run/saslauthd/) by adding the 'prosody' user to the
'sasl' group (or otherwise ensuring that the prosody user has filesystem
permissions to access the socket).

### Cyrus SASL Configuration file {#cyrus_sasl_configuration_file}

Cyrus SASL needs a configuration file in order to know where to look for
user credentials. For Prosody, the file will be named prosody.conf by
default. Its location varies by OS and distribution; refer to the table
below or your local system documentation for where it should go.

  Location     Platforms
  ------------ -------------------
  /etc/sasl    Debian and Ubuntu
  /etc/sasl2   Arch, RHEL/CentOS

The contents of the configuration file depend on what you want to
authenticate against. If you want to authenticate against local
accounts, you'll want to set up saslauthd (the configuration of
saslauthd varies from system to system), and your prosody.conf will look
like this:

``` {.code}
pwcheck_method: saslauthd
mech_list: PLAIN
```

If using saslauthd, you must specify only PLAIN in the mech_list, as it
only supports plaintext authentication methods.

## Other references {#other_references}

-   [Setting up Prosody to authenticate against LDAP (blog
    post)](http://blog.marc-seeger.de/2009/12/30/setting-up-prosody-to-authenticate-against-ldap/)
    -   This post uses xmpp.conf, but the name is now prosody.conf (see
        cyrus_application_name above)
-   [Surviving Cyrus SASL
    (PDF)](http://www.arschkrebs.de/slides/surviving_cyrus_sasl-handout.pdf)
    [(view)](http://docs.google.com/viewer?url=http%3A%2F%2Fwww.arschkrebs.de%2Fslides%2Fsurviving_cyrus_sasl-handout.pdf)
-   [Cyrus SASL error
    codes](http://cvs.opensolaris.org/source/xref/onnv/onnv-gate/usr/src/lib/libsasl/include/sasl.h#186)
