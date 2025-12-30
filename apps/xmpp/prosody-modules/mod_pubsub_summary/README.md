Module that generates a nicer text version of Atom feeds, meant for
use with [mod_pubsub_feeds] and [mod_pubsub_text_interface].

It extracts title, content and links from entries, does a crude
conversion of HTML to [XEP-0393: Message Styling] and formats a text
version like this:

> \***Example Post Title**\*
>
> Lorem ipsum dolor sit amet.
>
> https://blog.example.com/example-post


