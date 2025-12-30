---
labels:
- 'Statistics'
...

Exposes server information over Pub/Sub per [XEP-0485: PubSub Server Information](https://xmpp.org/extensions/xep-0485.html).

The module announces support (used to 'opt-in', per the XEP) and publishes the name of the local domain via a Pub/Sub node. The published data
will contain a 'remote-domain' element for inbound and outgoing s2s connections. These elements will be named only when the remote domain announces
support ('opts in') too.

**Known issues:**

- [Issue #1841](https://issues.prosody.im/1841): In Prosody 0.12, this module conflicts with mod_server_contact_info (both will run, but it may affect the ability of some implementations to read the server/contact information provided). To work around this issue, the [mod_server_contact_info](https://modules.prosody.im/mod_server_contact_info) community module can be used.

Installation
============

Enable this module in the global or a virtual host.

The default configuration requires the existence of a Pub/Sub component that uses the 'pubsub' subdomain of the host in which the module is enabled:

    Component "pubsub.example.org" "pubsub"

The module will create a node and publish data, using a JID that matches the XMPP domain name of the host. Ensure that this actor is an admin of the
Pub/Sub service:

    admins = { "example.org" }

Configuration
=============

The Pub/Sub service on which data is published, by default, is a component addressed as the `pubsub` subdomain of the domain of the virtual host that
the module is loaded under. To change this, apply this configuration setting:

    pubsub_serverinfo_service = "anotherpubsub.example.org"

The Pub/Sub node on which data is published is, by default, a leaf-node named `serverinfo`. To change this, apply this configuration setting:

    pubsub_serverinfo_node = "foobar"

To prevent a surplus of event notifications, this module will only publish new data after a certain period of time has expired. The default duration
is 300 seconds (5 minutes). To change this simply put in the config:

    pubsub_serverinfo_publication_interval = 180 -- or any other number of seconds

To detect if remote domains allow their domain name to be included in the data that this module publishes, this module will perform a service
discovery request to each remote domain. To prevent a continuous flood of disco/info requests, the response to these requests is cached. By default,
a cached value will remain in cache for one hour. This duration can be modified by adding this configuration option:

    pubsub_serverinfo_cache_ttl = 1800 -- or any other number of seconds

To include the count of active (within the past 30 days) users:

    pubsub_serverinfo_publish_user_count = true

Enabling this option will automatically load mod_measure_active_users.

Compatibility
=============

Incompatible with 0.11 or lower.

Known Issues / TODOs
====================

The reported data does not contain the optional 'connection' child elements. These can be used to describe the direction of a connection.

More generic server information (eg: user counts, software version) should be included in the data that is published.
