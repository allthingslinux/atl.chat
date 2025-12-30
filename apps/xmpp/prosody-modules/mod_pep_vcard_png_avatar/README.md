Introduction
============

Conversations (an XMPP client for Android) is publishing PEP avatars in the webp file format. However Pidgin and other XMPP desktop clients can only show vcard avatars, that are in the PNG file format. This module is the [mod_pep_vcard_avatar](https://modules.prosody.im/mod_pep_vcard_avatar.html) module extended to also change the avatar file format to PNG.

This module needs `dwebp` from `webp` package as an additional dependency.

Configuration
=============

Enable the module as any other:

    modules_enabled = {
      "mod_pep_vcard_png_avatar";
    }

You MUSTN'T load mod\_pep\_vcard\_avatar if this module is loaded.

Compatibility
=============

  ----- -------------
  trunk Works
  0.10  Should work
  0.9   Should work
  ----- -------------


