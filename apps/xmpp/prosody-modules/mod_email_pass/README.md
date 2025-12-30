---
labels:
- 'Stage-Beta'
...

Introduction
============

This module aims to help in the procedure of user password restoration.
To start the restoration, the user must go to an URL provided by this
module, fill the JID and email and submit the request.

The module will generate a token valid for 24h and send an email with a
specially crafted url to the vCard email address. If the user goes to
this url, will be able to change his password.

Usage
=====

Simply add "email\_pass" to your modules\_enabled list and copy files
"**mod\_email\_pass.lua**" and "**vcard.lib.lua**" to prosody modules
folder. This module need to that **https\_host** or **http\_host** must
be configured. This parameter is necessary to construct the URL that has
been sended to the user.

This module only send emails to the vCard user email address, then the
user must set this address in order to be capable of do the restoration.

Configuration
=============

  --------------- ------------------------------------------------------------
  smtp\_server    The Host/ip of your SMTP server
  smtp\_port      Port used by your SMTP server. Default 25
  smtp\_ssl       Use of SMTP SSL legacy (No STARTTLS)
  smtp\_user      Username used to do SMTP auth
  smtp\_pass      Password used to do SMTP auth
  smtp\_address   EMail address that will be apears as From in mails
  msg\_subject    Subject used for messages/mails
  msg\_body       Message send when password has been changed
  url\_path       Path where the module will be visible. Default /resetpass/
  --------------- ------------------------------------------------------------

Compatibility
=============

  ----- -------
  0.9   Works
  ----- -------
