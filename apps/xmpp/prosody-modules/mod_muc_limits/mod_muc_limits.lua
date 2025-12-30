
local mod_muc = module:depends"muc";
local rooms = rawget(mod_muc, "rooms"); -- Old MUC API

local jid_split, jid_bare = require "util.jid".split, require "util.jid".bare;
local st = require "util.stanza";
local new_throttle = require "util.throttle".create;
local t_insert, t_concat = table.insert, table.concat;

local xmlns_muc = "http://jabber.org/protocol/muc";

local period = math.max(module:get_option_number("muc_event_rate", 0.5), 0);
local burst = math.max(module:get_option_number("muc_burst_factor", 6), 1);

local max_nick_length = module:get_option_number("muc_max_nick_length", 23); -- Default chosen through scientific methods
local max_line_count = module:get_option_number("muc_max_line_count", 23); -- Default chosen through s/scientific methods/copy and paste/
local max_char_count = module:get_option_number("muc_max_char_count", 5664); -- Default chosen by multiplying a number by 23
local base_cost = math.max(module:get_option_number("muc_limit_base_cost", 1), 0);
local line_multiplier = math.max(module:get_option_number("muc_line_count_multiplier", 0.1), 0);

local join_only = module:get_option_boolean("muc_limit_joins_only", false);
local dropped_count = 0;
local dropped_jids;

local function log_dropped()
	module:log("warn", "Dropped %d stanzas from %d JIDs: %s", dropped_count, #dropped_jids, t_concat(dropped_jids, ", "));
	dropped_count = 0;
	dropped_jids = nil;
end

local function handle_stanza(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.name == "presence" and stanza.attr.type == "unavailable" then -- Don't limit room leaving
		return;
	end
	local dest_room, dest_host, dest_nick = jid_split(stanza.attr.to);
	local room = event.room or rooms[dest_room.."@"..dest_host];
	if not room then return; end
	local from_jid = stanza.attr.from;
	if room:get_affiliation(jid_bare(from_jid)) then
		module:log("debug", "Skipping stanza from affiliated user...");
		return;
	elseif dest_nick and max_nick_length and stanza.name == "presence" and not room._occupants[stanza.attr.to] and #dest_nick > max_nick_length then
		module:log("debug", "Forbidding long (%d bytes) nick in %s", #dest_nick, dest_room)
		origin.send(st.error_reply(stanza, "modify", "policy-violation", "Your nick name is too long, please use a shorter one")
			:up():tag("x", { xmlns = xmlns_muc }));
		return true;
	end
	local throttle = room.throttle;
	if not room.throttle then
		throttle = new_throttle(period*burst, burst);
		room.throttle = throttle;
	end
	local cost = base_cost;
	local body = stanza:get_child_text("body");
	if body then
		-- TODO calculate a text diagonal cross-section or some mathemagical
		-- number, maybe some cost multipliers
		if #body > max_char_count then
			origin.send(st.error_reply(stanza, "modify", "policy-violation", "Your message is too long, please write a shorter one")
				:up():tag("x", { xmlns = xmlns_muc }));
			return true;
		end
		local body_lines = select(2, body:gsub("\n[^\n]*", ""));
		if body_lines > max_line_count then
			origin.send(st.error_reply(stanza, "modify", "policy-violation", "Your message is too long, please write a shorter one"):up()
				:tag("x", { xmlns = xmlns_muc; }));
			return true;
		end
		cost = cost + (body_lines * line_multiplier);
	end
	if not throttle:poll(cost) then
		module:log("debug", "Dropping stanza for %s@%s from %s, over rate limit", dest_room, dest_host, from_jid);
		if not dropped_jids then
			dropped_jids = { [from_jid] = true, from_jid };
			module:add_timer(5, log_dropped);
		elseif not dropped_jids[from_jid] then
			dropped_jids[from_jid] = true;
			t_insert(dropped_jids, from_jid);
		end
		dropped_count = dropped_count + 1;
		if stanza.attr.type == "error" then -- We don't want to bounce errors
			return true;
		end
		local reply = st.error_reply(stanza, "wait", "policy-violation", "The room is currently overactive, please try again later");
		if body then
			reply:up():tag("body"):text(body):up();
		end
		local x = stanza:get_child("x", xmlns_muc);
		if x then
			reply:add_child(st.clone(x));
		end
		origin.send(reply);
		return true;
	end
end

if rooms then
	function module.unload()
		for room_jid, room in pairs(rooms) do --luacheck: ignore 213/room_jid
			room.throttle = nil;
		end
	end

	module:hook("presence/full", handle_stanza, 501);
	if not join_only then
		module:hook("message/bare", handle_stanza, 501);
		module:hook("message/full", handle_stanza, 501);
		module:hook("presence/bare", handle_stanza, 501);
	end
else
	module:hook("muc-occupant-pre-join", handle_stanza);
	if not join_only then
		module:hook("muc-occupant-pre-change", handle_stanza);
		module:hook("muc-occupant-groupchat", handle_stanza);
	end
end
