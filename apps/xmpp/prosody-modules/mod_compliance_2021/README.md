---
summary: XMPP Compliance Suites 2021 self-test
rockspec:
  dependencies:
  - mod_cloud_notify
  - mod_smacks
  - mod_bookmarks
...

Compare the list of enabled modules with
[XEP-0443: XMPP Compliance Suites 2021] and produce basic report to the
Prosody log file.

If installed with the Prosody plugin installer (trunk/0.12+ required)
then all modules needed for a green checkmark should be included.
