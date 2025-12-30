---
summary: XMPP Compliance Suites self-test
labels:
- Stage-Beta
rockspec:
  dependencies:
  - mod_compliance_2023
...

# Introduction

This meta-module will always `require` (and therefore auto-load) the lastest compliance tester we have in the community modules.
Currently this is [mod_compliance_2023]. See the linked module for further details.

If you do not use the *Prosody plugin installer* this module will likely have limited value to you.
You can also just install the current compliance tester manually.

# Configuration

Just load this module as any other module and it will automatically install and load [mod_compliance_2023] if you use the *Prosody plugin installer*. 

# Compatibility

  Prosody-Version Status
  --------------- ----------------------
  trunk           Works as of 2024-12-22
  0.12            Works
