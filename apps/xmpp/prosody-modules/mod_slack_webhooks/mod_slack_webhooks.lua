-- Allow Slack-style incoming and outgoing hooks to MUC rooms
-- Based on mod_muc_intercom and mod_post_msg
-- Copyright 2016-2017 Nathan Whitehorn <nwhitehorn@physics.ucla.edu>
--
-- This file is MIT/X11 licensed.

module:depends"http"

local msg = require "util.stanza".message;
local jid = require "util.jid";
local now = require "util.datetime".datetime;
local json = require "util.json"
local formdecode = require "net.http".formdecode;
local http = require "net.http";

local mod_muc = module:depends"muc";
local rooms = rawget(mod_muc, "rooms");
local get_room_from_jid = rawget(mod_muc, "get_room_from_jid") or
	function (room_jid)
		return rooms[room_jid];
	end

local routing = module:get_option("outgoing_webhook_routing") or {};
local listen_path = module:get_option("incoming_webhook_path") or "/webhook";
local default_from_nick = module:get_option("incoming_webhook_default_nick") or "Bot";

function postcallback(_, code)
	module:log("debug", "HTTP result %d", code)
end

function check_message(data)
	local stanza = data.stanza;

	local this_room = get_room_from_jid(stanza.attr.to);
	if not this_room then return; end -- no such room

	local from_room_jid = this_room._jid_nick[stanza.attr.from];
	if not from_room_jid then return; end -- no such nick

	local from_room, from_host, from_nick = jid.split(from_room_jid);

	local body = stanza:get_child("body");
	if not body then return; end -- No body, like topic changes
	body = body and body:get_text(); -- I feel like I want to do `or ""` there :/

	if not routing[from_room] then
		return;
	end

	local json_out = {
		channel_name = from_room,
		timestamp = now(),
		text = body,
		team_domain = from_host,
		user_name = from_nick,
	};
	local stanzaid = stanza:get_child("id");
	if stanzaid and string.sub(stanzaid,1,string.len("webhookbot"))=="webhookbot" then
		json_out["bot_id"] = "webhookbot";
	end

	json_out = json.encode(json_out)
	local url = routing[from_room];
	module:log("debug", "message from %s in %s to %s", from_nick, from_room, url);
	if url == "DEBUG" then
		module:log("debug", "json_out = %s", json_out);
		return;
	end
	local headers = {
		["Content-Type"] = "application/json",
	};
	http.request(url, { method = "POST", body = json_out, headers = headers }, postcallback)
end

module:hook("message/bare", check_message, 10);

local function route_post(f)
	return function(event, path)
		local bare_room = jid.join(path, module.host);
		if not get_room_from_jid(bare_room) then
			module:log("warn", "mod_slack_webhook: invalid JID: %s", bare_room);
			return 404;
		end
		-- Check secret?
		return f(event, path)
	end
end

local function handle_post(event, path)
	local request = event.request;
	local headers = request.headers;

	local body_type = headers.content_type;
	local post_body;
	if body_type == "application/x-www-form-urlencoded" then
		post_body = formdecode(request.body);
	elseif body_type == "application/json" then
		post_body = json.decode(request.body)
		if not post_body then
			return 420;
		end
	else
		return 422;
	end
	local bare_room = jid.join(path, module.host);
	local dest_room = get_room_from_jid(bare_room);
	local from_nick = default_from_nick;
	if post_body["username"] then
		from_nick = post_body["username"];
	end
	local sender = jid.join(path, module.host, from_nick);
	module:log("debug", "message to %s from %s", bare_room, sender);
	module:log("debug", "body: %s", post_body["text"]);
	local message = msg({ to = bare_room, from = sender, type = "groupchat", id="webhookbot" .. now()},post_body["text"]);
	dest_room:broadcast_message(message, true);
	return 201;
end

module:provides("http", {
	default_path = listen_path;
	route = {
		["POST /*"] = route_post(handle_post);
		OPTIONS = function(e)
			local headers = e.response.headers;
			headers.allow = "POST";
			headers.accept = "application/x-www-form-urlencoded, application/json";
			return 200;
		end;
	}
});

