local mt = require"util.multitable";
local datetime = require"util.datetime";
local jid_split = require"util.jid".split;
local nodeprep = require"util.encodings".stringprep.nodeprep;
local url = require"socket.url";
local os_time, os_date = os.time, os.date;
local httplib = require "util.http";
local render_funcs = {};
local render = require"util.interpolation".new("%b{}", require"util.stanza".xml_escape, render_funcs);

local archive = module:open_store("muc_log", "archive");

-- Prosody 0.11+ MUC API
local mod_muc = module:depends"muc";
local each_room = mod_muc.each_room;
local get_room_from_jid = mod_muc.get_room_from_jid;

local function get_room(name)
	local jid = name .. '@' .. module.host;
	return get_room_from_jid(jid);
end

local use_oob = module:get_option_boolean(module.name .. "_show_images", false);
module:depends"http";

local template;
do
	local template_filename = module:get_option_string(module.name .. "_template", "res/" .. module.name .. ".html");
	local template_file, err = module:load_resource(template_filename);
	if template_file then
		template, err = template_file:read("*a");
		template_file:close();
	end
	if not template then
		module:log("error", "Error loading template: %s", err);
		template = render("<h1>mod_{module} could not read the template</h1>\
		<p>Tried to open <b>{filename}</b></p>\
		<pre>{error}</pre>",
			{ module = module.name, filename = template_filename, error = err });
	end
end

local resources = module:get_option_path(module.name .. "_resources", "static");

-- local base_url = module:http_url() .. '/'; -- TODO: Generate links in a smart way
local get_link do
	local link, path = { path = '/' }, { "", "", is_directory = true };
	function get_link(room, date)
		path[1], path[2] = room, date;
		path.is_directory = not date;
		link.path = url.build_path(path);
		return url.build(link);
	end
end

local function get_absolute_link(room, date)
	local link = url.parse(module:http_url());
	local path = url.parse_path(link.path);
	if room then
		table.insert(path, room);
		if date then
			table.insert(path, date)
			path.is_directory = false;
		else
			path.is_directory = true;
		end
	end
	link.path = url.build_path(path)
	return url.build(link)
end

-- Whether room can be joined by anyone
local function open_room(room) -- : boolean
	if type(room) == "string" then
		room = get_room(room);
		-- assumed to be a room object otherwise
	end
	if not room then
		return nil;
	end

	if room:get_members_only() then
		return false;
	end

	if room:get_password() then
		return false;
	end

	return true;
end

-- Can be set to "latest"
local default_view = module:get_option_string(module.name .. "_default_view", nil);

module:hook("muc-disco#info", function (event)
	local room = event.room;
	if open_room(room) then
		table.insert(event.form, { name = "muc#roominfo_logs", type="text-single" });
		event.formdata["muc#roominfo_logs"] = get_absolute_link(jid_split(event.room.jid), default_view);
	end
end);

local function sort_Y(a,b) return a.year > b.year end
local function sort_m(a,b) return a.n > b.n end

-- Time zone hack?
local t_diff = os_time(os_date("*t")) - os_time(os_date("!*t"));
local function time(t)
	return os_time(t) + t_diff;
end
local function date_floor(t)
	return t - t % 86400;
end

-- Fetch one item
local function find_once(room, query, retval)
	if query then query.limit = 1; else query = { limit = 1 }; end
	local iter, err = archive:find(room, query);
	if not iter then return iter, err; end
	if retval then
		return select(retval, iter());
	end
	return iter();
end

local lazy = module:get_option_boolean(module.name .. "_lazy_calendar", true);

local presence_logged = module:get_option_boolean("muc_log_presences", false);

local function show_presence(request) --> boolean|nil
	-- boolean -> yes or no
	-- nil -> dunno
	if not presence_logged then
		-- No presence stored, skip
		return nil;
	end
	if request.url.query then
		local data = httplib.formdecode(request.url.query);
		if type(data) == "table" then
			if data.p == "s" or data.p == "h" then
				return data.p == "s";
			end
		end
	end
end

local function presence_with(request)
	local show = show_presence(request);
	if show == true then
		return nil; -- no filter, everything
	elseif show == false or show == nil then
		-- only messages
		return "message<groupchat";
	end
end

local function presence_query(request) -- > ?p=[sh]
	local show = show_presence(request);
	if show == true then
		return { p = "s" }
	elseif show == false then
		return { p = "h" }
	else
		return nil;
	end
end

local function get_dates(room) --> { integer, ... }
	local date_list = archive.dates and archive:dates(room);
	if date_list then
		for i = 1, #date_list do
			date_list[i] = datetime.parse(date_list[i].."T00:00:00Z");
		end
		return date_list;
	end

	if lazy then
		-- Lazy with many false positives
		date_list = {};
		local first_day = find_once(room, nil, 3);
		local last_day = find_once(room, { reverse = true }, 3);
		if first_day and last_day then
			first_day = date_floor(first_day);
			last_day = date_floor(last_day);
			for when = first_day, last_day, 86400 do
				table.insert(date_list, when);
			end
		else
			return; -- 404
		end
		return date_list;
	end

	-- Collect date the hard way
	module:log("debug", "Find all dates with messages");
	date_list = {};
	local next_day;
	repeat
		local when = find_once(room, { start = next_day; }, 3);
		if not when then break; end
		table.insert(date_list, when);
		next_day = date_floor(when) + 86400;
	until not next_day;
	return date_list;
end

function render_funcs.calendarize(date_list)
	-- convert array of timestamps to a year / month / day tree
	local dates = mt.new();
	for _, when in ipairs(date_list) do
		local t = os_date("!*t", when);
		dates:set(t.year, t.month, t.day, when);
	end
	-- Wrangle Y/m/d tree into year / month / week / day tree for calendar view
	local years = {};
	for current_year, months_t in pairs(dates.data) do
		local t = { year = current_year, month = 1, day = 1 };
		local months = { };
		local year = { year = current_year, months = months };
		years[#years+1] = year;
		for current_month, days_t in pairs(months_t) do
			t.day = 1;
			t.month = current_month;
			local tmp = os_date("!*t", time(t));
			local days = {};
			local week = { days = days }
			local weeks = { week };
			local month = { year = year.year, month = os_date("!%B", time(t)), n = current_month, weeks = weeks };
			months[#months+1] = month;
			local current_day = 1;
			for _=1, (tmp.wday+5)%7 do
				days[current_day], current_day = {}, current_day+1;
			end
			for i = 1, 31 do
				t.day = i;
				tmp = os_date("!*t", time(t));
				if tmp.month ~= current_month then break end
				if i > 1 and tmp.wday == 2 then
					days = {};
					weeks[#weeks+1] = { days = days };
					current_day = 1;
				end
				days[current_day] = {
					wday = tmp.wday, day = i, href = days_t[i] and datetime.date(days_t[i])
				};
				current_day = current_day+1;
			end
		end
		table.sort(months, sort_m);
	end
	table.sort(years, sort_Y);
	return years;
end

-- Produce the calendar view
local function years_page(event, path)
	local request, response = event.request, event.response;

	local room = nodeprep(path:match("^(.*)/$"));
	local is_open = open_room(room);
	if is_open == nil then
		return -- implicit 404
	elseif is_open == false then
		return 403;
	end

	local date_list = get_dates(room);
	if not date_list then
		return; -- 404
	end

	-- Phew, all wrangled, all that's left is rendering it with the template

	response.headers.content_type = "text/html; charset=utf-8";
	local room_obj = get_room(room);
	return render(template, {
		static = "../@static";
		room = room_obj._data;
		jid = room_obj.jid;
		jid_node = jid_split(room_obj.jid);
		q = presence_query(request);
		show_presence = show_presence(request);
		presence_available = presence_logged;
		dates = date_list;
		links = {
			{ href = "../", rel = "up", text = "Room list" },
			{ href = "latest", rel = "last", text = "Latest" },
		};
	});
end

-- Produce the chat log view
local function logs_page(event, path)
	local request, response = event.request, event.response;

	-- /room --> 303 /room/
	-- /room/ --> calendar view
	-- /room/yyyy-mm-dd --> logs view
	-- /room/yyyy-mm-dd/* --> 404
	local room, date = path:match("^([^/]+)/([^/]*)$");
	if not room and not path:find"/" then
		response.headers.location = url.build({ path = path .. "/" });
		return 303;
	elseif not room then
		return 404;
	end
	room = nodeprep(room);
	if not room then
		return 400;
	elseif date == "" then
		return years_page(event, path);
	end
	local is_open = open_room(room);
	if is_open == nil then
		return -- implicit 404
	elseif is_open == false then
		return 403;
	end
	if date == "latest" then
		local last_day = find_once(room, { reverse = true }, 3);
		response.headers.location = url.build({ path = datetime.date(last_day), query = request.url.query });
		return 303;
	end
	local day_start = datetime.parse(date.."T00:00:00Z");
	if not day_start then
		module:log("debug", "Invalid date format: %q", date);
		return 400;
	end

	local logs, i = {}, 1;
	local iter, err = archive:find(room, {
		["start"] = day_start;
		["end"]   = day_start + 86399;
		["with"]  = presence_with(request);
	});
	if not iter then
		module:log("warn", "Could not search archive: %s", err or "no error");
		return 500;
	end

	local first, last;
	for archive_id, item, when in iter do
		local body_tag = item:get_child("body");
		local body = body_tag and body_tag:get_text();
		local subject = item:get_child_text("subject");
		local verb = nil;
		local lang = body_tag and body_tag.attr["xml:lang"] or item.attr["xml:lang"];

		-- XEP-0359: Unique and Stable Stanza IDs
		local message_id = item:find("{urn:xmpp:sid:0}origin-id@id") or item.attr.id;

		if subject then
			verb, body = "set the topic to", subject;
		elseif body and body:sub(1,4) == "/me " then
			verb, body = body:sub(5), nil;
		elseif item.name == "presence" then
			-- TODO Distinguish between join and presence update
			verb = item.attr.type == "unavailable" and "has left" or "has joined";
			lang = "en";
		end

		local nick = select(3, jid_split(item.attr.from));
		local occupant_id = item:find("{urn:xmpp:occupant-id:0}occupant-id@id") or nick;

		-- XEP-0066: Out of Band Data
		local oob = use_oob and item:get_child("x", "jabber:x:oob");

		-- XEP-0425: Message Moderation
		local moderated = item:get_child("moderated", "urn:xmpp:message-moderate:0");
		if moderated then
			local actor = moderated.attr.by;
			if actor then actor = select(3, jid_split(actor)); end
			verb = "removed by " .. (actor or "moderator");
			body = moderated:get_child_text("reason") or "";
		end

		local moderation = item:find("{urn:xmpp:fasten:0}apply-to/{urn:xmpp:message-moderate:0}moderated");
		if moderation then
			nick = nick or "a moderator";
			verb = "removed a message";
			body = moderation:get_child_text("reason") or "";
		end

		-- XEP-0308: Last Message Correction
		local edit = item:find("{urn:xmpp:message-correct:0}replace/@id");
		if edit then
			local found = false;
			for n = i-1, 1, -1 do
				if logs[n].message_id == edit and occupant_id == logs[n].occupant_id then
					found = true;
					logs[n].edited = archive_id;
					edit = logs[n].archive_id;
					break;
				end
			end
			if not found then
				-- Ignore unresolved edit.
				edit = nil;
			end
		end

		-- XEP-0444: Message Reactions
		local reactions = item:get_child("reactions", "urn:xmpp:reactions:0");
		if reactions then
			-- COMPAT Movim uses an @to attribute instead of the correct @id
			local target_id = reactions.attr.id or reactions.attr.to;
			for n = i - 1, 1, -1 do
				if logs[n].archive_id == target_id then
					local react_map = logs[n].reactions; -- [occupant_id][emoji]boolean
					if not react_map then
						react_map = {};
						logs[n].reactions = react_map;
					end
					local reacts = {};
					for reaction_tag in reactions:childtags("reaction") do
						local reaction_text = reaction_tag:get_text() or "�";
						reacts[reaction_text] = true;
					end
					react_map[occupant_id] = reacts;
					break
				end
			end
		end

		-- XEP-0461: Message Replies
		local reply = item:find("{urn:xmpp:reply:0}reply@id");

		if body or verb or oob then
			local line = {
				message_id = message_id;
				archive_id = archive_id;
				occupant_id = occupant_id;
				datetime = datetime.datetime(when);
				time = datetime.time(when);
				verb = verb;
				body = body;
				lang = lang;
				nick = nick;
				st_name = item.name;
				st_type = item.attr.type;
				edit = edit;
				reply = reply;
				-- COMPAT
				key = archive_id;
			};
			if oob then
				line.oob = {
					url = oob:get_child_text("url");
					desc = oob:get_child_text("desc");
				}
			end
			logs[i], i = line, i + 1;
		end

		first = first or archive_id;
		last = archive_id;
	end
	if i == 1 and not lazy then return end -- No items

	-- collapse reactions[occupant-id][reaction]boolean into reactions[reaction]integer
	for n = 1, #logs do
		local reactions = logs[n].reactions;
		if reactions then
			local collated = {};
			for _, reacts in pairs(reactions) do
				for reaction_text in pairs(reacts) do
					collated[reaction_text] = (collated[reaction_text] or 0) + 1;
				end
			end
			logs[n].reactions = collated;
		end
	end

	local next_when, prev_when = "", "";
	local date_list = archive.dates and archive:dates(room);
	if date_list then
		for j = 1, #date_list do
			if date_list[j] == date then
				next_when = date_list[j+1] or "";
				prev_when = date_list[j-1] or "";
				break;
			end
		end
	elseif lazy then
		next_when = datetime.date(day_start + 86400);
		prev_when = datetime.date(day_start - 86400);
	elseif first and last then

		module:log("debug", "Find next date with messages");
		next_when = find_once(room, { after = last }, 3);
		if next_when then
			next_when = datetime.date(next_when);
			module:log("debug", "Next message: %s", next_when);
		end

		module:log("debug", "Find prev date with messages");
		prev_when = find_once(room, { before = first, reverse = true }, 3);
		if prev_when then
			prev_when = datetime.date(prev_when);
			module:log("debug", "Previous message: %s", prev_when);
		end
	end

	local links = {
		{ href = "../", rel = "up", text = "Room list" },
		{ href = "./", rel = "up", text = "Calendar" },
	};
	if prev_when ~= "" then
		table.insert(links, { href = prev_when, rel = "prev", text = prev_when});
	end
	if next_when ~= "" then
		table.insert(links, { href = next_when, rel = "next", text = next_when});
	end

	response.headers.content_type = "text/html; charset=utf-8";
	local room_obj = get_room(room);
	return render(template, {
		static = "../@static";
		date = date;
		room = room_obj._data;
		jid = room_obj.jid;
		jid_node = jid_split(room_obj.jid);
		q = presence_query(request);
		show_presence = show_presence(request);
		presence_available = presence_logged;
		lang = room_obj.get_language and room_obj:get_language();
		lines = logs;
		links = links;
		dates = {}; -- COMPAT util.interpolation {nil|func#...} bug
	});
end

local room_weights = setmetatable(module:get_option_array(module.name.."_list_order", {}):reverse(), nil);
for i = #room_weights, 1, -1 do
	local room_jid = room_weights[i];
	room_weights[i] = nil;
	room_weights[room_jid] = i;
end

local function list_rooms(event)
	local request, response = event.request, event.response;
	local room_list, i = {}, 1;
	for room in each_room() do
		if room:get_public() then
			local localpart = jid_split(room.jid);
			room_list[i], i = {
				jid = room.jid;
				localpart = localpart;
				href = get_link(localpart, default_view);
				name = room:get_name() or localpart;
				lang = room.get_language and room:get_language();
				description = room:get_description();
				priority = room_weights[ room.jid ] or 0;
			}, i + 1;
		end
	end

	table.sort(room_list, function (a, b)
		if a.priority ~= b.priority then return a.priority > b.priority; end
		if a.description ~= nil and b.description == nil then
			return true;
		elseif a.description == nil and b.description ~= nil then
			return false;
		end
		return a.jid < b.jid;
	end);

	response.headers.content_type = "text/html; charset=utf-8";
	return render(template, {
		static = "./@static";
		title = module:get_option_string("name", "Prosody Chatrooms");
		jid = module.host;
		q = presence_query(request);
		show_presence = show_presence(request);
		presence_available = presence_logged;
		rooms = room_list;
		dates = {}; -- COMPAT util.interpolation {nil|func#...} bug
	});
end

local serve_static
do
	local http_files = require "net.http.files";
	local mime_map = module:shared("/*/http_files/mime").types or { css = "text/css"; js = "application/javascript" };
	serve_static = http_files.serve({ path = resources; mime_map = mime_map });
end

module:provides("http", {
	title = module:get_option_string("name", "Chatroom logs");
	route = {
		["GET /"] = list_rooms;
		["GET /*"] = logs_page;
		-- mod_http only supports one wildcard so logs_page will dispatch to years_page if the path contains no date
		-- thus:
		-- GET /room --> years_page (via logs_page)
		-- GET /room/yyyy-mm-dd --> logs_page (for real)

		["GET /@static/*"] = serve_static;
		-- There are not many ASCII characters that are safe to use in URLs but not
		-- valid in JID localparts, '@' seemed the only option.
	};
});

