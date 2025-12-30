---
labels:
- 'Stage-Alpha'
summary: 'Client-side certificate management for Prosody'
...

Introduction
============

[XEP-0257](http://xmpp.org/extensions/xep-0257.html) specifies a
protocol for clients to store and manage client side certificates. When
a client presents a stored client side certificate during the TLS
handshake, it can log in without supplying a password (using SASL
EXTERNAL). This makes it possible to have multiple devices accessing an
account, without any of them needing to know the password, and makes it
easier to revoke access for a single device.

Details
=======

Each user can add their own certificates. These do not need to be signed
by a trusted CA, yet they do need to be valid at the time of logging in
and they should include an subjectAltName with otherName
"id-on-xmppAddr" with the JID of the user.

Generating your certificate
---------------------------

1.  To generate your own certificate with a "id-on-xmppAddr" attribute
    using the command line `openssl` tool, first create a file called
    `client.cnf` with contents:

        [req] prompt = no
        x509_extensions = v3_extensions
        req_extensions = v3_extensions
        distinguished_name = distinguished_name

        [v3_extensions]
        extendedKeyUsage = clientAuth
        keyUsage = digitalSignature,keyEncipherment
        basicConstraints = CA:FALSE
        subjectAltName = @subject_alternative_name

        [subject_alternative_name]
        otherName.0 =
        1.3.6.1.5.5.7.8.5;FORMAT:UTF8,UTF8:hamlet@shakespeare.lit

        [distinguished_name]
        commonName = Your Name
        emailAddress = hamlet@shakespeare.lit

2.  Replace the values for `otherName.0` and `commonName` and
    `emailAddress` with your own values. The JID in `otherName.0` can
    either be a full JID or a bare JID, in the former case, the client
    can only use the resource specified in the resource. There are many
    other fields you can add, however, for SASL EXTERNAL, they will have
    no meaning. You can add more JIDs as `otherName.1`, `otherName.2`,
    etc.
3.  Create a private key (as an example, a 4096 bits RSA key):

        openssl genrsa -out client.key 4096

4.  Create the certificate request:

        openssl req -key client.key -new -out client.req -config client.cnf -extensions v3_extensions

5.  Sign it yourself:

        openssl x509 -req -days 365 -in client.req -signkey client.key -out client.crt -extfile client.cnf -extensions v3_extensions

The 365 means the certificate will be valid for a year starting now.

The `client.key` **must** be kept secret, and is only needed by clients
connecting using this certificate. The `client.crt` file contains the
certificate that should be sent to the server using XEP-0257, and is
also needed by clients connecting to the server. The `client.req` file
is not needed anymore.

Configuration
=============

(None yet)

Compatibility
=============

  ----- -----------------------------
  0.9   Works
  0.8   Untested. Probably doesn't.
  ----- -----------------------------

Clients
=======

(None?)

TODO
====

Possible options to add to the configuration:

-   Require certificates to be signed by a trusted CA.
-   Do not require a id-on-xmppAddr
-   Remove expired certs after a certain time
-   Limit the number of certificates per user
