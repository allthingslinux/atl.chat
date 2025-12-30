Introduction
============

This module was written to encourage usage of End-to-end encryption for chat and MUC messages. It can be configured to warn the sender after every plaintext/unencrypted message or to block all plaintext/unencrypted messages. It also supports MUC and JID whitelisting, so administrators can for example whitelist public support MUCs ;-)

Configuration
=============

Enable the module as any other:

    modules_enabled = {
      "e2e_policy";
    }

You can then set some options to configure your desired policy:

  Option                                 Default        Description
  ------------------------------------   ------------   -------------------------------------------------------------------------------------------------------------------------------------------------
  e2e\_policy\_chat                      `"optional"`   Policy for chat messages. Possible values: `"none"`, `"optional"` and `"required"`.
  e2e\_policy\_muc                       `"optional"`   Policy for MUC messages. Possible values: `"none"`, `"optional"` and `"required"`.
  e2e\_policy\_whitelist                 `{ }`          Make this module ignore messages sent to and from this JIDs or MUCs.
  e2e\_policy\_message\_optional\_chat   `""`           Set a custom warning message for chat messages.
  e2e\_policy\_message\_required\_chat   `""`           Set a custom error message for chat messages.
  e2e\_policy\_message\_optional\_muc    `""`           Set a custom warning message for MUC messages.
  e2e\_policy\_message\_required\_muc    `""`           Set a custom error message for MUC messages.

Some examples:

    e2e_policy_chat = "optional"
    e2e_policy_muc = "optional"
    e2e_policy_whitelist = { "admin@example.com", "prosody@conference.prosody.im" }
    e2e_policy_message_optional_chat = "For security reasons, OMEMO, OTR or PGP encryption is STRONGLY recommended for conversations on this server."
    e2e_policy_message_required_chat = "For security reasons, OMEMO, OTR or PGP encryption is required for conversations on this server."
    e2e_policy_message_optional_muc = "For security reasons, OMEMO, OTR or PGP encryption is STRONGLY recommended for MUC on this server."
    e2e_policy_message_required_muc = "For security reasons, OMEMO, OTR or PGP encryption is required for MUC on this server."

Compatibility
=============

  ----- -------------
  trunk Works
  0.10  Should work
  0.9   Should work
  ----- -------------


