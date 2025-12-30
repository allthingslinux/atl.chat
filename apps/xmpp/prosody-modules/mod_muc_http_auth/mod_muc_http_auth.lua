local http = require "net.http";
local jid_bare = require "util.jid".bare;
local jid_host = require "util.jid".host;
local jid_node = require "util.jid".node;
local jid_resource = require "util.jid".resource;
local json = require "util.json";
local set = require "util.set";
local st = require "util.stanza";
local urlencode = require "util.http".urlencode;
local wait_for = require "util.async".wait_for;

local authorization_url = module:get_option("muc_http_auth_url", "")
local enabled_for = module:get_option("muc_http_auth_enabled_for",  nil)
local disabled_for = module:get_option("muc_http_auth_disabled_for",  nil)
local insecure = module:get_option("muc_http_auth_insecure", false) --For development purposes
local authorize_registration = module:get_option("muc_http_auth_authorize_registration", false)
local authorization_header = module:get_option("muc_http_auth_authorization_header", nil)

local options = {method="GET", insecure=insecure}
if authorization_header then
	options.headers = {["Authorization"] = authorization_header};
end

local verbs = {presence='join', iq='register'};

local function must_be_authorized(room_node, user_host)
	-- If none of these is set, all rooms need authorization
	if not enabled_for and not disabled_for then return true; end

	if enabled_for then
		local enabled_for_host = set.new(enabled_for[user_host] or {});
		local enabled_for_all = set.new(enabled_for['all'] or {});
		return enabled_for_host:contains(room_node) or enabled_for_all:contains(room_node);

	end
	if disabled_for then
		local disabled_for_host = set.new(disabled_for[user_host] or {});
		local disabled_for_all = set.new(disabled_for['all'] or {});
		return not disabled_for_host:contains(room_node) and not disabled_for_all:contains(room_node);
	end
end

local function handle_success(response)
	local body = json.decode(response.body or "") or {}
	response = {
		err = body.error,
		allowed = body.allowed,
		code = response.code
	}
	return {response=response, err=response.err};
end

local function handle_error(err)
	return {err=err};
end

local function handle_presence(event)
	local stanza = event.stanza;
	if stanza.name ~= "iq" and stanza.name ~= "presence" or stanza.attr.type == "unavailable" then return; end

	local room, origin = event.room, event.origin;
	if (not room) or (not origin) then return; end

	local user_bare_jid = jid_bare(stanza.attr.from)
	if not must_be_authorized(jid_node(room.jid), jid_host(user_bare_jid)) then
		module:log("debug", "Authorization not required for "..jid_node(room.jid).." and "..jid_host(user_bare_jid))
		return;
	end

	local user_nickname = jid_resource(stanza.attr.to);

	-- Nickname is mandatory to enter a MUC
	if not user_nickname then return; end

	local url = authorization_url .. "?userJID=" .. urlencode(user_bare_jid) .."&mucJID=" .. urlencode(room.jid) .. "&nickname=" .. urlencode(user_nickname);

	local result = wait_for(http.request(url, options):next(handle_success, handle_error));
	local response, err = result.response, result.err;

	local verb = verbs[stanza.name];
	if not (response and response.allowed) then
		-- User is not authorized to join this room
		err = (response or {}).err or err
		module:log("debug", user_bare_jid .. " is not authorized to " ..verb.. ": " .. room.jid .. " Error: " .. tostring(err));
		origin.send(st.error_reply(stanza, "auth", "not-authorized", nil, module.host));
		return true;
	end

	module:log("debug", user_bare_jid .. " is authorized to " .. verb .. ": " .. room.jid);
	return;
end

if authorize_registration then
	module:hook("muc-register-iq", handle_presence);
end

module:hook("muc-occupant-pre-join", handle_presence);
