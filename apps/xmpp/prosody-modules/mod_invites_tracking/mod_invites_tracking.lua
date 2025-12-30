local tracking_store = module:open_store("invites_tracking");

module:hook("user-registered", function(event)
	local validated_invite = event.validated_invite or (event.session and event.session.validated_invite);
	local new_username = event.username;

	if not validated_invite then
		module:log("debug", "No invitation found for registration of %s", new_username);
		return;
	end

	local invite_id = nil;
	local invite_source = nil;
	if validated_invite then
		invite_source = validated_invite.additional_data and validated_invite.additional_data.source;
		invite_id = validated_invite.token;
	end

	tracking_store:set(new_username, {invite_id = invite_id, invite_source = invite_source});
	module:log("debug", "recorded that invite from %s was used to create %s", invite_source, new_username)
end);

-- " " is an invalid localpart -> we can safely use it for store metadata
tracking_store:set(" ", {version="1"});
