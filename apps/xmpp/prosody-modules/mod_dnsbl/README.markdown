---
labels:
- 'Stage-Alpha'
summary: 'Flag accounts registered by IPs matching blocklists'
depends:
  - mod_anti_spam
---

This module is designed for servers with public registration enabled, and
makes it easier to identify accounts that have been registered by potentially
"bad" IP addresses, e.g. those that are likely to be used by spam bots.

**Note:** Running a Prosody instance with public registration enabled opens up
your server as a potential relay for spam and abuse, which can have a negative
impact on your server and the network as a whole. We do not recommended it
unless you have prior experience operating public internet services and are
prepared for the time and effort necessary to tackle any issues. For other
advice, see the Prosody documentation on [public servers](https://prosody.im/doc/public_servers).

## How does it work?

When a user account is registered on your server, this module checks the user's
IP address against a list of configured blocklists. If a match is found, it
flags the account using [mod_flags].

Flags can be reviewed and managed by using the mod_flags commands and flagged
accounts can be automatically restricted, e.g. by mod_firewall or similar.

This module supports two kinds of block lists:

- DNS blocklists (DNSBLs)
- Text files, with one IP/subnet per line

## Configuration

**Note:** mod_dnsbl requires mod_anti_spam to be installed, but it does not
need to be enabled or loaded (only some code is shared). mod_flags is also
required, and this will be automatically loaded if not specified in the
config file.

The main configuration option is `dnsbls`, a list of DNSBL addresses:

```lua
dnsbls = {
  "dnsbl.dronebl.org";
  "cbl.abuseat.org";
}
```

You can set a message to be sent to users who register from a matched IP
address:

```lua
dnsbl_message = "Your IP address has been detected on a block list. Some functionality may be restricted."
```

You can change the default flag that is applied to accounts:

```lua
dnsbl_flag = "dnsbl_hit"
```

### File-based blocklists

As well as real DNSBLs, you can also put file-based blocklists here, by
prefixing `@` to a filesystem path (Prosody must have read permission to
access the file):

```lua
dnsbls = {
  "dnsbl.dronebl.org";
  "@/etc/prosody/ip_blocklist.txt";
}
```

The file must contain a single IP address or subnet on each line, though blank
lines and comments are ignored. For example:

```
# This is a comment
203.0.113.0/24
2001:db8:7894::/64
```

File-based lists are automatically reloaded when you reload Prosody's
configuration.

### Advanced configuration

You can override the flag and message on a per-blocklist basis with a slightly
more detailed configuration syntax:

```lua
dnsbls = {
  ["dnsbl.dronebl.org"] = {
    flag = "dnsbl_hit";
    message = "Your account is restricted because your IP address has been detected as running an open proxy. For more information see https://dronebl.org/lookup?ip={registration.ip}";
  };
  ["@/etc/prosody/ip_blocklist.txt"] = {
    flag = "local_blocklist";
    message = "Your account is restricted";
  };
}
```

## Compatibility

Compatible with Prosody 0.12 and later.

If you are using Prosody 0.12, make sure you install mod_flags from the
community module repository. If you are using a later version, mod_flags is
already included with Prosody.
