---
labels:
- 'Stage-Beta'
summary: 'XEP-0355 (Namespace Delegation) implementation'
...

Introduction
============

Namespace Delegation is an extension which allows server to delegate some
features handling to an entity/component. Typical use case is an external PEP
service, but it can be used more generally when your preferred server lack one
internal feature, and you found an external component which can do it.

Details
=======

You can have all the details by reading the
[XEP-0355](http://xmpp.org/extensions/xep-0355.html). Only the admin mode is
implemented so far.

Usage
=====

To use the module, like usual add **"delegation"** to your *modules\_enabled*.
Note that if you use it with a local component, you also need to activate the
module in your component section:

    modules_enabled = {
            [...]

            "delegation";
    }

    [...]

    Component "youcomponent.yourdomain.tld"
        component_secret = "yourpassword"
        modules_enabled = {"delegation"}

then specify delegated namespaces **in your host section** like that:

    VirtualHost "yourdomain.tld"

        delegations = {
            ["urn:xmpp:mam:2"] = {
                filtering = {"node"};
                jid = "pubsub.yourdomain.tld";
            },
            ["http://jabber.org/protocol/pubsub"] = {
                jid = "pubsub.yourdomain.tld";
            },
            ["http://jabber.org/protocol/pubsub#owner"] = {
                jid = "pubsub.yourdomain.tld";
            },
            ["urn:xmpp:delegation:2:bare:disco#info:*"] = {
                jid = "pubsub.yourdomain.tld";
            },
            ["urn:xmpp:delegation:2:bare:disco#items:*"] = {
                jid = "pubsub.yourdomain.tld";
            },

        }

Here all MAM requests with a "node" attribute (i.e. all MAM pubsub request) will
be delegated to pubsub.yourdomain.tld. Similarly, all pubsub request to the host
(i.e. the PEP requests) will be delegated to pubsub.yourdomain.tld. Check the
XEP for the meaning of "urn:xmpp:delegation:2:bare:disco#info:*" and
"urn:xmpp:delegation:2:bare:disco#items:*".

**/!\ Be extra careful when you give a delegation to an entity/component, it's a
powerful access, only do it if you absolutely trust the component/entity, and
you know where the software is coming from**

Configuration
=============

The configuration is done with a table which map delegated namespace to
namespace data. Namespace data MUST have a **jid** (in the form **jid =
"delegated@domain.tld"**) and MAY have an additional **filtering** array. If
filtering is present, request with attributes in the array will be delegated,
others will be treated normally (i.e. by Prosody).

If you are not a developer, the delegated namespace(s)/attribute(s) are most
probably specified with the external component/entity you want to use.

The pseudo-namespace `http://jabber.org/protocol/disco#items:*` is used to
delegate remaining disco#items (i.e. items nodes not already handled by Prosody
itself).

Compatibility
=============

If you use it with Prosody 0.9 and a component, you need to patch
core/mod\_component.lua to fire a new signal. To do it, copy the following patch
in a, for example, /tmp/component.patch file:

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

Then, at the root of prosody, enter:

`patch -p1 < /tmp/component.patch`

  ----- ----------------------------------------------------
  0.11  Works
  0.10  Works
  0.9   Need a patched core/mod\_component.lua (see above)
  ----- ----------------------------------------------------

Note
====

This module is often used with mod\_privilege (c.f. XEP for more details)
