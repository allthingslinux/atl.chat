---
summary: Implement XEP-0215
labels:
- 'Stage-Obsolete'
...

::: {.alert .alert-warning}
A similar module is already included in prosody since 0.12, see [mod_turn_external][doc:modules:mod_turn_external] making this module obsolete.
:::

# Introduction

[XEP-0215] implementation for [time-limited TURN
credentials](https://tools.ietf.org/html/draft-uberti-behave-turn-rest-00).

# Configuration

  Option                    Type     Default
  ------------------------- -------- ------------
  turncredentials\_secret   string   *required*
  turncredentials\_host     string   *required*
  turncredentials\_port     number   `3478`
  turncredentials\_ttl      number   `86400`

# Compatible TURN / STUN servers.

-   [coturn](https://github.com/coturn/coturn) - [setup guide][doc:coturn]
-   [restund](http://www.creytiv.com/restund.html)
-   [eturnal](https://eturnal.net/)

# Compatibility

Incompatible with [mod_extdisco](https://modules.prosody.im/mod_extdisco.html)

  ------- --------------
  0.12     Works
  0.11     Works
  ------- --------------
