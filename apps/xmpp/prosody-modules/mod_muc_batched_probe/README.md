# mod_muc_batched_probe

This module allows you to probe the presences of multiple MUC occupants or members.

XEP-0045 makes provision for MUC presence probes, which allows an entity to
probe for the presence information of a MUC occupant (or offline member).

See here: https://xmpp.org/extensions/xep-0045.html#bizrules-presence

This module creates the possibility to probe with a single IQ stanza the
presence information of multiple JIDs, instead of having to send out a presence
probe stanza per JID.

The IQ stanza needs to look as follows:

```
   <iq from="hag66@shakespeare.lit/pda"
      id="zb8q41f4"
      to="chat.shakespeare.lit"
      type="get">

      <query xmlns="http://jabber.org/protocol/muc#user">
         <item jid="hecate@shakespeare.lit"/>
         <item jid="crone1@shakespeare.lit"/>
         <item jid="wiccarocks@shakespeare.lit"/>
         <item jid="hag66@shakespeare.lit"/>
      </query>
   </iq>
```



## Configuration

Under your MUC component, add `muc_batched_probe` to `modules_enabled`

```
   Component "conference.example.org" "muc"
      modules_enabled = {
               "muc_batched_probe";
      }
```


## Client Support

Converse.js has a plugin which supports this feature.

https://www.npmjs.com/package/@converse-plugins/muc-presence-probe
