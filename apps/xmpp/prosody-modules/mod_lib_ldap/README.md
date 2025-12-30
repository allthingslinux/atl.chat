# LDAP plugin suite for Prosody

The LDAP plugin suite includes an authentication plugin (mod\_auth\_ldap2) and storage plugin
(mod\_storage\_ldap) to query against an LDAP server.  It also provides a plugin library (mod\_lib\_ldap)
for accessing an LDAP server to make writing other LDAP-based plugins easier in the future.

# LDAP Authentication

**NOTE**: LDAP authentication currently only works with plaintext auth (as opposed to DIGEST-MD5 or SCRAM)
If this isn't ok with you, don't use it!  (Or better yet, fix it =) )

With that note in mind, if you need to allow (XMPP) clients to connect to your server without TLS and
want to use this module, you need to set 'allow\_unencrypted\_plain\_auth' to true in your
configuration.  You probably don't actually want to do this, though.

To enable LDAP authentication, set 'authentication' to 'ldap2' in your configuration file.
See also http://prosody.im/doc/authentication.

# LDAP Storage

LDAP storage is currently read-only, and it only supports rosters and vCards.

To enable LDAP storage, set 'storage' to 'ldap' in your configuration file.
See also http://prosody.im/doc/storage.

# LDAP Configuration

All of the LDAP-specific configuration for the plugin set goes into an 'ldap' section
in the configuration.  You must set the 'hostname' field in the 'ldap' section to
your LDAP server's location (a custom port is also accepted, so I guess it's not strictly
a hostname).  The 'bind\_dn' and 'bind\_password' are optional if you want to bind as
a specific DN.  There should be an example configuration included with this README, so
feel free to consult that.

## The user section

The user section must contain the following keys:

  * basedn - The base DN against which to base your LDAP queries for users.
  * filter - An LDAP filter expression that matches users.
  * usernamefield - The name of the attribute in an LDAP entry that contains the username.
  * namefield - The name of the attribute in an LDAP entry that contains the user's real name.

## The groups section

The LDAP plugin suite has support for grouping (ala mod\_groups), which can be enabled via the groups
section in the ldap section of the configuration file.  Currently, you must have at least one group.
The groups section must contain the following keys:

  * basedn - The base DN against which to base your LDAP queries for groups.
  * memberfield - The name of the attribute in an LDAP entry that contains a list of a group's members. The contents of this field
                  must match usernamefield in the user section.
  * namefield - The name of the attribute in an LDAP entry that contains the group's name.

The groups section must contain at least one entry in its array section.  Each entry must be a table, with the following keys:

  * name - The name of the group that will be presented in the roster.
  * $namefield (whatever namefield is set to is the name) - An attribute pair to match this group against.
  * admin (optional) - whether or not this group's members are admins.

## The vcard\_format section

The vcard\_format section is used to generate a vCard given an LDAP entry.  See http://xmpp.org/extensions/xep-0054.html for
more information.  The JABBERID field is automatically populated.

The key/value pairs in this table fall into three categories:

### Simple pairs

Some values in the vcard\_format table are simple key-value pairs, where the key corresponds to a vCard
entry, and the value corresponds to the attribute name in the LDAP entry for the user.  The fields that
be configured this way are:

  * displayname - corresponds to FN
  * nickname - corresponds to NICKNAME
  * birthday - corresponds to BDAY
  * mailer - corresponds to MAILER
  * timezone - corresponds to TZ
  * title - corresponds to TITLE
  * role - corresponds to ROLE
  * note - corresponds to NOTE
  * rev - corresponds to REV
  * sortstring - corresponds to SORT-STRING
  * uid - corresponds to UID
  * url - corresponds to URL
  * description - corresponds to DESC

### Single-level fields

These pairs have a table as their values, and the table itself has a series of key value pairs that are translated
similarly to simple pairs.  The fields that are configured this way are:

  * name - corresponds to N
    * family - corresponds to FAMILY
    * given - corresponds toGIVEN
    * middle - corresponds toMIDDLE
    * prefix - corresponds toPREFIX
    * suffix - corresponds toSUFFIX
  * photo - corresponds to PHOTO
    * type - corresponds to TYPE
    * binval - corresponds to BINVAL
    * extval - corresponds to EXTVAL
  * geo - corresponds to GEO
    * lat - corresponds to LAT
    * lon - corresponds to LON
  * logo - corresponds to LOGO
    * type - corresponds to TYPE
    * binval - corresponds to BINVAL
    * extval - corresponds to EXTVAL
  * org - corresponds to ORG
    * orgname - corresponds to ORGNAME
    * orgunit - corresponds to ORGUNIT
  * sound - corresponds to SOUND
    * phonetic - corresponds to PHONETIC
    * binval - corresponds to BINVAL
    * extval - corresponds to EXTVAL
  * key - corresponds to KEY
    * type - corresponds to TYPE
    * cred - corresponds to CRED

### Multi-level fields

These pairs have a table as their values, and each table itself has tables as its values.  The nested tables have
the same key-value pairs you're used to, the only difference being that values may have a boolean as their type, which
converts them into an empty XML tag.  I recommend looking at the example configuration for clarification.

  * address - ADR
  * telephone - TEL
  * email - EMAIL

For example, to get something like this in your vCard:

    <TEL>
      <WORK />
      <VOICE />
      <NUMBER>555-555-5555</NUMBER>
    </TEL>

Your configuration for `telephone` will probably look something like this:

    telephone = {
      work = {
        voice = true,
        number = 'telephoneNumber',
      },
    }

### Unsupported vCard fields

  * LABEL
  * AGENT
  * CATEGORIES
  * PRODID
  * CLASS

### Example Configuration

You can find an example configuration in the dev directory underneath the
directory that this file is located in.

# Missing Features

This set of plugins is missing a few features, some of which are really just ideas:

  * Implement non-plaintext authentication.
  * Use proper LDAP binding (LuaLDAP must be patched with http://prosody.im/patches/lualdap.patch, though)
  * Non-hardcoded LDAP groups (derive groups from LDAP queries)
  * LDAP-based MUCs (like a private MUC per group, or something)
  * This suite of plugins was developed with a POSIX-style setup in mind; YMMV. Patches to work with other setups are welcome!
  * Add ability for users to change their vCard/passwords/etc from within Prosody
