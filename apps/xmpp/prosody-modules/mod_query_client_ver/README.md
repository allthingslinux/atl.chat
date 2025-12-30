# Introduction

This module sends a [version query][xep0092] to clients when they
connect, and logs the response, allowing statistics of client usage to
be recorded.

Note that since this is per connection, there will be a bias towards
mobile clients on bad connections.

## Example

    info    Running Running Swift version 4.0
