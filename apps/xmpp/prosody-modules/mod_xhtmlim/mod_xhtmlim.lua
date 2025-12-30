-- XEP-0071: XHTML-IM sanitizing

local assert = assert;

local st = require "util.stanza";
local url = require "socket.url";

local no_styles = module:get_option_boolean("strip_xhtml_style", true);

-- Tables from XEP-0071
local xeptables = [[
<body/>	class, id, title; style
<head/>	profile
<html/>	version
<title/>
<abbr/>	class, id, title; style
<acronym/>	class, id, title; style
<address/>	class, id, title; style
<blockquote/>	class, id, title; style; cite
<br/>	class, id, title; style
<cite/>	class, id, title; style
<code/>	class, id, title; style
<dfn/>	class, id, title; style
<div/>	class, id, title; style
<em/>	class, id, title; style
<h1/>	class, id, title; style
<h2/>	class, id, title; style
<h3/>	class, id, title; style
<h4/>	class, id, title; style
<h5/>	class, id, title; style
<h6/>	class, id, title; style
<kbd/>	class, id, title; style
<p/>	class, id, title; style
<pre/>	class, id, title; style
<q/>	class, id, title; style; cite
<samp/>	class, id, title; style
<span/>	class, id, title; style
<strong/>	class, id, title; style
<var/>	class, id, title; style
<a/>	class, id, title; style; accesskey, charset, href, hreflang, rel, rev, tabindex, type
<dl/>	class, id, title; style
<dt/>	class, id, title; style
<dd/>	class, id, title; style
<ol/>	class, id, title; style
<ul/>	class, id, title; style
<li/>	class, id, title; style
<img/>	class, id, title; style; alt, height, longdesc, src, width
]];

-- map of whitelisted tag names to set of allowed attributes
local tags = {}; -- { string : { string : boolean } }

for tag, attrs in xeptables:gmatch("<(%w+)/>([^\n]*)") do
	tags[tag] = { xmlns = true, ["xml:lang"] = true };
	for attr in attrs:gmatch("%w+") do
		tags[tag][attr] = true;
	end
	if no_styles then
		tags[tag]["style"] = nil;
	end
end

-- module:log("debug", "tags = %s;", require "util.serialization".serialize(tags));

-- TODO Decide if disallowed tags should be bounced or silently discarded.
-- XEP says "ignore" and replace tag with text content, but that would
-- need a different transform which can't use `maptags`.
if not module:get_option_boolean("bounce_invalid_xhtml", false) then
	assert = function (x) return x end
end

local function sanitize_xhtml(tag)
	-- module:log("debug", "sanitize_xhtml(<{%s}%s>)", tag.attr.xmlns, tag.name);
	if tag.attr.xmlns == "http://www.w3.org/1999/xhtml" then
		local allowed = assert(tags[tag.name], tag.name);
		if allowed then
			for attr, value in pairs(tag.attr) do
				if not allowed[attr] then
					-- module:log("debug", "Removing disallowed attribute %q from <%s>", attr, tag.name);
					tag.attr[attr] = nil;
				elseif attr == "src" or attr == "href" then
					local urlattr = url.parse(value);
					local scheme = urlattr and urlattr.scheme;
					if scheme ~= "http" and scheme ~= "https" and scheme ~= "mailto" and scheme ~= "xmpp" and scheme ~= "cid" then
						tag.attr[attr] = "https://url.was.invalid/";
					end
				end
			end
		else
			tag.name = "span"
			tag.attr = { xmlns = "http://www.w3.org/1999/xhtml" }
		end
		-- Check child tags
		tag:maptags(sanitize_xhtml);
		-- This tag is clean!
		return tag;
	end
	-- Not xhtml, probably best to discard it
	return nil;
end

-- Check for xhtml-im, sanitize if exists
local function message_handler(event)
	local stanza = event.stanza;
	if stanza:get_child("html", "http://jabber.org/protocol/xhtml-im") then
		stanza = st.clone(stanza);
		if pcall(function() -- try
			stanza:get_child("html", "http://jabber.org/protocol/xhtml-im"):maptags(sanitize_xhtml);
		end) then
			event.stanza = stanza;
		else -- catch
			if stanza.attr.type ~= "error" then
				event.origin.send(st.error_reply(stanza, "modify", "not-acceptable", "Stanza contained illegal XHTML-IM tag"));
			end
			return true;
		end
	end
end

-- Stanzas received from clients
module:hook("pre-message/bare", message_handler, 71);
module:hook("pre-message/full", message_handler, 71);
module:hook("pre-message/host", message_handler, 71);

-- Stanzas about to be delivered to clients
module:hook("message/bare", message_handler, 71);
module:hook("message/full", message_handler, 71);
