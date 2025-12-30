---
labels:
- 'Stage-Beta'
- 'Type-Auth'
summary: 'Two-factor authentication using Yubikeys'
...

Introduction
============

A [YubiKey](http://www.yubico.com/yubikey) is a small USB
one-time-password (OTP) generator.

The idea behind one-time-passwords is that they can, well, only be used
once. After authenticating with an OTP the only way to log in again is
to calculate another one and use that. The only (practical) way to
generate this is by inserting the (correct) Yubikey and pressing its
button. Acting as a USB keyboard it then "types" the OTP into the
password prompt of your XMPP client.

Details
=======

This self-contained module handles all the authentication of Yubikeys,
it does not for example depend on the Yubico authentication service, or
on any external system service such as PAM.

When this module is enabled, only PLAIN authentication is enabled on the
server (because Prosody needs to receive the full password from the
client to decode it, not a hash), so connection encryption will
automatically be enforced by Prosody.

Even if the password is intercepted it is of little use to the attacker
as it expires as soon as it is used. Additionally the data stored in
Prosody's DB is not enough to authenticate as the user if stolen by the
attacker.

When this module is in use each user can either use normal password
authentication, or instead have their account associated with a
Yubikey - at which point only the key will work.

Installation
============

Requires bitlib for Lua, and yubikey-lua from
http://code.matthewwild.co.uk/yubikey-lua . When properly installed, the
command `lua -lbit -lyubikey` should give you a Lua prompt with no
errors.

Configuration
=============

Associating keys
----------------

Each Yubikey is configured with several pieces of information that
Prosody needs to know. This information is shown in the Yubikey
personalization tool (the *yubikey-personalization* package in
Debian/Ubuntu).

To associate a Yubikey with a user, run the following prosodyctl
command:

        prosodyctl mod_auth_internal_yubikey associate user@example.com

This will run you through a series of questions about the information
Prosody requires about the key configuration.

**NOTE:** All keys used with the server (rather, with a given host) must
all have a "public ID" (uid) of the same length. This length must be set
in the Prosody config with the 'yubikey\_prefix\_length' option.

Instead of entering the information interactively it is also possible to
specify each option on the command-line (useful for automation)
via --option="value". The valid options are:

  password   The user's password (may be blank)
  ---------- --------------------------------------------------------------------------------------------
  fixed      The public ID that the Yubikey prefixes to the OTP
  uid        The private ID that the Yubikey encrypts in the OTP
  key        The AES key that the Yubikey uses (may be blank if a global shared key is used, see below)

If a password is configured for the user (recommended) they must enter
this into the password box immediately before the OTP. This password
doesn't have to be incredibly long or secure, but it prevents the
Yubikey being used for authentication if it is stolen and the password
isn't known.

Configuring Prosody
-------------------

To use this module for authentication, set in the config:

        authentication = "internal_yubikey"

Module-specific options:

  yubikey\_prefix\_length   (**REQUIRED**) The length of the public ID prefixed to the OTPs
  ------------------------- -------------------------------------------------------------------------------------------------------------------
  yubikey\_global\_key      If all Yubikeys use the same AES key, you can specify it here. Pass --key="" to prosodyctl when associating keys.

If switching from a plaintext storage auth module then users without
Yubikeys associated with their account can continue to use their
existing passwords as normal, otherwise password resets are required.

Compatibility
=============

  ----- -------
  0.8   Works
  ----- -------
