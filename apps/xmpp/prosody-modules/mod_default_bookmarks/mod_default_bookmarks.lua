-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
-- Copyright (C) 2011 Kim Alvefur
-- Copyright (C) 2018 Emmanuel Gil Peyrot
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local st = require "util.stanza"
local dm_load = require "util.datamanager".load
local jid = require "util.jid"

-- COMPAT w/trunk
local mod_bookmarks_available = false;
local mm = require "core.modulemanager";
if mm.get_modules_for_host then
	local host_modules = mm.get_modules_for_host(module.host);
	if host_modules:contains("bookmarks") then
		mod_bookmarks_available = "bookmarks";
	elseif host_modules:contains("bookmarks2") then
		mod_bookmarks_available = "bookmarks2";
	end
end

local function get_default_bookmarks(nickname)
	local bookmarks = module:get_option_array("default_bookmarks");
	if not bookmarks or #bookmarks == 0 then
		return false;
	end
	local reply = st.stanza("storage", { xmlns = "storage:bookmarks" });
	local nick = nickname and st.stanza("nick"):text(nickname);
	for _, bookmark in ipairs(bookmarks) do
		if type(bookmark) ~= "table" then -- assume it's only a jid
			bookmark = { jid = bookmark, name = jid.split(bookmark) };
		end
		reply:tag("conference", {
			jid = bookmark.jid,
			name = bookmark.name,
			autojoin = "1",
		});
		if nick then
			reply:add_child(nick):up();
		end
		if bookmark.password then
			reply:tag("password"):text(bookmark.password):up();
		end
		reply:up();
	end
	return reply;
end

if mod_bookmarks_available then
	local mod_bookmarks = module:depends(mod_bookmarks_available);
	if rawget(mod_bookmarks, "publish_to_pep") then
		local function on_bookmarks_empty(event)
			local session = event.session;
			local bookmarks = get_default_bookmarks(session.username);
			if bookmarks then
				mod_bookmarks.publish_to_pep(session.full_jid, bookmarks);
			end
		end
		module:hook("bookmarks/empty", on_bookmarks_empty);
	else
		local mod_pep = module:depends "pep";

		local function publish_bookmarks2(event)
			local session = event.session;
			local publish_options = {
				["persist_items"] = true;
				["max_items"] = "max";
				["send_last_published_item"] = "never";
				["access_model"] = "whitelist";
			}
			if not pcall(mod_pep.check_node_config, nil, nil, publish_options) then
				-- 0.11 or earlier not supporting max_items="max" trows an error here
				module:log("debug", "Setting max_items=pep_max_items because 'max' is not supported in this version");
				publish_options["max_items"] = module:get_option_number("pep_max_items", 256);
			end
			local service = mod_pep.get_pep_service(session.username);
			local bookmarks = module:get_option_array("default_bookmarks");
			if not bookmarks or #bookmarks == 0 then
				return;
			end
			local ns = event.version or "urn:xmpp:bookmarks:1";
			for i, bookmark in ipairs(bookmarks) do
				if type(bookmark) ~= "table" then -- assume it's only a jid
					bookmark = { jid = bookmark, name = jid.split(bookmark) };
				end
				local bm_jid = jid.prep(bookmark.jid);
				if not bm_jid then
					module:log("error", "Invalid JID in default_bookmarks[%d].jid = %q", i, bookmark.jid);
				else
					local item = st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub"; id = bm_jid });
					item:tag("conference", { xmlns = ns; name = bookmark.name; autojoin = bookmark.autojoin and "true" or nil });
					if bookmark.nick then item:text_tag("nick", bookmarks.nick); end
					if bookmark.password then item:text_tag("password", bookmarks.password); end
					local ok, err = service:publish("urn:xmpp:bookmarks:1", session.full_jid, bm_jid, item, publish_options);
					if not ok then
						module:log("error", "Could not add default bookmark %s to %s: %s", bm_jid, session.username, err);
					end
				end
			end
		end
		module:hook("bookmarks/empty", publish_bookmarks2);
	end
else
	local function on_private_xml_get(event)
		local origin, stanza = event.origin, event.stanza;
		local tag = stanza.tags[1].tags[1];
		local key = tag.name..":"..tag.attr.xmlns;
		if key ~= "storage:storage:bookmarks" then
			return;
		end

		local data, err = dm_load(origin.username, origin.host, "private");
		if data and data[key] then
			return;
		end

		local bookmarks = get_default_bookmarks(origin.username);
		if not bookmarks then
			return;
		end;

		local reply = st.reply(stanza):tag("query", { xmlns = "jabber:iq:private" })
			:add_child(bookmarks);
		origin.send(reply);
		return true;
	end
	module:hook("iq-get/self/jabber:iq:private:query", on_private_xml_get, 1);
end
