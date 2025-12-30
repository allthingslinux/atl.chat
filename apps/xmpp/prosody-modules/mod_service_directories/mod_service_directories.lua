-- Prosody IM
-- Copyright (C) 2011 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

-- An implementation of [XEP-0309: Service Directories]

-- Imports and defines

local st = require "util.stanza";
local jid_split = require "util.jid".split;
local adhoc_new = module:require "adhoc".new;
local to_ascii = require "util.encodings".idna.to_ascii;
local nameprep = require "util.encodings".stringprep.nameprep;
local dataforms_new = require "util.dataforms".new;
local pairs, ipairs = pairs, ipairs;
local module = module;
local hosts = hosts;

local subscription_from = {};
local subscription_to = {};
local contact_features = {};
local contact_vcards = {};

-- Advertise in disco

module:add_identity("server", "directory", module:get_option_string("name", "Prosody"));
module:add_feature("urn:xmpp:server-presence");

-- Handle subscriptions

module:hook("presence/host", function(event) -- inbound presence to the host
	local origin, stanza = event.origin, event.stanza;

	local node, host, resource = jid_split(stanza.attr.from);
	if stanza.attr.from ~= host then return; end -- not from a host

	local t = stanza.attr.type;
	if t == "probe" then
		module:send(st.presence({ from = module.host, to = host, id = stanza.attr.id }));
	elseif t == "subscribe" then
		subscription_from[host] = true;
		module:send(st.presence({ from = module.host, to = host, id = stanza.attr.id, type = "subscribed" }));
		module:send(st.presence({ from = module.host, to = host, id = stanza.attr.id }));
		add_contact(host);
	elseif t == "subscribed" then
		subscription_to[host] = true;
		query_host(host);
	elseif t == "unsubscribe" then
		subscription_from[host] = nil;
		module:send(st.presence({ from = module.host, to = host, id = stanza.attr.id, type = "unsubscribed" }));
		remove_contact(host);
	elseif t == "unsubscribed" then
		subscription_to[host] = nil;
		remove_contact(host);
	end
	return true;
end, 10); -- priority over mod_presence

function remove_contact(host, id)
	contact_features[host] = nil;
	contact_vcards[host] = nil;
	if subscription_to[host] then
		subscription_to[host] = nil;
		module:send(st.presence({ from = module.host, to = host, id = id, type = "unsubscribe" }));
	end
	if subscription_from[host] then
		subscription_from[host] = nil;
		module:send(st.presence({ from = module.host, to = host, id = id, type = "unsubscribed" }));
	end
end
function add_contact(host, id)
	if not subscription_to[host] then
		module:send(st.presence({ from = module.host, to = host, id = id, type = "subscribe" }));
	end
end

-- Admin ad-hoc command to subscribe

local function add_contact_handler(self, data, state)
	local layout = dataforms_new{
		title = "Adding a Server Buddy";
		instructions = "Fill out this form to add a \"server buddy\".";

		{ name = "FORM_TYPE", type = "hidden", value = "http://jabber.org/protocol/admin" };
		{ name = "peerjid", type = "jid-single", required = true, label = "The server to add" };
	};

	if not state then
		return { status = "executing", form = layout }, "executing";
	elseif data.action == "canceled" then
		return { status = "canceled" };
	else
		local fields = layout:data(data.form);
		local peerjid = nameprep(fields.peerjid);
		if not peerjid or peerjid == "" or #peerjid > 1023 or not to_ascii(peerjid) then
			return { status = "completed", error = { message = "Invalid JID" } };
		end
		add_contact(peerjid);
		return { status = "completed" };
	end
end

local add_contact_command = adhoc_new("Adding a Server Buddy", "http://jabber.org/protocol/admin#server-buddy", add_contact_handler, "admin");
module:add_item("adhoc", add_contact_command);

-- Disco query remote host
function query_host(host)
	local stanza = st.iq({ from = module.host, to = host, type = "get", id = "mod_service_directories:disco" })
		:query("http://jabber.org/protocol/disco#info");
	module:send(stanza);
end

-- Handle disco query result
module:hook("iq-result/bare/mod_service_directories:disco", function(event)
	local origin, stanza = event.origin, event.stanza;

	if not subscription_to[stanza.attr.from] then return; end -- not from a contact
	local host = stanza.attr.from;

	local query = stanza:get_child("query", "http://jabber.org/protocol/disco#info")
	if not query then return; end

	-- extract disco features
	local features = {};
	for _,tag in ipairs(query.tags) do
		if tag.name == "feature" and tag.attr.var then
			features[tag.attr.var] = true;
		end
	end
	contact_features[host] = features;

	if features["urn:ietf:params:xml:ns:vcard-4.0"] then
		local stanza = st.iq({ from = module.host, to = host, type = "get", id = "mod_service_directories:vcard" })
			:tag("vcard", { xmlns = "urn:ietf:params:xml:ns:vcard-4.0" });
		module:send(stanza);
	end
	return true;
end);

-- Handle vcard result
module:hook("iq-result/bare/mod_service_directories:vcard", function(event)
	local origin, stanza = event.origin, event.stanza;

	if not subscription_to[stanza.attr.from] then return; end -- not from a contact
	local host = stanza.attr.from;

	local vcard = stanza:get_child("vcard", "urn:ietf:params:xml:ns:vcard-4.0");
	if not vcard then return; end

	contact_vcards[host] = st.clone(vcard);
	return true;
end);

-- PubSub

-- TODO the following should be replaced by mod_pubsub

module:hook("iq-get/host/http://jabber.org/protocol/pubsub:pubsub", function(event)
	local origin, stanza = event.origin, event.stanza;
	local payload = stanza.tags[1];

	local items = payload:get_child("items", "http://jabber.org/protocol/pubsub");
	if items and items.attr.node == "urn:xmpp:contacts" then
		local reply = st.reply(stanza)
			:tag("pubsub", { xmlns = "http://jabber.org/protocol/pubsub" })
				:tag("items", { node = "urn:xmpp:contacts" });
		for host, vcard in pairs(contact_vcards) do
			reply:tag("item", { id = host })
				:add_child(vcard)
			:up();
		end
		origin.send(reply);
		return true;
	end
end);

