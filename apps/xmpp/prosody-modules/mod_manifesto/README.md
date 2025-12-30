---
summary: Module for raising awareness about the Security Test Days
...

Introduction
============

This module informs users about the XMPP Test day and whether their
contacts are affected. For mor info about the test day, see
<https://stpeter.im/journal/1496.html>

Configuration
=============

``` lua
manifesto_contact_encryption_warning = [[
    Your rant about security here
]]
admin_contact_address = "mailto:xmpp@example.com"
```

`admin_contact_address` can be a JID or a `mailto:` URI.

The default for `manifesto_contact_encryption_warning` is the following:

    Hello there.

    This is a brief system message to let you know about some upcoming changes to the $HOST service.

    Some of your contacts are on other Jabber/XMPP services that do not support encryption.  As part of an initiative to increase the security of the Jabber/XMPP network, this service ($HOST) will be participating in a series of tests to discover the impact of our planned changes, and you may lose the ability to communicate with some of your contacts.

    The test days will be on the following dates: January 4, February 22, March 22 and April 19.  On these days we will require that all client and server connections are encrypted.  Unless they enable encryption before that, you will be unable to communicate with your contacts that use these services:

    $SERVICES

    Your affected contacts are:

    $CONTACTS

    What can you do?  You may tell your contacts to inform their service administrator about their lack of encryption.  Your contacts may also switch to a more secure service.  A list of public services can be found at https://xmpp.net/directory.php

    For more information about the Jabber/XMPP security initiative that we are participating in, please read the announcement at https://stpeter.im/journal/1496.html

    If you have any questions or concerns, you may contact us via $CONTACTVIA at $CONTACT

Translations would be appreciated. There is currently a Swedish
translation residing in a text file in the same directory as the module.
