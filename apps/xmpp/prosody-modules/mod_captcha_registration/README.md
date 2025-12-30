---
labels:
- 'Stage-Beta'
summary: provides captcha protection for registration form
...

Introduction
============

Prosody-captcha is a little modification of prosody's
"mod\_register.lua" module that provides captcha protection for
registration form.

Installation
============

First of all you should build and install lua bindings for libgd —
[lua-gd](https://github.com/ittner/lua-gd/).

Then clone repsository lua-captcha:

    $ git clone https://github.com/mrDoctorWho/lua-captcha

install it:

    $ make install

Configuration
=============

After that you would configure prosody. This module requires from you 4
fields, you should add this into your VirtualHost entry.

    captcha_config = {
            dir = "/tmp"; -- Directory used to storage captcha images. Please make sure prosody user allowed to write there.
            timeout = 60; -- Timeout when captcha will expire
            web_path = "challenge"; -- Web path used to separate main prosody site from itself modules.
            font = "/usr/lib/prosody/FiraSans-Regular.ttf" -- Font used for captcha text
    }

You can run script "install.lua" to install this or instead of that
while prosody developers didn't accepted "dataforms" changes you should
replace standard prosody "dataforms.lua" located in ubuntu in
/usr/lib/prosody/util by another one from this repository. You should do
the same thing with "mod\_register.lua" located in ubuntu in
/usr/lib/prosody/modules.

After this all you can try to register on your server and see the
captcha.

TODO
====

-   Maybe use recaptcha instead of libgd.
