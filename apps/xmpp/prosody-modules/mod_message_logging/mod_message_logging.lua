module:set_global();

local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;

local stat, mkdir = require "lfs".attributes, require "lfs".mkdir;

-- Get a filesystem-safe string
local function fsencode_char(c)
	return ("%%%02x"):format(c:byte());
end
local function fsencode(s)
	return (s:gsub("[^%w._-@]", fsencode_char):gsub("^%.", "_"));
end

local log_base_path = module:get_option("message_logging_dir", prosody.paths.data.."/message_logs");
mkdir(log_base_path);

local function get_host_path(host)
	return log_base_path.."/"..fsencode(host);
end

local function get_user_path(jid)
	local username, host = jid_split(jid);
	local base = get_host_path(host)..os.date("/%Y-%m-%d");
	if not stat(base) then
		mkdir(base);
	end
	return base.."/"..fsencode(username)..".msglog";
end

local open_files_mt = { __index = function (open_files, jid)
	local f, err = io.open(get_user_path(jid), "a+");
	if not f then
		module:log("error", "Failed to open message log for writing [%s]: %s", jid, err);
	end
	rawset(open_files, jid, f);
	return f;
end };

-- [user@host] = filehandle
local open_files = setmetatable({}, open_files_mt);

function close_open_files()
	module:log("debug", "Closing all open files");
	for jid, filehandle in pairs(open_files) do
		filehandle:close();
		open_files[jid] = nil;
	end
end
module:hook_global("logging-reloaded", close_open_files);

local function write_to_log(log_jid, jid, prefix, body)
	if not body then return; end
	local f = open_files[log_jid];
	if not f then return; end
	body = body:gsub("\n", "\n    "); -- Indent newlines
	f:write(os.date("%H:%M:%S "), prefix or "", prefix and ": " or "", jid, ": ", body, "\n");
	f:flush();
end

local function handle_incoming_message(event)
	local origin, stanza = event.origin, event.stanza;
	local message_type = stanza.attr.type;

	if message_type == "error" then return; end

	local from, to = jid_bare(stanza.attr.from), jid_bare(stanza.attr.to or stanza.attr.from);
	if message_type == "groupchat" then
		from = from.." <"..(select(3, jid_split(stanza.attr.from)) or "")..">";
	end
	write_to_log(to, from, "RECV", stanza:get_child_text("body"));
end

local function handle_outgoing_message(event)
	local origin, stanza = event.origin, event.stanza;
	local message_type = stanza.attr.type;

	if message_type == "error" then return; end

	local from, to = jid_bare(stanza.attr.from), jid_bare(stanza.attr.to or origin.full_jid);
	write_to_log(from, to, "SEND", stanza:get_child_text("body"));
end

local function handle_muc_message(event)
	local stanza = event.stanza;
	if stanza.attr.type ~= "groupchat" then return; end
	local room = event.room or hosts[select(2, jid_split(stanza.attr.to))].modules.muc.rooms[stanza.attr.to];
	if not room then return; end
	local nick = select(3, jid_split(room._jid_nick[stanza.attr.from]));
	if not nick then return; end
	write_to_log(room.jid, jid_bare(stanza.attr.from).." <"..nick..">", "MESG", stanza:get_child_text("body"));
end

function module.add_host(module)
	local host_base_path = get_host_path(module.host);
	if not stat(host_base_path) then
		mkdir(host_base_path);
	end

	if hosts[module.host].modules.muc then
		module:hook("message/bare", handle_muc_message, 1);
	else
		module:hook("message/bare", handle_incoming_message, 1);
		module:hook("message/full", handle_incoming_message, 1);
	
		module:hook("pre-message/bare", handle_outgoing_message, 1);
		module:hook("pre-message/full", handle_outgoing_message, 1);
		module:hook("pre-message/host", handle_outgoing_message, 1);
	end

end

function module.command(arg)
	local command = table.remove(arg, 1);
	if command == "path" then
		print(get_user_path(arg[1]));
	else
		io.stderr:write("Unrecognised command: ", command);
		return 1;
	end
	return 0;
end

function module.save()
	return { open_files = open_files };
end

function module.restore(saved)
	open_files = setmetatable(saved.open_files or {}, open_files_mt);
end
