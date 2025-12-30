---
rockspec:
  build:
    copy_directories:
    - templates
  dependencies:
  - mod_http_libjs
summary: JSXC demo
---

Try out JSXC easily by serving it from Prosodys built-in HTTP server.

Uses [mod_http_libjs] to serve jQuery, on Debian you can `apt install
libjs-jquery`.

# Configuration

mod_jsxc can be set up to either use resources from a separate HTTP
server or serve resources from Prosody's built-in HTTP server.

## Using CDN

`jsxc_cdn`
:   String. Base URL where JSXC resources are served from. Defaults to
    empty string.

`jsxc_version`
:   String. Concatenated with the CDN URL. Defaults to empty string.

## Local resources

Download a JSXC release archive and unpack it somewhere on your server.

`jsxc_resources`
:   String. Path to the `dist` directory containing JSXC resources on
the local file system. Disabled by default.

## Other options

`jquery_url`
:   String. URL or relative path to jQuery. Defaults to
    `"/share/jquery/jquery.min.js"` which will work with
    [mod_http_libjs].
