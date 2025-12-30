---
labels:
- 'Stage-Alpha'
summary: XMPP to SMS gateway using the Clickatell API
...

Introduction
============

This module provides and SMS gateway component which uses the Clickatell
HTTP API to deliver text messages. See clickatell.com for details on
their services. Note that at present, this is entirely one way: replies
will either go nowhere or as sms to the source number you specify.

Configuration
=============

In prosody.cfg.lua:

    Component "sms.example.com" "sms_clickatell"
        sms_message_prefix = "some text"

The sms\_message\_prefix is a piece of text you want prefixing to all
messages sent through the gateway. For example, I use the prefix
"`[Via XMPP]` " to indicate to recipients that I've sent the message via
the internet rather than the mobile network. Since my primary use case
for this component is to be able to send messages to people only
reachable via mobile when I myself only have internet access and no
mobile reception, this option allows me to give a hint to my recipients
that any reply they send may not reach me in a timely manner.

Usage
=====

Once you've installed and configured, you should be able to use service
discovery in your XMPP client to find the component service. Once found,
you need to register with the service, supplying your Clickatell
username, password, API ID, and a source number for your text messages.

The source number is the mobile number you want messages to 'originate'
from i.e. where your recipients see messages coming from. The number
should be in international format without leading plus sign, or you can
use some other format if clickatell supports it.

To send text messages to a target number, you need to add a contact in
the form of `[number]@sms.example.com`, where `[number]` is the mobile
number of the recipient, in international format without leading plus
sign, and sms.example.com is the name for the component you configured
above. For example:

447999000001@sms.yourdomain.com

You should then be able to send messages to this contact which get sent
as text messages to the number by the component.

Compatibility
=============

  ----- -------
  0.7   Works
  ----- -------

Todo
====

-   Refactor to create a framework for multiple sms gateway back ends,
    and split Clickatell specific code in to its own back end
