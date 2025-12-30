---
summary: XMPP Compliance Suites 2023 self-test
labels:
- Stage-Beta
rockspec:
  dependencies:
  - mod_cloud_notify

...

Compare the list of enabled modules with
[XEP-0479: XMPP Compliance Suites 2023] and produce basic report to the
Prosody log file.

If installed with the Prosody plugin installer then all modules needed for a green checkmark should be included. (With prosody 0.12 only [mod_cloud_notify] is not included with prosody and we need the community module) 

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2024-12-21
  0.12            Works
