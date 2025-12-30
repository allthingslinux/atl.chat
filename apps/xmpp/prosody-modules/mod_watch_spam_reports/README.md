---
labels:
- 'Stage-Beta'
rockspec:
  dependencies:
  - mod_spam_reporting
summary: 'Notify admins about incoming XEP-0377 spam reports'
---

This module sends a message to the server admins for incoming
[XEP-0377][1] spam reports. It depends on [mod\_spam\_reporting][2] 
and doesn't require any configuration.

Compatibility
=============

  ----- -----------
  trunk Works
  0.11  Works
  ----- -----------


[1]:https://xmpp.org/extensions/xep-0377.html
[2]:https://modules.prosody.im/mod_spam_reporting.html
