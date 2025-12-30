local mod_groups = module:depends("groups_internal");

module:hook("user-registered", function(event)
	local validated_invite = event.validated_invite or (event.session and event.session.validated_invite);
	if not validated_invite then
		-- not registered via invite, nothing to do
		return
	end
	local groups = validated_invite and validated_invite.additional_data and validated_invite.additional_data.groups;
	if not groups then
		-- invite has no groups, nothing to do
		return
	end

	local new_username = event.username;
	module:log("debug", "adding %s to groups from invite", new_username);
	for _, group in ipairs(groups) do
		mod_groups.add_member(group, new_username);
	end
end);
