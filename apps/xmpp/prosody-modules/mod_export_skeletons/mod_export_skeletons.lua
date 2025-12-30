
local t_insert = table.insert;
local t_sort = table.sort;

local sm = require "core.storagemanager";
local um = require "core.usermanager";

local argparse = require "util.argparse";
local dt = require "util.datetime";
local jid = require "util.jid";
local st = require "util.stanza";

local function skeleton(s)
	local o = st.stanza(s.name, { xmlns = s.attr.xmlns });

	local children = {};
	for _, child in ipairs(s.tags) do t_insert(children, skeleton(child)) end
	t_sort(children, function(a, b)
		if a.attr.xmlns == b.attr.xmlns then return a.name < b.name; end
		return (a.attr.xmlns or "") < (b.attr.xmlns or "");
	end);
	for _, child in ipairs(children) do o:add_direct_child(child); end
	return o;
end

local function classify_jid(s)
	if not s then return "" end
	local u, h, r = jid.split(s);
	if r then
		return "full"
	elseif u then
		return "bare"
	elseif h then
		return "host"
	else
		return "invalid"
	end
end

function module.command(arg)
	local opts = argparse.parse(arg, { value_params = { store = true; with = true; start = true; ["end"] = true } });
	local store = opts.store or "archive"; -- so you can pass 'archive2'
	opts.store = nil;
	local query = { with = jid.prep(opts.with); start = dt.parse(opts.start); ["end"] = dt.parse(opts["end"]) };
	local host_initialized = {};
	for _, export_jid in ipairs(arg) do

		local username, host = jid.split(export_jid);
		if not host_initialized[host] then
			sm.initialize_host(host);
			um.initialize_host(host);
			host_initialized[host] = true;
		end

		local archive = module:context(host):open_store(store, "archive");
		local iter, total = assert(archive:find(username, query))
		if total then io.stderr:write(string.format("Processing %d entries\n", total)); end
		for _, item in iter do
			local clean = skeleton(item);

			-- Normalize top level attributes
			clean.attr.type = item.attr.type;
			if clean.attr.type == nil and clean.name == "message" then clean.attr.type = "normal"; end
			clean.attr.id = string.rep("x", math.floor(math.log(1+#(item.attr.id or ""), 2)));
			clean.attr.from = classify_jid(item.attr.from);
			clean.attr.to = classify_jid(item.attr.to);
			print(clean);
		end

	end
end
