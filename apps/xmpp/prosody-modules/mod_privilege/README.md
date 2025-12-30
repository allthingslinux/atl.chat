---
labels:
- 'Stage-Beta'
summary: 'XEP-0356 (Privileged Entity) implementation'
...

Introduction
============

Privileged Entity is an extension which allows entity/component to have
privileged access to server (set/get roster, send message on behalf of server,
send IQ stanza on behalf of user, access presence information). It can be used
to build services independently of server (e.g.: PEP service).

Details
=======

You can have all the details by reading the
[XEP-0356](http://xmpp.org/extensions/xep-0356.html).

Only the latest version of the XEP is implemented (using namespace
`urn:xmpp:privilege:2`), if your component use an older version, please update.

Note that roster permission is not fully implemented yet, roster pushes are not yet sent
to privileged entity.

Usage
=====

To use the module, like usual add **"privilege"** to your
modules\_enabled. Note that if you use it with a local component, you
also need to activate the module in your component section:

    modules_enabled = {
            [...]
        
            "privilege";
    }

    [...]

    Component "pubsub.yourdomain.tld"
        component_secret = "yourpassword"
        modules_enabled = {"privilege"}

then specify privileged entities **in your host section** like that:

    VirtualHost "yourdomain.tld"

        privileged_entities = {
            ["romeo@montaigu.lit"] = {
                roster = "get";
                presence = "managed_entity";
            },
            ["juliet@capulet.lit"] = {
                roster = "both";
                message = "outgoing";
                presence = "roster";
            },
            ["pubsub.yourdomain.tld"] = {
                roster = "get";
                message = "outgoing";
                presence = "roster";
                iq = {
                    ["http://jabber.org/protocol/pubsub"] = "set";
                };
            },
        }

Here *romeo@montaigu.lit* can **get** roster of anybody on the host, and will
**have presence for any user** of the host, while *juliet@capulet.lit* can
**get** and **set** a roster, **send messages** on behalf of the server, and
**access presence of anybody linked to the host** (not only people on the
server, but also people in rosters of users of the server).

*pubsub.yourdomain.tld* is a Pubsub/PEP component which can **get** roster of
anybody on the host, **send messages** on the behalf of the server, **access
presence of anybody linked to the host**, and **send IQ stanza of type "set" for
the namespace "http://jabber.org/protocol/pubsub"** (this can be used to
implement XEP-0376 "Pubsub Account Management").

**/!\\ Be extra careful when you give a permission to an entity/component, it's
a powerful access, only do it if you absolutely trust the component/entity, and
you know where the software is coming from**

Configuration
=============

roster
------

All the permissions give access to all accounts of the virtual host.

  -------- ------------------------------------------------ ----------------------
  roster   none *(default)*                                 No access to rosters
  get      Allow **read** access to rosters                 
  set      Allow **write** access to rosters                
  both     Allow **read** and **write** access to rosters   
  -------- ------------------------------------------------ ----------------------

Note that roster implementation is incomplete at the moment, roster pushes are not yet
send to privileged entity.

message
-------

  ------------------ ------------------------------------------------------------
  none *(default)*   Can't send message from server
  outgoing           Allow to send message on behalf of server (from bare jids)
  ------------------ ------------------------------------------------------------

presence
--------

  ------------------ ------------------------------------------------------------------------------------------------
  none *(default)*   Do not have extra presence information
  managed\_entity    Receive presence stanzas (except subscriptions) from host users
  roster             Receive all presence stanzas (except subsciptions) from host users and people in their rosters
  ------------------ ------------------------------------------------------------------------------------------------

iq
--

IQ permission is a table mapping allowed namespaces to allowed stanza type. When
a namespace is specified, IQ stanza of the specified type (see below) can be
sent if and only if the first child element of the IQ stanza has the specified
namespace. See https://xmpp.org/extensions/xep-0356.html#iq for details.

Allowed stanza type:

  -------- -------------------------------------------
  get      Allow IQ stanza of type **get**
  set      Allow IQ stanza of type **set**
  both     Allow IQ stanza of type **get** and **set**
  -------- -------------------------------------------

Compatibility
=============

If you use it with Prosody 0.9 and with a component, you need to patch
core/mod\_component.lua to fire a new signal. To do it, copy the
following patch in a, for example, /tmp/component.patch file:

``` {.patch}
    diff --git a/plugins/mod_component.lua b/plugins/mod_component.lua
    --- a/plugins/mod_component.lua
    +++ b/plugins/mod_component.lua
    @@ -85,6 +85,7 @@
                    session.type = "component";
                    module:log("info", "External component successfully authenticated");
                    session.send(st.stanza("handshake"));
    +               module:fire_event("component-authenticated", { session = session });
     
                    return true;
            end
```

Then, at the root of prosody, enter:

`patch -p1 < /tmp/component.patch`

  ----- --------------------------------------------------
  trunk Works
  0.12  Works
  0.11  Works
  0.10  Works
  0.9   Need a patched core/mod\_component.lua (see above)
  ----- --------------------------------------------------

Note
====

This module is often used with mod\_delegation (c.f. XEP for more details)
