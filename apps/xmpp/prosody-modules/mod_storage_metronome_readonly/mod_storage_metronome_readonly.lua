local datamanager = require "prosody.core.storagemanager".olddm;
local datetime = require "prosody.util.datetime";
local st = require "prosody.util.stanza";
local now = require "prosody.util.time".now;
local gen_id = require "prosody.util.id".medium;
local set = require "prosody.util.set";
local envloadfile = require"prosody.util.envload".envloadfile;
local dir = require "lfs".dir;

local host = module.host;

local archive_item_limit = module:get_option_integer("storage_archive_item_limit", 10000, 0);

-- Metronome doesn’t store the item publish time, so fallback to the migration time.
local time_now = math.floor(now());

local function encode (s)
        return s and (s:gsub("%W", function (c) return string.format("%%%02x", c:byte()); end));
end

local file = io.open("/etc/mime.types");
local mimes = {};
while true do
	local line = file:read("*l");
	if not line then
		break;
	end
	if line ~= "" then
		local first_char = line:sub(1, 1);
		if first_char ~= "#" then
			--local line:match("(%S+)%s+"));
			local match = line:gmatch("%S+");
			local mime = match();
			for ext in match do
				mimes[ext] = mime;
			end
		end
	end
end
file:close();

local driver = {};

function driver:open(store, typ)
	local mt = self[typ or "keyval"]
	if not mt then
		return nil, "unsupported-store";
	end
	return setmetatable({ store = store, type = typ }, mt);
end

function driver:stores(username) -- luacheck: ignore 212/self
	if username == true then
		local nodes = set.new();
		for user in datamanager.users(host, "pep") do
			local data = datamanager.load(user, host, "pep");

			for _, node in ipairs(data["nodes"]) do
				nodes:add("pep_" .. node);
			end
		end
		return function()
			-- luacheck: ignore 512
			for node in nodes do
				nodes:remove(node);
				return node;
			end
		end;
	end
end

function driver:purge(user) -- luacheck: ignore 212/self user
	return nil, "unsupported-store";
end

local keyval = { };
driver.keyval = { __index = keyval };

function keyval:get(user)
	if self.store == "pep" then
		local ret = datamanager.load(user, host, self.store);
		local nodes = ret["nodes"];
		local result = {};

		local pep_base_path = datamanager.getpath(user, host, self.store):sub(1, -5);

		for _, node in ipairs(nodes) do
			local path = ("%s/%s.dat"):format(pep_base_path, encode(node));
			local get_data = envloadfile(path, {});
			if not get_data then
				module:log("error", "Failed to load metronome storage");
				return nil, "Error reading storage";
			end
			local success, data = pcall(get_data);
			if not success then
				module:log("error", "Unable to load metronome storage");
				return nil, "Error reading storage";
			end
			local new_node = {};
			new_node["name"] = node;
			new_node["subscribers"] = data["subscribers"];
			new_node["affiliations"] = data["affiliations"];
			new_node["config"] = data["config"];
			result[node] = new_node;
		end
		return result;
	elseif self.store == "cloud_notify" then
		local ret = datamanager.load(user, host, "push");
		local result = {};
		for jid, data in pairs(ret) do
			local secret = data["secret"];
			for node in pairs(data["nodes"]) do
				-- TODO: Does Metronome store more info than that?
				local options;
				if secret then
					options = st.preserialize(st.stanza("x", { xmlns = "jabber:x:data", type = "submit" })
						:tag("field", { var = "FORM_TYPE" })
							:text_tag("value", "http://jabber.org/protocol/pubsub#publish-options")
						:up()
						:tag("field", { var = "secret" })
							:text_tag("value", secret));
				end
				result[jid.."<"..node] = {
					jid = jid,
					node = node,
					options = options,
				};
			end
		end
		return result;
	elseif self.store == "roster" then
		return datamanager.load(user, host, self.store);
	elseif self.store == "vcard" then
		return datamanager.load(user, host, self.store);
	elseif self.store == "private" then
		return datamanager.load(user, host, self.store);

	-- After that, handle MUC specific stuff, not tested yet whatsoever.
	elseif self.store == "persistent" then
		return datamanager.load(user, host, self.store);
	elseif self.store == "config" then
		return datamanager.load(user, host, self.store);
	elseif self.store == "vcard_muc" then
		local data = datamanager.load(user, host, "room_icons");
		return data and data["photo"];
	else
		return nil, "unsupported-store";
	end
end

function keyval:set(user, data) -- luacheck: ignore 212/self user data
	return nil, "unsupported-store";
end

function keyval:users()
	local store;
	if self.store == "vcard_muc" then
		store = "room_icons";
	elseif self.store == "cloud_notify" then
		store = "push";
	else
		store = self.store;
	end
	return datamanager.users(host, store, self.type);
end

local function parse_logs(logs, jid)
	local iter = ipairs(logs);
	local i = 0;
	local message;
	return function()
		i, message = iter(logs, i);
		if not message then
			return;
		end

		local with;
		local bare_to = message["bare_to"];
		local bare_from = message["bare_from"];
		if jid == bare_to then
			-- received
			with = bare_from;
		else
			-- sent
			with = bare_to;
		end

		local to = message["to"];
		local from = message["from"];
		local id = message["id"];
		local type = message["type"];

		local key = message["uid"];
		local when = message["timestamp"];
		local item = st.message({ to = to, from = from, id = id, type = type }, message["body"]);
		if message["tags"] then
			for _, tag in ipairs(message["tags"]) do
				setmetatable(tag, st.stanza_mt);
				item:add_direct_child(tag);
			end
		end
		if message["marker"] then
			item:tag(message["marker"], { xmlns = "urn:xmpp:chat-markers:0", id = message["marker_id"] });
		end
		return key, item, when, with;
	end;
end

local archive = {};
driver.archive = { __index = archive };

archive.caps = {
	total = true;
	quota = archive_item_limit;
	full_id_range = true;
	ids = true;
};

function archive:append(username, key, value, when, with) -- luacheck: ignore 212/self username key value when with
	return nil, "unsupported-store";
end

function archive:find(username, query) -- luacheck: ignore 212/self query
	if self.store == "archive" then
		local jid = username.."@"..host;
		local data = datamanager.load(username, host, "archiving");
		return parse_logs(data["logs"], jid);

	elseif self.store:sub(1, 4) == "pep_" then
		local node = self.store:sub(5);

		local pep_base_path = datamanager.getpath(username, host, "pep"):sub(1, -5);
		local path = ("%s/%s.dat"):format(pep_base_path, encode(node));
		local get_data = envloadfile(path, {});
		if not get_data then
			module:log("debug", "Failed to load metronome storage");
			return {};
		end
		local success, data = pcall(get_data);
		if not success then
			module:log("error", "Unable to load metronome storage");
			return nil, "Error reading storage";
		end

		local iter = pairs(data["data"]);
		local key = nil;
		local payload;
		return function()
			key, payload = iter(data["data"], key);
			if not key then
				return;
			end
			local item = st.deserialize(payload[1]);
			local with = data["data_author"][key];
			return key, item, time_now, with;
		end;

	elseif self.store == "offline" then
		-- This is mostly copy/pasted from mod_storage_internal.
		local list, err = datamanager.list_open(username, host, self.store);
		if not list then
			if err then
				return list, err;
			end
			return function()
			end;
		end

		local i = 0;
		local iter = function()
			i = i + 1;
			return list[i];
		end

		return function()
			local item = iter();
			if item == nil then
				if list.close then
					list:close();
				end
				return
			end
			local key = gen_id();
			local when = item.attr and datetime.parse(item.attr.stamp);
			local with = "";
			item.key, item.when, item.with = nil, nil, nil;
			item.attr.stamp = nil;
			-- COMPAT Stored data may still contain legacy XEP-0091 timestamp
			item.attr.stamp_legacy = nil;
			item = st.deserialize(item);
			return key, item, when, with;
		end

	elseif self.store == "uploads" then
		local list = {};

		for user in datamanager.users(host, "http_upload", "list") do
			local data, err = datamanager.list_open(user, host, "http_upload");
			if not data then
				if err then
					return data, err;
				end
				return function()
				end;
			end

			for _, stuff in ipairs(data) do
				local key = stuff.dir;
				local size = tostring(stuff.size);
				local time = stuff.time;
				local filename = stuff.filename;
				local ext = filename:match(".*%.(%S+)"):lower();
				local mime = mimes[ext] or "application/octet-stream";
				local stanza = st.stanza("request", { xmlns = "urn:xmpp:http:upload:0", size = size, ["content-type"] = mime, filename = filename })
				list[key] = {user.."@"..host, time, stanza};
			end
		end

		local iter = pairs(list);
		local key = nil;
		local payload;
		return function()
			key, payload = iter(list, key);
			if not key then
				return;
			end
			local with = payload[1];
			local when = payload[2];
			local stanza = payload[3];
			return key, stanza, when, with;
		end;

	elseif self.store == "muc_log" then
		local base_path = datamanager.getpath("", host, "stanza_log"):sub(1, -5);
		local days = {};
		for date in dir(base_path) do
			if date ~= "." and date ~= ".." then
				table.insert(days, date);
			end
		end
		table.sort(days);
		local list = {};
		for _, date in ipairs(days) do
			local path = base_path..date.."/"..encode(username)..".dat";
			local get_data = envloadfile(path, {});
			if get_data then
				local success, data = pcall(get_data);
				if not success then
					module:log("error", "Unable to load metronome storage");
					return nil, "Error reading storage";
				end
				for key, item, when in parse_logs(data) do
					table.insert(list, {key, item, when});
				end
			end
		end

		local i = 0;
		local iter = function()
			i = i + 1;
			return list[i];
		end

		return function()
			local item = iter();
			if item == nil then
				if list.close then
					list:close();
				end
				return
			end
			return item[1], item[2], item[3], "message<groupchat"
		end

	else
		return nil, "unsupported-store";
	end
end

function archive:get(username, wanted_key)
	local iter, err = self:find(username, { key = wanted_key })
	if not iter then return iter, err; end
	for key, stanza, when, with in iter do
		if key == wanted_key then
			return stanza, when, with;
		end
	end
	return nil, "item-not-found";
end

function archive:set(username, key, new_value, new_when, new_with) -- luacheck: ignore 212/self username key new_value new_when new_with
	return nil, "unsupported-store";
end

function archive:dates(username) -- luacheck: ignore 212/self username
	return nil, "unsupported-store";
end

function archive:summary(username, query) -- luacheck: ignore 212/self username query
	return nil, "unsupported-store";
end

function archive:users()
	if self.store == "archive" then
		return datamanager.users(host, "archiving");
	elseif self.store:sub(1, 4) == "pep_" then
		local wanted_node = self.store:sub(5);
		local iter, tbl = datamanager.users(host, "pep");
		return function()
			while true do
				local user = iter(tbl);
				if not user then
					return;
				end
				local data = datamanager.load(user, host, "pep");
				for _, node in ipairs(data["nodes"]) do
					if node == wanted_node then
						return user;
					end
				end
			end
		end;
	elseif self.store == "offline" then
		return datamanager.users(host, self.store, "list");
	elseif self.store == "uploads" then
		local done = false;
		return function()
			if not done then
				done = true;
				return "";
			end
		end;
	elseif self.store == "muc_log" then
		local iter, tbl = pairs(datamanager.load(nil, host, "persistent"));
		local jid = nil;
		return function()
			jid = iter(tbl, jid);
			if not jid then
				return;
			end
			local user = jid:gsub("@.*", "");
			return user;
		end;
	else
		return nil, "unsupported-store";
	end
end

function archive:trim(username, to_when) -- luacheck: ignore 212/self username to_when
	return nil, "unsupported-store";
end

function archive:delete(username, query) -- luacheck: ignore 212/self username query
	return nil, "unsupported-store";
end

module:provides("storage", driver);
