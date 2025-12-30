local array = require "util.array";

module:add_item("openid-claim", { claim = "groups"; title = "User Groups";
	description = "List of group memberships"; });

local group_memberships = module:open_store("groups", "map");
local function user_groups(username)
	return pairs(group_memberships:get_all(username) or {});
end

module:hook("token/userinfo", function(event)
	local userinfo = event.userinfo;
	if event.claims:contains("groups") then
		userinfo.groups = array(user_groups(event.username));
	end
end);
