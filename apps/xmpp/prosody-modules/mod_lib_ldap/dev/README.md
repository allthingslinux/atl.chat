Developer Utilities/Tests
=========================

This directory exists for reasons of sanity checking.  If you wish
to run the tests, set up Prosody as you normally would, and install the LDAP
modules as normal as well.  Set up OpenLDAP using the configuration directory
found in this directory (slapd.conf), and run the following command to import
the test definitions into the LDAP server:

    ldapadd -x -w prosody -D 'cn=Manager,dc=example,dc=com' -f posix-users.ldif

Then just run prove (you will need perl and AnyEvent::XMPP installed):

    prove t
