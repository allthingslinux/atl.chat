local os_time = os.time;
local math_floor = math.floor;
local store = module:open_store("muc_activity", "keyval");

local accumulator = {};

local field_var = "{urn:xmpp:muc-activity}message-activity";

module:hook("muc-room-destroyed", function (event)
	local jid = event.room.jid;
	module:log("debug", "deleting activity data for destroyed muc %s", jid);
	store:set_keys(jid, {});
	accumulator[jid] = nil;
end)

module:hook("muc-occupant-groupchat", function (event)
	local jid = event.room.jid;
	if not event.room:get_persistent() then
		-- we do not count stanzas in non-persistent rooms
		if accumulator[jid] then
			-- if we have state for the room, drop it.
			store:set_keys(jid, {});
			accumulator[jid] = nil;
		end

		return
	end

	if event.stanza:get_child("body") == nil then
		-- we do not count stanzas without body.
		return
	end

	module:log("debug", "counting stanza for MUC activity in %s", jid);
	accumulator[jid] = (accumulator[jid] or 0) + 1;
end)

local function shift(data)
	for i = 1, 23 do
		data[i] = data[i+1]
	end
end

local function accumulate(data)
	if data == nil then
		return 0;
	end
	local accum = 0;
	for i = 1, 24 do
		local v = data[i];
		if v ~= nil then
			accum = accum + v
		end
	end
	return accum;
end

module:hourly("muc-activity-shift", function ()
	module:log("info", "shifting MUC activity store forward by one hour");
	for jid in store:users() do
		local data = store:get(jid);
		local new = accumulator[jid] or 0;
		shift(data);
		data[24] = new;
		accumulator[jid] = nil;
		store:set(jid, data);
	end

	-- All remaining entries in the accumulator are non-existent in the store,
	-- otherwise they would have been removed earlier.
	for jid, count in pairs(accumulator) do
		store:set(jid, { [24] = count });
	end
	accumulator = {};
end)

module:hook("muc-disco#info", function(event)
	local room = event.room;
	local jid = room.jid;
	if not room:get_persistent() or not room:get_public() or room:get_members_only() or room:get_password() ~= nil then
		module:log("debug", "%s is not persistent or not public, not injecting message activity", jid);
		return;
	end
	local count = accumulate(store:get(jid)) / 24.0;
	table.insert(event.form, { name = field_var, label = "Message activity" });
	event.formdata[field_var] = tostring(count);
end);
