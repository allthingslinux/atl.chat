---
description: CSI module to save battery on mobile devices
---

Please use this module instead of [mod_csi_pump] if you want timestamping,
properly handled carbon copies, support for handling encrypted messages and
correctly handled smacks events.

If smacks is used on the same server this needs at least version [f70c02c14161]
of the smacks module! There could be message reordering on resume otherwise.

Stanzas are queued in a buffer until either an "important" stanza is
encountered or the buffer becomes full. Then all queued stanzas are sent
at the same time. This way, nothing is lost or reordered while still
allowing for power usage savings by not requiring mobile clients to
bring up their radio for unimportant stanzas.

`IQ` stanzas, and `message` stanzas containing a body or being encrypted,
chat markers (see [XEP-0333]) and all *nonzas* are considered important.
If the config option `csi_battery_saver_filter_muc` is set to true,
groupchat messages must set a subject or have the user's username or nickname
mentioned in the messages (or be encrypted) to count as "important".
**Warning:** you should only set this to true if your users can live with
groupchat messages being delayed several minutes!
On the other hand if this option is set to false (*default*),
all groupchat messages having a body or being encrypted are considered "important".
In this case [mod_csi_muc_priorities] can be used to let user configure per groupchat
which of them are important for them (e.g. all messages having a body are important)
and which are not (e.g. only mentions and own messages are important).
If users don't change their settings, [mod_csi_muc_priorities] handles all groupchats
as important (see its docs for more information).
`Presence` stanzas are always considered not "important".

All buffered stanzas that allow timestamping are properly stamped to
reflect their original send time, see [XEP-0203].

Use with other CSI plugins such as [mod_throttle_presence],
[mod_filter_chatstates], [mod_csi_simple] or [mod_csi_pump] is **not** supported.
Usage of [mod_csi_muc_priorities] is allowed (see configuration).

*Hint:* [mod_csi_muc_priorities] needs [mod_track_muc_joins] to function properly.

Configuration
=============

  Option                                  Default           Description
  ----------------------------------      ---------- -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  `csi_battery_saver_filter_muc`          false      Controls whether all MUC messages having a body should be considered as important as long as [mod_csi_muc_priorities] doesn't configure them to be **not** important (false) or only such containing the user's room nic (true). **WARNING:** you should only set this to true if your users can live with muc messages being delayed several minutes.
  `csi_battery_saver_queue_size`          256        Size of the stanza buffer used for the queue (if the queue is full a flush will be forced)


[f70c02c14161]: //hg.prosody.im/prosody-modules/raw-file/f70c02c14161/mod_smacks/mod_smacks.lua