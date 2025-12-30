XEP-0357 Business rules implementation in prosody
=================================================

Daniel proposed some business rules for push notifications [^1]
This document describes the various implementation details involved in
implementing these rules in prosody.

Point 3 of Daniel's mail is implemented by setting two attributes
on the session table when a client enables push for a session:

- push_identifier: this is push_jid .. "<" .. (push_node or "")
  (this value is used as key of the user_push_services table)
- push_settings: this is a reference to the user_push_services[push_identifier]


Point 4 of Daniel's mail contains the actual business rules
-----------------------------------------------------------

**a)**  
CSI is honoured in this scenario because messages hold back by csi don't even
reach the smacks module. mod_smacks has 3 events:

- smacks-ack-delayed: This event is triggered when the client doesn't respond to
   a smacks <r> in a configurable amount of time (default: 60 seconds).
   Mod_cloud_notify reacts on this event and sends out push notifications
   to the push service registered for this session in point 3 (see above) for all
   stanzas in the smacks queue (the queue is given in the event).

- smacks-hibernation-start: This event is triggered when the smacks session
  is put in hibernation state. The event contains the smacks queue, too.
  Mod_cloud_notify uses this event to send push notifications for all
  stanzas not already pushed and installs a "stanzas/out"-filter to
  react on new stanzas coming in while the session is hibernated.
  The push endpoint of the hibernated session is then also notified
  for every new stanza.
- smacks-hibernation-end: This event is triggered, when the smacks hibernation
  is stopped (the smacks session is resumed) and used by Mod_cloud_notify
  to remove the "stanzas/out"-filter.

**b)**  
Mod_mam already provides an event named "archive-message-added" which is
triggered every time a stanza is saved into the mam store.
Mod_cloud_notify uses this event to send out push notifications to all
push services registered for the user the stanza is for, but *only*
to those push services not having an active (or smacks hibernated) session.
Only those stanzas are considered that contain the "for_user" event attribute
of mod_mam as the user part of the jid.
This is done to ensure that mam archiving rules are honoured.

**c)**  
The "message/offline/handle"-hook is used to send out push notifications to all
registered push services belonging to the user the offline stanza is for.
This was already implemented in the first version of mod_cloud_notify.


Some statements to related technologies/XEPs/modules
----------------------------------------------------

- carbons: These are handled as usual and don't interfere with these business rules
  at all. Smacks events are generated for carbon copies if needed and mod_cloud_notify
  uses them to wake up the device in question if needed, as normal stanzas would do, too.

- csi: Csi is honoured also, because every stanza hold back by mod_pump or other csi
  modules is never seen by the smacks module, thus not added to its queue and not
  forwarded to mod_cloud_notify by the smacks events.
  Mod_cloud_notify does only notify devices having no active or smacks hibernated session
  of new mam stored stanzas, so stanzas filtered by csi don't get to mod_cloud_notify
  this way neither.

- other technologies: There shouldn't be any issues with other technologies imho.

[^1]: https://mail.jabber.org/pipermail/standards/2016-February/030925.html
