local mod_muc = module:depends("muc");

function add_user_hat(user_jid, room_jid, hat_id, attachment)
	local room = mod_muc.get_room_from_jid(room_jid);
	if not room then
		return nil, "item-not-found", "no such room";
	end
	local user_aff = room:get_affiliation(user_jid);
	if not user_aff then
		return nil, "item-not-found", "user not affiliated with room";
	end
	local aff_data = room:get_affiliation_data(user_jid) or {};
	local hats = aff_data.hats;
	if not hats then
		hats = {};
		aff_data.hats = hats;
	end

	hats[hat_id] = {
		active = attachment.active;
		required = attachment.required;
		title = attachment.title;
	};

	local ok, err = room:set_affiliation(true, user_jid, user_aff, nil, aff_data);
	if not ok then
		return nil, err;
	end
	return true;
end

function remove_user_hat(user_jid, room_jid, hat_id)
	local room = mod_muc.get_room_from_jid(room_jid);
	if not room then
		return nil, "item-not-found", "no such room";
	end
	local user_aff = room:get_affiliation(user_jid);
	if not user_aff then
		return nil, "item-not-found", "user not affiliated with room";
	end
	local aff_data = room:get_affiliation_data(user_jid);
	local hats = aff_data and aff_data.hats;
	if not hats then
		return true;
	end

	hats[hat_id] = nil;

	local ok, err = room:set_affiliation(true, user_jid, user_aff, nil, aff_data);
	if not ok then
		return nil, err;
	end
	return true;
end

function set_user_hats(user_jid, room_jid, new_hats)
	local room = mod_muc.get_room_from_jid(room_jid);
	if not room then
		return nil, "item-not-found", "no such room";
	end
	local user_aff = room:get_affiliation(user_jid);
	if not user_aff then
		return nil, "item-not-found", "user not affiliated with room";
	end
	local aff_data = room:get_affiliation_data(user_jid) or {};

	aff_data.hats = new_hats;

	local ok, err = room:set_affiliation(true, user_jid, user_aff, nil, aff_data);
	if not ok then
		return nil, err;
	end
	return true;
end

