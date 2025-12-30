
local st = require "util.stanza";
local jid_bare = require "util.jid".bare;

-- advertise disco features
module:add_feature("urn:xmpp:sift:1");

-- supported features
module:add_feature("urn:xmpp:sift:stanzas:iq");
module:add_feature("urn:xmpp:sift:stanzas:message");
module:add_feature("urn:xmpp:sift:stanzas:presence");
module:add_feature("urn:xmpp:sift:recipients:all");
module:add_feature("urn:xmpp:sift:senders:all");

-- allowed values of 'sender' and 'recipient' attributes
local senders = {
	["all"] = true;
	["local"] = true;
	["others"] = true;
	["remote"] = true;
	["self"] = true;
};
local recipients = {
	["all"] = true;
	["bare"] = true;
	["full"] = true;
};

-- this function converts a <message/>, <presence/> or <iq/> element in
-- the SIFT namespace into a hashtable, for easy lookup
local function to_hashtable(element)
	if element ~= nil then
		local hash = {};
		-- make sure the sender and recipient attributes has a valid value
		hash.sender = element.attr.sender or "all";
		if not senders[hash.sender] then return false; end -- bad value, returning false
		hash.recipient = element.attr.recipient or "all";
		if not recipients[hash.recipient] then return false; end -- bad value, returning false
		-- next we loop over all <allow/> elements
		for _, tag in ipairs(element) do
			if tag.name == "allow" and tag.attr.xmlns == "urn:xmpp:sift:1" then
				-- make sure the element is valid
				if not tag.attr.name or not tag.attr.ns then return false; end -- missing required attributes, returning false
				hash[tag.attr.ns.."|"..tag.attr.name] = true;
				hash.allowed = true; -- just a flag indicating we have some elements allowed
			end
		end
		return hash;
	end
end

local data = {}; -- table with all our data

-- handle SIFT set
module:hook("iq/self/urn:xmpp:sift:1:sift", function(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.type == "set" then
		local sifttag = stanza.tags[1]; -- <sift/>

		-- first, get the elements we are interested in
		local message = sifttag:get_child("message");
		local presence = sifttag:get_child("presence");
		local iq = sifttag:get_child("iq");

		-- for quick lookup, convert the elements into hashtables
		message = to_hashtable(message);
		presence = to_hashtable(presence);
		iq = to_hashtable(iq);

		-- make sure elements were valid
		if message == false or presence == false or iq == false then
			origin.send(st.error_reply(stanza, "modify", "bad-request"));
			return true;
		end

		local existing = data[origin.full_jid] or {}; -- get existing data, if any
		data[origin.full_jid] = { presence = presence, message = message, iq = iq }; -- store new data

		origin.send(st.reply(stanza)); -- send back IQ result

		if not existing.presence and not origin.presence and presence then
			-- TODO send probes
		end
		return true;
	end
end);

-- handle user disconnect
module:hook("resource-unbind", function(event)
	data[event.session.full_jid] = nil; -- discard data
end);

-- IQ handler
module:hook("iq/full", function(event)
	local origin, stanza = event.origin, event.stanza;
	local siftdata = data[stanza.attr.to];
	if stanza.attr.type == "get" or stanza.attr.type == "set" then
		if siftdata and siftdata.iq then -- we seem to have an IQ filter
			local tag = stanza.tags[1]; -- the IQ child
			if not siftdata.iq[(tag.attr.xmlns or "jabber:client").."|"..tag.name] then
				-- element not allowed; sending back generic error
				origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
				return true;
			end
		end
	end
end, 50);

-- Message to full JID handler
module:hook("message/full", function(event)
	local origin, stanza = event.origin, event.stanza;
	local siftdata = data[stanza.attr.to];
	if siftdata and siftdata.message then -- we seem to have an message filter
		local allowed = false;
		for _, childtag in ipairs(stanza.tags) do
			if siftdata.message[(childtag.attr.xmlns or "jabber:client").."|"..childtag.name] then
				allowed = true;
			end
		end
		if not allowed then
			-- element not allowed; sending back generic error
			origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
			-- FIXME maybe send to offline storage
			return true;
		end
	end
end, 50);

-- Message to bare JID handler
module:hook("message/bare", function(event)
	local origin, stanza = event.origin, event.stanza;
	local user = bare_sessions[jid_bare(stanza.attr.to)];
	local allowed = false;
	for _, session in pairs(user and user.sessions or {}) do
		local siftdata = data[session.full_jid];
		if siftdata and siftdata.message then -- we seem to have an message filter
			for _, childtag in ipairs(stanza.tags) do
				if siftdata.message[(childtag.attr.xmlns or "jabber:client").."|"..childtag.name] then
					allowed = true;
				end
			end
		else
			allowed = true;
		end
	end
	if user and not allowed then
		-- element not allowed; sending back generic error
		origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		-- FIXME maybe send to offline storage
		return true;
	end
end, 50);

-- Presence to full JID handler
module:hook("presence/full", function(event)
	local origin, stanza = event.origin, event.stanza;
	local siftdata = data[stanza.attr.to];
	if siftdata and siftdata.presence then -- we seem to have an presence filter
		local allowed = false;
		for _, childtag in ipairs(stanza.tags) do
			if siftdata.presence[(childtag.attr.xmlns or "jabber:client").."|"..childtag.name] then
				allowed = true;
			end
		end
		if not allowed then
			-- element not allowed; sending back generic error
			--origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
			return true;
		end
	end
end, 50);

-- Presence to bare JID handler
module:hook("presence/bare", function(event)
	local origin, stanza = event.origin, event.stanza;
	local user = bare_sessions[jid_bare(stanza.attr.to)];
	local allowed = false;
	for _, session in pairs(user and user.sessions or {}) do
		local siftdata = data[session.full_jid];
		if siftdata and siftdata.presence then -- we seem to have an presence filter
			for _, childtag in ipairs(stanza.tags) do
				if siftdata.presence[(childtag.attr.xmlns or "jabber:client").."|"..childtag.name] then
					allowed = true;
				end
			end
		else
			allowed = true;
		end
	end
	if user and not allowed then
		-- element not allowed; sending back generic error
		--origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		return true;
	end
end, 50);
