-- Export a module:may() that works on Prosody 0.12 and earlier
-- (i.e. backed by is_admin).

-- This API is safe because Prosody 0.12 and earlier do not support
-- per-session roles - all authorization is based on JID alone. It is not
-- safe on versions that support per-session authorization.

module:set_global();

local moduleapi = require "core.moduleapi";

-- If module.may already exists, abort
if moduleapi.may then return; end

local jid_split = require "util.jid".split;
local um_is_admin = require "core.usermanager".is_admin;

local function get_jid_role_name(jid, host)
	if um_is_admin(jid, "*") then
		return "prosody:operator";
	elseif um_is_admin(jid, host) then
		return "prosody:admin";
	end
	return nil;
end

local function get_user_role_name(username, host)
	return get_jid_role_name(username.."@"..host, host);
end

-- permissions[host][role_name][permission_name] = is_permitted
local permissions = {};

local role_inheritance = {
	["prosody:operator"] = "prosody:admin";
	["prosody:admin"] = "prosody:member";
	["prosody:member"] = "prosody:registered";
	["prosody:registered"] = "prosody:guest";

	-- COMPAT
	["prosody:user"] = "prosody:registered";
};

local function role_may(host, role_name, permission)
	local host_roles = permissions[host];
	if not host_roles then
		return false;
	end
	local role_permissions = host_roles[role_name];
	if not role_permissions then
		return false;
	end
	if role_permissions[permission] then
		return true;
	end
	local next_role = role_inheritance[role_name];
	if not next_role then
		return false;
	end
	return role_may(host, next_role, permission);
end

function moduleapi.may(self, action, context)
	if action:byte(1) == 58 then -- action begins with ':'
		action = self.name..action; -- prepend module name
	end
	if type(context) == "string" then -- check JID permissions
		local role;
		local node, host = jid_split(context);
		if host == self.host then
			role = get_user_role_name(node, self.host);
		else
			role = get_jid_role_name(context, self.host);
		end
		if not role then
			self:log("debug", "Access denied: JID <%s> may not %s (no role found)", context, action);
			return false;
		end

		local permit = role_may(self.host, role, action);
		if not permit then
			self:log("debug", "Access denied: JID <%s> may not %s (not permitted by role %s)", context, action, role.name);
		end
		return permit;
	end

	local session = context.origin or context.session;
	if type(session) ~= "table" then
		error("Unable to identify actor session from context");
	end
	if session.type == "s2sin" or (session.type == "c2s" and session.host ~= self.host) then
		local actor_jid = context.stanza.attr.from;
		local role_name = get_jid_role_name(actor_jid);
		if not role_name then
			self:log("debug", "Access denied: JID <%s> may not %s (no role found)", actor_jid, action);
			return false;
		end
		local permit = role_may(self.host, role_name, action, context);
		if not permit then
			self:log("debug", "Access denied: JID <%s> may not %s (not permitted by role %s)", actor_jid, action, role_name);
		end
		return permit;
	end
end

function moduleapi.default_permission(self, role_name, permission)
	local p = permissions[self.host];
	if not p then
		p = {};
		permissions[self.host] = p;
	end
	local r = p[role_name];
	if not r then
		r = {};
		p[role_name] = r;
	end
	r[permission] = true;
end

function moduleapi.default_permissions(self, role_name, permission_list)
	for _, permission in ipairs(permission_list) do
		self:default_permission(role_name, permission);
	end
end

function module.add_host(host_module)
	permissions[host_module.host] = {};
	function host_module.unload()
		permissions[host_module.host] = nil;
	end
end
