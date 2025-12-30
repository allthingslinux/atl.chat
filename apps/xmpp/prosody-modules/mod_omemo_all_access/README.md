---
labels:
- 'Stage-Alpha'
summary: 'Disable access control for all OMEMO related PEP nodes'
---

Introduction
============

Traditionally OMEMO encrypted messages could only be exchanged after gaining mutual presence subscription due to the OMEMO key material being stored in PEP.

XEP-0060 defines a method of changing the access model of a PEP node from `presence` to `open`. However Prosody does not yet support access models on PEP nodes.

This module disables access control for all OMEMO PEP nodes (=all nodes in the namespace of `eu.siacs.conversations.axolotl.*`), giving everyone access to the OMEMO key material and allowing them to start OMEMO sessions with users on this server.

Disco feature
=============

This modules annouces a disco feature on the account to allow external tools such as the [Compliance Tester](https://conversations.im/compliance/) to check if this module has been installed.


Compatibility
=============

  ----- -----------------------------------------------------------------------------
  trunk Not needed, mod\_pep provides this feature already
  0.11  Not needed, mod\_pep provides this feature already
  0.10  Works
  ----- -----------------------------------------------------------------------------
