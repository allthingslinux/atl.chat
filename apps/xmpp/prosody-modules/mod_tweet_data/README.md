# mod_tweet_data

This module adds [Open Graph Protocol](https://ogp.me) metadata to Twitter.com tweet URLs sent inside a MUC.

It's similar to [mod_ogp](https://modules.prosody.im/mod_ogp.html) but is adapted specifically to Twitter.com, which doesn't support the [Open Graph Protocol](https://ogp.me).

When a user sends a tweet URL in a MUC (where the message has its `id` equal to its `origin-id`), this module calls that URL to get the tweet data.
If it finds any, it sends a [XEP-0422 fastening](https://xmpp.org/extensions/xep-0422.html) applied to the original message that looks as follows (note, I haven't used real data here):

```xml
    <message xmlns="jabber:client" to="user@chat.example.org/resource" from="chatroom@muc.example.org" type="groupchat">
        <apply-to xmlns="urn:xmpp:fasten:0" id="82dbc94c-c18a-4e51-a0d5-9fd3a7bfd267">
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:article:author" content="TwitterCritter" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:article:published_time" content="2021-06-22T06:44:20.000Z" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:description" content="I'm in ur twitterz" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:image" content="https://pbs.twimg.com/profile_images/984325764849045505/Ty3F93Ln_normal.jpg" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:title" content="TwitterCritter" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:type" content="tweet" />
            <meta xmlns="http://www.w3.org/1999/xhtml" property="og:url" content="https://twitter.com/TwitterCritter/status/1407227938391707648" />
        </apply-to>
        <stanza-id xmlns="urn:xmpp:sid:0" by="chatroom@muc.example.org" id="90e8818d-390a-4c69-a2d8-0fd463fb3366"/>
    </message>
```

Configuration
-------------

You'll need to provide a Twitter APIv2 bearer token.

```lua
Component "muc.example.org" "muc"
  modules_enabled = { "tweet_data" }
  twitter_apiv2_bearer_token  = { "some-very-long-string" }
```
