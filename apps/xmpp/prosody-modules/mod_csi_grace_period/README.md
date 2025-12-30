---
summary: Don't wake inactive clients, if annother is in use.
labels:
- 'Stage-Beta'
...

# Introduction

This module helps reduces power usage of inactive mobile clients while
another client is actively used. E.g. in the case of chatting on a
desktop computer, instantly pushing messages to a phone in someones
pocket is not the best use of radio time.

# Compatibility

Works with [mod_csi_simple][doc:modules:mod_csi_simple] which is
included with Prosody.

  ------- ------------------------
  trunk   Works as of 2025-06-13
  13      Works
  0.12    Works
  ------- ------------------------
