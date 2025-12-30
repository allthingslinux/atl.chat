local lfs = require "lfs";

local adns = require "net.adns";
local it = require "util.iterators";
local parse_cidr = require "util.ip".parse_cidr;
local parse_ip = require "util.ip".new_ip;
local promise = require "util.promise";
local set = require "util.set";
local st = require "util.stanza";

local render_message = require "util.interpolation".new("%b{}", function (s)
	return s;
end);

local trie = module:require("mod_anti_spam/trie");

local dnsbls_config_raw = module:get_option("dnsbls");
local default_dnsbl_flag = module:get_option_string("dnsbl_flag", "dnsbl_hit");
local default_dnsbl_message = module:get_option("dnsbl_message");

if not dnsbls_config_raw then
	module:log_status("error", "No 'dnsbls' in config file");
	return;
end

local dnsbls = set.new();
local dnsbls_config = {};

for k, v in ipairs(dnsbls_config_raw) do
	local dnsbl_name, dnsbl_config;
	if type(k) == "string" then
		dnsbl_name = k;
		dnsbl_config = v;
	else
		dnsbl_name = v;
		dnsbl_config = {};
	end
	dnsbls:add(dnsbl_name);
	dnsbls_config[dnsbl_name] = dnsbl_config;
end

local function read_dnsbl_file(filename)
	local t = trie.new();
	local f, err = io.open(filename);
	if not f then
		module:log("error", "Failed to read file: %s", err);
		return t;
	end

	local n_line, n_added = 0, 0;
	for line in f:lines() do
		n_line = n_line + 1;
		line = line:gsub("#.+$", ""):match("^%s*(.-)%s*$");
		if line == "" then -- luacheck: ignore 542
			-- Skip
		else
			local parsed_ip, parsed_bits = parse_cidr(line);
			if not parsed_ip then
				-- Skip
				module:log("warn", "Failed to parse IP/CIDR on %s:%d", filename, n_line);
			else
				if not parsed_bits then
					-- Default to full length of IP address
					parsed_bits = #parsed_ip.packed * 8;
				end
				t:add_subnet(parsed_ip, parsed_bits);
				n_added = n_added + 1;
			end
		end
	end

	module:log("info", "Loaded %d entries from %s", n_added, filename);

	return t;
end

local ipsets = {};
local ipsets_last_updated = {};

function reload_file_dnsbls()
	for dnsbl in dnsbls do
		if dnsbl:byte(1) == 64 then -- '@'
			local filename = dnsbl:sub(2);
			local file_last_updated = lfs.attributes(filename, "change");
			if (ipsets_last_updated[dnsbl] or 0) < file_last_updated then
				ipsets[dnsbl] = read_dnsbl_file(filename);
				ipsets_last_updated[dnsbl] = file_last_updated;
			end
		end
	end
end

module:hook_global("config-reloaded", reload_file_dnsbls);
reload_file_dnsbls();

local mod_flags = module:depends("flags");

local function reverse(ip, suffix)
	local a,b,c,d = ip:match("^(%d+).(%d+).(%d+).(%d+)$");
	if not a then return end
	return ("%d.%d.%d.%d.%s"):format(d,c,b,a, suffix);
end

function check_dnsbl(ip_address, dnsbl, callback, ud)
	if dnsbl:byte(1) == 64 then -- '@'
		local parsed_ip = parse_ip(ip_address);
		if not parsed_ip then
			module:log("warn", "Failed to parse IP address: %s", ip_address);
			callback(ud, false, dnsbl);
			return;
		end
		callback(ud, not not ipsets[dnsbl]:contains_ip(parsed_ip), dnsbl);
		return;
	else
		if ip_address:sub(1,7):lower() == "::ffff:" then
			ip_address = ip_address:sub(8);
		end

		local rbl_ip = reverse(ip_address, dnsbl);
		if not rbl_ip then return; end

		module:log("debug", "Sending DNSBL lookup for %s", ip_address);
		adns.lookup(function (reply)
			local hit = not not (reply and reply[1]);
			module:log("debug", "Received DNSBL result for %s: %s", ip_address, hit and "present" or "absent");
			callback(ud, hit, dnsbl);
		end, rbl_ip);
	end
end

local function handle_dnsbl_register_result(registration_event, hit, dnsbl)
	if not hit then return; end

	if registration_event.dnsbl_match then return; end
	registration_event.dnsbl_match = true;

	local username = registration_event.username;
	local flag = dnsbls_config[dnsbl].flag or default_dnsbl_flag;

	module:log("info", "Flagging %s for user %s registered from %s matching %s", flag, username, registration_event.ip, dnsbl);

	mod_flags:add_flag(username, flag, "Matched "..dnsbl);

	local msg = dnsbls_config[dnsbl].message or default_dnsbl_message;

	if msg then
		module:log("debug", "Sending warning message to %s", username);
		local msg_stanza = st.message(
			{
				to = username.."@"..module.host;
				from = module.host;
			},
			render_message(msg, { registration = registration_event })
		);
		module:send(msg_stanza);
	end
end

module:hook("user-registered", function (event)
	local session = event.session;
	local ip = event.ip or (session and session.ip);
	if not ip then return; end

	if not event.ip then
		event.ip = ip;
	end

	for dnsbl in dnsbls do
		check_dnsbl(ip, dnsbl, handle_dnsbl_register_result, event);
	end
end);

module:add_item("account-trait", {
	name = "register-dnsbl-hit";
	prob_bad_true = 0.6;
	prob_bad_false = 0.4;
});

module:hook("get-account-traits", function (event)
	event.traits["register-dnsbl-hit"] = mod_flags.has_flag(event.username, default_dnsbl_flag);
end);

module:add_item("shell-command", {
	section = "dnsbl";
	section_desc = "Manage DNS blocklists";
	name = "lists";
	desc = "Show all lists currently in use on the specified host";
	args = {
		{ name = "host", type = "string" };
	};
	host_selector = "host";
	handler = function(self, host) --luacheck: ignore 212/self 212/host
		local count = 0;
		for list in dnsbls do
			count = count + 1;
			self.session.print(list);
		end
		return true, ("%d lists"):format(count);
	end;
});

module:add_item("shell-command", {
	section = "dnsbl";
	section_desc = "Manage DNS blocklists";
	name = "check";
	desc = "Check an IP against the configured block lists";
	args = {
		{ name = "host", type = "string" };
		{ name = "ip_address", type = "string" };
	};
	host_selector = "host";
	handler = function(self, host, ip_address) --luacheck: ignore 212/self 212/host
		local parsed_ip = parse_ip(ip_address);
		if not parsed_ip then
			return false, "Failed to parse IP address";
		end

		local matches, total = 0, 0;

		local promises = {};

		for dnsbl in dnsbls do
			total = total + 1;
			promises[dnsbl] = promise.new(function (resolve)
				check_dnsbl(parsed_ip, dnsbl, resolve, true);
			end);
		end

		return promise.all_settled(promises):next(function (results)
			for dnsbl, result in it.sorted_pairs(results) do
				local msg;
				if result.status == "fulfilled" then
					if result.value then
						msg = "[X]";
						matches = matches + 1;
					else
						msg = "[ ]";
					end
				else
					msg = "[?]";
				end

				print(msg, dnsbl);
			end
			return ("Found in %d of %d lists"):format(matches, total);
		end);
	end;
});
