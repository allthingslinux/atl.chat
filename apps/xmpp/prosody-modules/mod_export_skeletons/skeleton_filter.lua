#!/usr/bin/env lua

package.path = package.path:gsub("([^;]*)(?[^;]*)", "%1prosody/%2;%1%2");
package.cpath = package.cpath:gsub("([^;]*)(?[^;]*)", "%1prosody/%2;%1%2");

local t_insert = table.insert;
local t_sort = table.sort;

local jid = require "util.jid";
local st = require "util.stanza";

local xs = require "util.xmppstream";

local function skeleton(s)
	local o = st.stanza(s.name, { xmlns = s.attr.xmlns });

	local children = {};
	for _, child in ipairs(s.tags) do t_insert(children, skeleton(child)) end
	t_sort(children, function(a, b)
		if a.attr.xmlns == b.attr.xmlns then return a.name < b.name; end
		return (a.attr.xmlns or "") < (b.attr.xmlns or "");
	end);
	for _, child in ipairs(children) do o:add_direct_child(child); end
	return o;
end

local function classify_jid(s)
	if not s then return "" end
	local u, h, r = jid.split(s);
	if r then
		return "full"
	elseif u then
		return "bare"
	elseif h then
		return "host"
	else
		return "invalid"
	end
end

local stream_session = { notopen = true };
local stream_callbacks = { stream_ns = "jabber:client"; default_ns = "jabber:client" };
function stream_callbacks:handlestanza(item)
	local clean = skeleton(item);

	-- Normalize top level attributes
	clean.attr.type = item.attr.type;
	if clean.attr.type == nil and clean.name == "message" then clean.attr.type = "normal"; end
	clean.attr.id = string.rep("x", math.floor(math.log(1 + #(item.attr.id or ""), 2)));
	clean.attr.from = classify_jid(item.attr.from);
	clean.attr.to = classify_jid(item.attr.to);
	print(clean);
end
local stream = xs.new(stream_session, stream_callbacks);
assert(stream:feed(st.stanza("stream", { xmlns = "jabber:client" }):top_tag()));
stream_session.notopen = nil;

local data = io.read(4096);
while data do
	stream:feed(data);
	data = io.read(4096);
end

assert(stream:feed("</stream>"));
