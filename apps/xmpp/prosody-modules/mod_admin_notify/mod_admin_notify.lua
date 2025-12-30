local it = require "util.iterators";
local jid = require "util.jid";
local set = require "util.set";
local st = require "util.stanza";

local roles_store = module:open_store("roles", "map");
local config_admins = module:get_option_inherited_set("admins", {}) / jid.prep;

local function append_host(username)
	return username.."@"..module.host;
end

local function get_admins()
	local role_admins = roles_store:get_all("prosody:admin") or {};
	local admins = config_admins + (set.new(it.to_array(it.keys(role_admins))) / append_host);
	return admins;
end

function notify(text) --luacheck: ignore 131/notify
	local base_msg = st.message({ from = module.host })
		:text_tag("body", text);
	for admin_jid in get_admins() do
		local msg = st.clone(base_msg);
		msg.attr.to = admin_jid;
		module:send(msg);
	end
end
