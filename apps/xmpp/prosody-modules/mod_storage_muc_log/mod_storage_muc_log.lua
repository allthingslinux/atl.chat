-- luacheck: ignore 212/self 431/err 131/open

local datamanager = require"core.storagemanager".olddm;
local xml_parse = require"util.xml".parse;
local data_load, data_store = datamanager.load, datamanager.store;
local datastore = "muc_log";
local datetime = require"util.datetime"
local lfs = require"lfs";
local os_date = os.date;

local timef, datef = "!%H:%M:%S", "!%y%m%d";
local host = module.host;

local driver = {};
local driver_mt = { __index = driver };

do
	-- Sanity check
	-- Fun fact: 09:00 and 21:00 en_HK are both "09:00:00 UTC"
	local t = os_date("!*t");
	t.hour = 9;
	local am = os_date("!%X", os.time(t));
	t.hour = 21;
	local pm = os_date("!%X", os.time(t));
	if am == pm then
		module:log("warn", "Timestamps in AM and PM are identical in your locale, expect timestamps to be wrong");
	end
	if os_date("!%X", os.time(t)) ~= os_date(timef, os.time(t)) then
		module:log("warn", "Timestamp format differ from what mod_muc_log used, this module may not work correctly");
	end
end

local function parse_silly(date, time)
	local year, month, day = date:match("^(%d%d)(%d%d)(%d%d)");
	year = "20"..year;
	-- year = (year < "70" and "20" or "19") .. year;
	local hour, min, sec = time:match("(%d%d)%D+(%d%d)%D+(%d%d)");
	if hour == "12" and time:find("[Aa][Mm]") then
		hour = "00";
	elseif hour < "12" and time:find("[Pp][Mm]") then
		hour = tostring(tonumber(hour) % 12 + 12);
	end
	return datetime.parse(("%s-%s-%sT%s:%s:%sZ"):format(year, month, day, hour or "00", min or "00", sec or "00"));
end

local function st_with(tag)
	local with = tag.attr.type;
	return with and tag.name .. "<" .. with or tag.name;
end

function driver:append(node, key, stanza, when, with) -- luacheck: ignore 212/key
	-- luacheck: ignore 311/with
	-- 'with' doesn't exist in the original mod_muc_log, so gets derived here
	if type(when) ~= "number" then
		when, with, stanza = stanza, when, with;
	end
	local today = os_date(datef, when);
	local now = os_date(timef, when);
	local data = data_load(node, host, datastore .. "/" .. today) or {};
	data[#data + 1] = "<stanza time=\"".. now .. "\">" .. tostring(stanza) .. "</stanza>\n";
	datamanager.getpath(node, host, datastore, nil, true); -- create the datastore dir
	local ok, err = data_store(node, host, datastore .. "/" .. today, data);
	if not ok then
		return ok, err;
	end
	return today .. "_" .. #data;
end

function driver:dates(node)
	local path = datamanager.getpath(node, host, datastore):match("(.*)/");

	local ok, iter, state, var = pcall(lfs.dir, path);
	if not ok then
		module:log("warn", iter);
		return nil, iter;
	end

	local dates, i = {}, 1;
	for dir in iter, state, var do
		if lfs.attributes(datamanager.getpath(node, host, datastore .. "/" .. dir), "mode") == "file" then
			dates[i], i = dir, i+1;
		end
	end
	if dates[1] == nil then return nil end
	table.sort(dates);
	return dates;
end

function driver:find(node, query)
	local dates, err = self:dates(node);
	if not dates then return dates, err; end

	return coroutine.wrap(function ()
		local start_date = query and query.start and os_date(datef, query.start) or dates[1];
		local end_date = query and query["end"] and os_date(datef, query["end"]) or dates[#dates];
		local start_time = query and query.start and os_date(timef, query.start) or dates[1];
		local end_time = query and query["end"] and os_date(timef, query["end"]) or dates[#dates];
		local query_with = query and query.with;
		local query_limit = query and query.limit;
		local seek_once = query and query.after;

		local today, time, data, err, item;
		local inner_start, inner_stop, inner_step;
		local outer_start, outer_stop, outer_step = 1, #dates, 1;
		if query and query.reverse then
			outer_start, outer_stop, outer_step = outer_stop, outer_start, -outer_step;
			seek_once = query.before;
			if seek_once then
				end_date = seek_once:match"^(%d+)_%d";
			end
		elseif seek_once then
			start_date = seek_once:match"^(%d+)_%d";
		end
		local matches = 0;
		for i = outer_start, outer_stop, outer_step do
			today = dates[i];
			if today >= start_date and today <= end_date then
				data, err = data_load(node, host, datastore .. "/" .. today);
				if data then
					inner_start, inner_stop, inner_step = 1, #data, 1;
					if query and query.reverse then
						inner_start, inner_stop, inner_step = inner_stop, inner_start, -inner_step;
					end
					if seek_once then
						inner_start = tonumber(seek_once:match("_(%d+)$"));
						inner_start = inner_start + (query and query.reverse and -1 or 1);
						seek_once = nil;
					end
					for i = inner_start, inner_stop, inner_step do -- luacheck: ignore 423/i
						item, err = data[i], nil;
						if item then
							item, err = xml_parse(item);
						end
						if item then
							time = item.attr.time;
							item = item.tags[1];
							local with = st_with(item);
							if (today >= start_date or time >= start_time) and
								(today <= end_date or time <= end_time) and
								(not query_with or query_with == with) and
								item:get_child_text("alreadyJoined") ~= "true" then
								matches = matches + 1;
								coroutine.yield(today.."_"..i, item, parse_silly(today, time), with);
								if query_limit and matches >= query_limit then
									return;
								end
							end
						elseif err then
							module:log("warn", err);
						end
					end
				elseif err then
					module:log("warn", err);
				end
			end
		end
	end);
end

function open(_, store, typ)
	if typ ~= "archive" then
		return nil, "unsupported-store";
	end
	return setmetatable({ store = store, type = typ }, driver_mt);
end

module:provides "storage";
