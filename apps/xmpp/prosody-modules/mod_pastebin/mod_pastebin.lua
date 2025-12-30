
local st = require "util.stanza";
module:depends("http");
local uuid_new = require "util.uuid".generate;
local os_time = os.time;
local t_remove = table.remove;
local add_task = require "util.timer".add_task;
local jid_bare = require "util.jid".bare;

local function get_room_from_jid() end;
local is_component = module:get_host_type() == "component";
if is_component then
	local mod_muc = module:depends "muc";
	local muc_rooms = rawget(mod_muc, "rooms");
	get_room_from_jid = rawget(mod_muc, "get_room_from_jid") or
		function (jid)
			return muc_rooms[jid];
		end
end

local utf8_pattern = "[\194-\244][\128-\191]*$";
local function drop_invalid_utf8(seq)
	local start = seq:byte();
	module:log("debug", "utf8: %d, %d", start, #seq);
	if (start <= 223 and #seq < 2)
	or (start >= 224 and start <= 239 and #seq < 3)
	or (start >= 240 and start <= 244 and #seq < 4)
	or (start > 244) then
		return "";
	end
	return seq;
end

local function utf8_length(str)
	local _, count = string.gsub(str, "[^\128-\193]", "");
	return count;
end

local pastebin_private_messages = module:get_option_boolean("pastebin_private_messages", not is_component);
local length_threshold = module:get_option_number("pastebin_threshold", 500);
local line_threshold = module:get_option_number("pastebin_line_threshold", 4);
local max_summary_length = module:get_option_number("pastebin_summary_length", 150);
local html_preview = module:get_option_boolean("pastebin_html_preview", true);

local base_url = module:get_option_string("pastebin_url", module:http_url()):gsub("/$", "").."/";

-- Seconds a paste should live for in seconds (config is in hours), default 24 hours
local expire_after = math.floor(module:get_option_number("pastebin_expire_after", 24) * 3600);

local trigger_string = module:get_option_string("pastebin_trigger");
trigger_string = (trigger_string and trigger_string .. " ");

local pastes = {};

local xmlns_xhtmlim = "http://jabber.org/protocol/xhtml-im";
local xmlns_xhtml = "http://www.w3.org/1999/xhtml";

function pastebin_text(text)
	local uuid = uuid_new();
	pastes[uuid] = { body = text, time = os_time(), };
	pastes[#pastes+1] = uuid;
	if not pastes[2] then -- No other pastes, give the timer a kick
		add_task(expire_after, expire_pastes);
	end
	return base_url..uuid;
end

function handle_request(event, pasteid)
	event.response.headers.content_type = "text/plain; charset=utf-8";

	if not pasteid then
		return "Invalid paste id, perhaps it expired?";
	end

	--module:log("debug", "Received request, replying: %s", pastes[pasteid].text);
	local paste = pastes[pasteid];

	if not paste then
		return "Invalid paste id, perhaps it expired?";
	end

	return paste.body;
end

local function replace_tag(s, replacement)
	local once = false;
	s:maptags(function (tag)
		if tag.name == replacement.name and tag.attr.xmlns == replacement.attr.xmlns then
			if not once then
				once = true;
				return replacement;
			else
				return nil;
			end
		end
		return tag;
	end);
	if not once then
		s:add_child(replacement);
	end
end

function check_message(data)
	local stanza = data.stanza;

	-- Only check for MUC presence when loaded on a component.
	if is_component then
		local room = get_room_from_jid(jid_bare(stanza.attr.to));
		if not room then return; end

		local nick = room._jid_nick[stanza.attr.from];
		if not nick then return; end
	end

	local body = stanza:get_child_text("body");

	if not body then return; end

	--module:log("debug", "Body(%s) length: %d", type(body), #(body or ""));

	if ( #body > length_threshold and utf8_length(body) > length_threshold ) or
		(trigger_string and body:find(trigger_string, 1, true) == 1) or
		(select(2, body:gsub("\n", "%0")) >= line_threshold)
	then
		if trigger_string and body:sub(1, #trigger_string) == trigger_string then
			body = body:sub(#trigger_string+1);
		end
		local url = pastebin_text(body);
		module:log("debug", "Pasted message as %s", url);
		--module:log("debug", " stanza[bodyindex] = %q", tostring( stanza[bodyindex]));
		local summary = (body:sub(1, max_summary_length):gsub(utf8_pattern, drop_invalid_utf8) or ""):match("[^\n]+") or "";
		summary = summary:match("^%s*(.-)%s*$");
		local summary_prefixed = summary:match("[,:]$");
		replace_tag(stanza, st.stanza("body"):text(summary .. "\n" .. url));

		stanza:add_child(st.stanza("query", { xmlns = "jabber:iq:oob" }):tag("url"):text(url));

		if html_preview then
			local line_count = select(2, body:gsub("\n", "%0")) + 1;
			local link_text = ("[view %spaste (%d line%s)]"):format(summary_prefixed and "" or "rest of ", line_count, line_count == 1 and "" or "s");
			local html = st.stanza("html", { xmlns = xmlns_xhtmlim }):tag("body", { xmlns = xmlns_xhtml });
			html:tag("p"):text(summary.." "):up();
			html:tag("a", { href = url }):text(link_text):up();
			replace_tag(stanza, html);
		end
	end
end

module:hook("message/bare", check_message);
if pastebin_private_messages then
	module:hook("message/full", check_message);
end

module:hook("muc-disco#info", function (event)
	local reply, form, formdata = event.reply, event.form, event.formdata;
	reply:tag("feature", { var = "https://modules.prosody.im/mod_pastebin" }):up();
	table.insert(form, { name = "{https://modules.prosody.im/mod_pastebin}max_lines", datatype = "xs:integer" });
	table.insert(form, { name = "{https://modules.prosody.im/mod_pastebin}max_characters", datatype = "xs:integer" });
	formdata["{https://modules.prosody.im/mod_pastebin}max_lines"] = tostring(line_threshold);
	formdata["{https://modules.prosody.im/mod_pastebin}max_characters"] = tostring(length_threshold);
end);

function expire_pastes(time)
	time = time or os_time(); -- COMPAT with 0.5
	if pastes[1] then
		pastes[pastes[1]] = nil;
		t_remove(pastes, 1);
		if pastes[1] then
			return (expire_after - (time - pastes[pastes[1]].time)) + 1;
		end
	end
end


module:provides("http", {
	route = {
		["GET /*"] = handle_request;
	};
});

local function set_pastes_metatable()
	-- luacheck: ignore 212/pastes 431/pastes
	if expire_after == 0 then
		local dm = require "util.datamanager";
		setmetatable(pastes, {
			__index = function (pastes, id)
				if type(id) == "string" then
					return dm.load(id, module.host, "pastebin");
				end
			end;
			__newindex = function (pastes, id, data)
				if type(id) == "string" then
					dm.store(id, module.host, "pastebin", data);
				end
			end;
		});
	else
		setmetatable(pastes, nil);
	end
end

module.load = set_pastes_metatable;

function module.save()
	return { pastes = pastes };
end

function module.restore(data)
	pastes = data.pastes or pastes;
	set_pastes_metatable();
end
