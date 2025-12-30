---
labels:
- 'Stage-Deprecated'
summary: 'Implementation of XEP-0138'
...

::: {.alert .alert-warning}
**NOTE:** XMPP compression has unresolved [security concerns](https://mail.jabber.org/pipermail/standards/2014-October/029215.html),
and this module has been removed from Prosody and renamed.
:::

While the bandwidth usage of XMPP isn't that much, compressing the data
sent to/from your server can give significant benefits to those on slow
connections, such as dial-up or mobile networks. Prosody supports
compression for client-to-server (if your client supports it) and
server-to-server streams using the mod\_compression plugin.

# Details

mod\_compression implements [XEP-0138], and supports the zlib compression
algorithm.

## Dependencies

The XMPP protocol specifies that all clients and servers supporting
compression must support the "zlib" compression method, and this is what
Prosody uses. However you will need to install zlib support for Lua on
your system. There are different ways of doing this depending on your
system. If in doubt whether it is installed correctly, the command
`lua -lzlib` in a console should open a Lua prompt with no errors.

Debian/Ubuntu
:   `apt-get install lua-zlib`

LuaRocks
:   `luarocks install lua-zlib`

Source
:   <https://github.com/brimworks/lua-zlib>

# Usage

``` lua
modules_enabled = {
    -- Other modules
    "compression_unsafe"; -- Enable mod_compression_unsafe
}
```

## Configuration

The compression level can be set using the `compression_level` option
which can be a number from 1 to 9. Higher compression levels will use
more resources but less bandwidth.

## Example

``` lua
modules_enabled = {
    -- Other modules
    "compression_unsafe"; -- Enable mod_compression_unsafe
}
 
compression_level = 5
```
