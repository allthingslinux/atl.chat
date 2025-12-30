local host = module.host;
local usermanager = require"core.usermanager";

local mod_groups = module:depends("groups_internal");
local default_group_id = module:get_option("group_default_id", "default");
local default_group_name = module:get_option("group_default_name", "default");

local function trigger_migration()
	if mod_groups.exists(default_group_id) then
		module:log("debug", "skipping migration, group exists already")
		return
	end
	module:log("info", "migrating to mod_groups!")

	local group_id = default_group_id;
	local ok, err = mod_groups.create({name=default_group_name}, true, group_id);
	if not ok then
		module:log("error", "failed to create group: %s", err)
		return
	end

	for user in usermanager.users(host) do
		mod_groups.add_member(group_id, user, true);
		module:log("debug", "added %s to %s", user, group_id)
	end
	module:log("debug", "synchronising group %s", group_id)
	mod_groups.sync(group_id)
	module:log("info", "added all users to group %s", group_id)
end

module:hook_global("server-started", trigger_migration, -100)
