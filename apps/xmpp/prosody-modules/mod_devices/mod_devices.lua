local it = require "util.iterators";
local new_id = require "util.id".medium;

local max_user_devices = module:get_option_number("max_user_devices", 5);

local device_store = module:open_store("devices");
local device_map_store = module:open_store("devices", "map");

--- Helper functions

local function _compare_device_timestamps(a, b)
	return (a.last_activity_at or 0) < (b.last_activity_at or 0);
end
local function sorted_devices(devices)
	return it.sorted_pairs(devices, _compare_device_timestamps);
end

local function new_device(username, alt_ids)
	local current_time = os.time();
	local device = {
		id = "dv-"..new_id();
		created_at = current_time;
		last_activity = "created";
		last_activity_at = current_time;
		alt_ids = alt_ids or {};
	};

	local devices = device_store:get(username);
	if not devices then
		devices = {};
	end
	devices[device.id] = device;
	local devices_ordered = {};
	for id in sorted_devices(devices) do
		table.insert(devices_ordered, id);
	end
	if #devices_ordered > max_user_devices then
		-- Iterate through oldest devices that are above limit, backwards
		for i = #devices_ordered, max_user_devices+1, -1 do
			local id = table.remove(devices_ordered, i);
			devices[id] = nil;
			module:log("debug", "Removing old device for %s: %s", username, id);
		end
	end
	device_store:set(username, devices);
	return device;
end

local function get_device_with_alt_id(username, alt_id_type, alt_id)
	local devices = device_store:get(username);
	if not devices then
		return nil;
	end

	for _, device in pairs(devices) do
		if device.alt_ids[alt_id_type] == alt_id then
			return device;
		end
	end
end

local function set_device_alt_id(username, device_id, alt_id_type, alt_id)
	local devices = device_store:get(username);
	if not devices or not devices[device_id] then
		return nil, "no such device";
	end
	devices[device_id].alt_ids[alt_id_type] = alt_id;
end

local function record_device_state(username, device_id, activity, time)
	local device = device_map_store:get(username, device_id);
	device.last_activity = activity;
	device.last_activity_at = time or os.time();
	device_map_store:set(username, device_id, device);
end

local function find_device(username, info)
	for _, alt_id_type in ipairs({ "resumption_token", "resource" }) do
		local alt_id = info[alt_id_type];
		if alt_id then
			local device = get_device_with_alt_id(username, alt_id_type, alt_id);
			if device then
				return device, alt_id_type;
			end
		end
	end
end

--- Information gathering

module:hook("pre-resource-bind", function (event)
	event.session.device_requested_resource = event.resource;
end, 1000);


local function store_resumption_token(session, stanza)
	session.device_requested_resume = stanza.attr.previd;
end
module:hook_stanza("urn:xmpp:sm:2", "resume", store_resumption_token, 5);
module:hook_stanza("urn:xmpp:sm:3", "resume", store_resumption_token, 5);

--- Identify device after resource bind

module:hook("resource-bind", function (event)
	local info = {
		resource = event.session.device_requested_resource;
		resumption_token = event.session.device_requested_resume;
	};
	local device, source = find_device(event.session.username, info);
	if device then
		event.session.log("debug", "Associated with device %s (from %s)", device.id, source);
		event.session.device_id = device.id;
	else
		device = new_device(event.session.username, info);
		event.session.log("debug", "Creating new device %s for session", device.id);
		event.session.device_id = device.id;
	end
	record_device_state(event.session.username, device.id, "login");
end, 1000);

module:hook("resource-unbind", function (event)
	if event.session.device_id then
		record_device_state(event.session.username, event.session.device_id, "logout");
	end
end);
