---
labels:
- 'Stage-Alpha'
summary: 'XEP-0489: Reporting Account Affiliations'
rockspec:
  build:
    modules:
      mod_report_affiliations.traits: traits.lib.lua
---


This module implements [XEP-0489: Reporting Account Affiliations](https://xmpp.org/extensions/xep-0489.html).
It can help with spam on the network, especially if you run a public server
that allows registration.

## How it works

Here is the scenario: you run a public server. Despite your best efforts, and
following the [best practices](https://prosody.im/doc/public_servers), some
spammers still occasionally manage to register on your server. Because of
this, other servers on the network start filtering messages from all accounts
on your server.

Enabling this module will include additional information in certain kinds of
outgoing traffic, which allows other servers to judge the sending account,
rather than the whole server.

### When is affiliation information shared?

Affiliation is shared when a user on your server:

- sends a message to a user that has not (yet) authorized them
- sends a subscription request to a user
- sends a "directed presence" to a remote JID (for example, when joining a
  group chat).

### What information is shared?

The following information is included in matching traffic:

- The affiliation of the account:
  - "guest" (the account is anonymous/temporary)
  - "registered" (the account was self-registered)
  - "member" (the account belongs to a recognised/trusted member of the server)
  - "admin" (the account belongs to a server administrator)

For the "registered" affiliation, the following additional items are included:

- When the account was created
- The "trust level" of the account

### What is the trust level?

This is a score out of 100 which indicates how trusted the account is. It is
automatically calculated, and the calculation may include various factors
provided by installed modules. At this time, in a default installation, the
reported value is always 50.

## Configuration

### Allowing queries

In most cases, Prosody will automatically include the affiliation information
when necessary. However it is also possible to provide affiliation on-demand,
in response to queries.

To avoid leaking information about the server's registered users, queries are
restricted by default.

You can configure a list of servers from which queries are permitted, by using
the 'report_affiliations_trusted_servers' option:

```lua
report_affiliations_trusted_servers = { "rtbl.example.net" }
```

In this example, permission has been granted to an RTBL service, so that it
can query the server and avoid adding legitimate users to the blocklist, even
if it receives reports about them (obviously this is just an example, RTBLs
will decide their own policies).

### Tweaking roles

Prosody automatically maps its standard roles to the affiliations defined by
the XEP. If your deployment uses custom roles, you can customize the mapping
by specifying the list of roles that should be mapped to a given affiliation.
This can be done using the following options:

- report_affiliations_admin_roles
- report_affiliations_member_roles
- report_affiliations_registered_roles
- report_affiliations_anonymous_roles

For example, to consider the 'company:staff' role as members, as well as the
built-in prosody:member role, you might set the following:

```lua
report_affiliations_member_roles = { "prosody:member", "company:staff" }
```

## Compatibility

Should work with 0.12, but has not been tested. 0.12 does not support the
"member" role, so all non-anonymous/non-admin accounts will be reported as
"registered".

Tested with trunk (2024-11-22).

