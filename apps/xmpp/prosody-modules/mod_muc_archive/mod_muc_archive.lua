-- The MIT License (MIT)
--
-- Copyright (C) 2009 Thilo Cestonaro
-- Copyright (C) 2009 Waqas Hussain
-- Copyright (C) 2009-2013 Matthew Wild
-- Copyright (C) 2013 Kim Alvefur
-- Copyright (C) 2013 Marco Cirillo
-- Copyright (c) 2020 JC Brand
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy of
-- this software and associated documentation files (the "Software"), to deal in
-- the Software without restriction, including without limitation the rights to
-- use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
-- the Software, and to permit persons to whom the Software is furnished to do so,
-- subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in all
-- copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
-- FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
-- COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
-- IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
-- CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
--
local hosts = prosody.hosts;
local tostring = tostring;
local st = require "util.stanza";
local split_jid = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local time_now = os.time;

local muc_form_config_option = "muc#roomconfig_enablelogging"

local log_all_rooms = module:get_option_boolean("muc_log_all_rooms", false);
local log_by_default = module:get_option_boolean("muc_log_by_default", false);
local log_presences = module:get_option_boolean("muc_log_presences", true);

local archive_store = "muc_logging_archive";
local archive = module:open_store(archive_store, "archive");

local xmlns_muc_user = "http://jabber.org/protocol/muc#user";

if archive.name == "null" or not archive.find then
	if not archive.find then
		module:log("error", "Attempt to open archive storage returned a driver without archive API support");
		module:log("error", "mod_%s does not support archiving",
			archive._provided_by or archive.name and "storage_"..archive.name.."(?)" or "<unknown>");
	else
		module:log("error", "Attempt to open archive storage returned null driver");
	end
	module:log("info", "See https://prosody.im/doc/storage and https://prosody.im/doc/archiving for more information");
	return false;
end


-- Module Definitions

local function get_room_from_jid(jid)
	local node, host = split_jid(jid);
	local component = hosts[host];
	if component then
		local muc = component.modules.muc
		if muc and rawget(muc,"rooms") then
			-- We're running 0.9.x or 0.10 (old MUC API)
			return muc.rooms[jid];
		elseif muc and rawget(muc,"get_room_from_jid") then
			-- We're running >0.10 (new MUC API)
			return muc.get_room_from_jid(jid);
		else
			return
		end
	end
end

local function logging_enabled(room)
	if log_all_rooms then
		return true;
	end
	if room._data.hidden then -- do not log data of private rooms
		return false;
	end
	local enabled = room._data.logging;
	if enabled == nil then
		return log_by_default;
	end
	return enabled;
end


local function log_if_needed(event)
	local stanza = event.stanza;

	if (stanza.name == "presence") or
		(stanza.name == "iq") or
		(stanza.name == "message" and tostring(stanza.attr.type) == "groupchat")
	then
		local node, host = split_jid(stanza.attr.to);
		if node and host then
			local room = get_room_from_jid(node.."@"..host)
			if not room then return end
			-- Policy check
			if not logging_enabled(room) then return end

			local muc_to = nil
			local muc_from = nil;

			if stanza.name == "presence" and stanza.attr.type == nil then
				muc_from = stanza.attr.to;
			elseif stanza.name == "iq" and stanza.attr.type == "set" then
				-- kick, to is the room, from is the admin, nick who is kicked is attr of iq->query->item
				if stanza.tags[1] and stanza.tags[1].name == "query" then
					local tmp = stanza.tags[1];
					if tmp.tags[1] ~= nil and tmp.tags[1].name == "item" and tmp.tags[1].attr.nick then
						tmp = tmp.tags[1];
						for jid, nick in pairs(room._jid_nick) do
							if nick == stanza.attr.to .. "/" .. tmp.attr.nick then
								muc_to = nick;
								break;
							end
						end
					end
				end
			else
				for jid, nick in pairs(room._jid_nick) do
					if jid == stanza.attr.from then
						muc_from = nick;
						break;
					end
				end
			end

			if (muc_from or muc_to) then
				local stored_stanza = st.clone(stanza);
				stored_stanza.attr.from = muc_from;
				stored_stanza.attr.to = muc_to;

				if stanza.name == "message" then
					local actor = jid_bare(room._occupants[muc_from].jid);
					local affiliation = room:get_affiliation(actor) or "none";
					local role = room:get_role(actor) or room:get_default_role(affiliation);
					stored_stanza:add_direct_child(st.stanza("x", { xmlns = xmlns_muc_user })
						:tag("item", { affiliation = affiliation; role = role; jid = actor }));
				end

				local with = stanza.name
				if stanza.attr.type then
					with = with .. "<" .. stanza.attr.type
				end
				archive:append(node, nil, stored_stanza, time_now(), with);
			end
		end
	end
end

if not log_all_rooms then
	module:hook("muc-config-form", function(event)
		local room, form = event.room, event.form;
		table.insert(form,
		{
			name = muc_form_config_option,
			type = "boolean",
			label = "Enable Logging?",
			value = logging_enabled(room),
		}
		);
	end);

	module:hook("muc-config-submitted", function(event)
		local room, fields, changed = event.room, event.fields, event.changed;
		local new = fields[muc_form_config_option];
		if new ~= room._data.logging then
			room._data.logging = new;
			if type(changed) == "table" then
				changed[muc_form_config_option] = true;
			else
				event.changed = true;
			end
		end
	end);
end

module:hook("message/bare", log_if_needed, 1);

if log_presences then
	module:hook("iq/bare", log_if_needed, 1);
	module:hook("presence/full", log_if_needed, 1);
end

module:log("debug", "module mod_muc_archive loaded!");
