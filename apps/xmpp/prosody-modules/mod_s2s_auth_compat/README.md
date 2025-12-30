---
labels:
summary: Workaround for servers doing EXTERNAL without proper stream headers
...

Introduction
============

This module is a workaround for servers that try to do s2s
authentication with certificates and SASL EXTERNAL, but do not send
correct stream headers. Notably Openfire versions since 3.7 or 3.8.
