---
labels:
- 'Stage-Beta'
summary: Enforces HTTP Basic authentication across all HTTP endpoints served by Prosody
...

# mod_http_authentication

This module enforces HTTP Basic authentication across all HTTP endpoints served by Prosody.

## Configuration

  Name                               Default                           Description
  ---------------------------------- --------------------------------- --------------------------------------------------------------------------------------------------------------------------------------
  http\_credentials                  "minddistrict:secretpassword"     The credentials that HTTP clients must provide to access the HTTP interface. Should be a string with the syntax "username:password".
  unauthenticated\_http\_endpoints   { "/http-bind", "/http-bind/" }   A list of paths that should be excluded from authentication.

## Usage

This is a global module, so should be added to the global `modules_enabled` option in your config file. It applies to all HTTP virtual hosts.

## Compatibility

The module use a new API in Prosody 0.10 and will not work with older
versions.

## Details

By Kim Alvefur \<zash@zash.se\>
