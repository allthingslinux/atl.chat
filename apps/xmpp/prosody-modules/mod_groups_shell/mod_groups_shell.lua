module:set_global()

local modulemanager = require "core.modulemanager";

local shell_env = module:shared("/*/admin_shell/env")

shell_env.groups = {};

function shell_env.groups:sync_group(host, group_id)
	local print = self.session.print;

	if not host then
		return false, "host not given"
	end

	local mod_groups = modulemanager.get_module(host, "groups_internal")
	if not mod_groups then
		return false, host .. " does not have mod_groups_internal loaded"
	end

	if not group_id then
		return false, "group id not given"
	end

	local ok, err = mod_groups.emit_member_events(group_id)
	if ok then
		return true, "Synchronised members"
	else
		return ok, err
	end
end
