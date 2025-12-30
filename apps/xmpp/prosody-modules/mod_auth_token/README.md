# mod_auth_token

This module enables Prosody to authenticate time-based one-time-pin (TOTP) HMAC tokens.

This is an alternative to "external authentication" which avoids the need to
make a blocking HTTP call to the external authentication service (usually a web application backend).

Instead, the application generates the HMAC token, which is then sent to
Prosody via the XMPP client and Prosody verifies the authenticity of this
token.

If the token is verified, then the user is authenticated.

## Luarocks dependencies

You'll need to install the following luarocks

  otp 0.1-5
  luatz 0.3-1

## How to generate the TOTP seed and shared signing secret

You'll need a shared OTP_SEED value for generating time-based one-time-pin
(TOTP) values and a shared private key for signing the HMAC token.

You can generate the OTP_SEED value with Python, like so:

    >>> import pyotp
    >>> pyotp.random_base32()
    u'XVGR73KMZH2M4XMY'

and the shared secret key as follows:

    >>> import pyotp
    >>> pyotp.random_base32(length=32)
    u'JYXEX4IQOEYFYQ2S3MC5P4ZT4SDHYEA7'

## Configuration

Firest you need to enable the relevant modules to your Prosody.cfg file.

Look for the line `modules_enabled` (either globally or for your
particular `VirtualHost`), and then add the following to tokens:

    modules_enabled = {
        -- Token authentication
            "auth_token";
            "sasl_token";
    }

The previously generated token values also need to go into your Prosody.cfg file:

    authentication = "token";
    token_secret = "JYXEX4IQOEYFYQ2S3MC5P4ZT4SDHYEA7";
    otp_seed = "XVGR73KMZH2M4XMY";

The application that generates the tokens also needs access to these values.

For an example on how to generate a token, take a look at the `generate_token`
function in the `test_token_auth.lua` file inside this directory.

## Custom SASL auth

This module depends on a custom SASL auth mechanism called X-TOKEN and which
is provided by the file `mod_sasl_token.lua`.

Prosody doesn't automatically pick up this file, so you'll need to update your
configuration file's `plugin_paths` to link to this subdirectory (for example
to `/usr/lib/prosody-modules/mod_auth_token/`).

## Generating the token

Here's a Python snippet showing how you can generate the token that Prosody
will then verify:

    import base64
    import pyotp
    import random

    # Constants
    OTP_INTERVAL = 30
    OTP_DIGITS = 8

    jid = '{}@{}'.format(username, domain)

    otp_service = pyotp.TOTP(
        OTP_SEED,  # OTP_SEED must be set to the value generated previously (see above)
        digits=OTP_DIGITS,
        interval=OTP_INTERVAL
    )
    otp = otp_service.generate_otp(otp_service.timecode(datetime.utcnow()))

    nonce = ''.join([str(random.randint(0, 9)) for i in range(32)])
    string_to_sign = otp + nonce + jid
    signature = hmac.new(token_secret, string_to_sign, hashlib.sha256).digest()
    token = u"{} {}".format(otp+nonce, base64.b64encode(signature))

