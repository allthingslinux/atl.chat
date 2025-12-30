local it = require "util.iterators";
local http = require "util.http";
local sm = require "core.storagemanager";
local st = require "util.stanza";
local xml = require "util.xml";

local jid_join = require "util.jid".join;

local mod_pep = module:depends("pep");
local tokens = module:depends("tokenauth");
module:depends("storage_xep0227");

local archive_store_name = module:get_option("archive_store", "archive");

local known_stores = {
	accounts = "keyval";
	roster = "keyval";
	private = "keyval";
	pep = "keyval";
	vcard = "keyval";

	[archive_store_name] = "archive";
	pep_data = "archive";
};

local xmlns_pubsub = "http://jabber.org/protocol/pubsub";

local function new_user_xml(username, host)
	local user_xml = st.stanza("server-data", {xmlns='urn:xmpp:pie:0'})
		:tag("host", { jid = host })
			:tag("user", { name = username }):reset();

	return {
		set_user_xml = function (_, store_username, store_host, new_xml)
			if username ~= store_username or store_host ~= host then
				return nil;
			end
			user_xml = new_xml;
			return true;
		end;

		get_user_xml = function (_, store_username, store_host)
			if username ~= store_username or store_host ~= host then
				return nil;
			end
			return user_xml;
		end
	};
end

local function get_selected_stores(query_params)
	local selected_kv_stores, selected_archive_stores, export_pep_data = {}, {}, false;
	if query_params.stores then
		for store_name in query_params.stores:gmatch("[^,]+") do
			local store_type = known_stores[store_name];
			if store_type == "keyval" then
				table.insert(selected_kv_stores, store_name);
			elseif store_type == "archive" then
				if store_name == "pep_data" then
					export_pep_data = true;
				else
					table.insert(selected_archive_stores, store_name);
				end
			else
				module:log("warn", "Unknown store: %s", store_name);
				return 400;
			end
		end
	end
	return {
		keyval = selected_kv_stores;
		archive = selected_archive_stores;
		export_pep_data = export_pep_data;
	};
end

local function get_config_driver(store_name, host)
	-- Fiddling to handle the 'pep_data' storage config override
	if store_name:find("pep_", 1, true) == 1 then
		store_name = "pep_data";
	end
	-- Return driver
	return sm.get_driver(host, store_name);
end

local function handle_export_227(event)
	local session = assert(event.session, "No session found");
	local xep227_driver = sm.load_driver(session.host, "xep0227");

	local username = session.username;

	local user_xml = new_user_xml(session.username, session.host);

	local query_params = http.formdecode(event.request.url.query or "");

	local selected_stores = get_selected_stores(query_params);

	for store_name in it.values(selected_stores.keyval) do
		-- Open the source store that contains the data
		local store = sm.open(session.host, store_name);
		-- Read the current data
		local data, err = store:get(username);
		if data ~= nil or not err then
			-- Initialize the destination store (XEP-0227 backed)
			local target_store = xep227_driver:open_xep0227(store_name, nil, user_xml);
			-- Transform the data and update user_xml (via the _set_user_xml callback)
			if not target_store:set(username, data == nil and {} or data) then
				return 500;
			end
		elseif err then
			return 500;
		end
	end

	if selected_stores.export_pep_data then
		local pep_node_list = sm.open(session.host, "pep"):get(session.username);
		if pep_node_list then
			for node_name in it.keys(pep_node_list) do
				table.insert(selected_stores.archive, "pep_"..node_name);
			end
		end
	end

	for store_name in it.values(selected_stores.archive) do
		local source_driver = get_config_driver(store_name, session.host);
		local source_archive = source_driver:open(store_name, "archive");
		local dest_archive = xep227_driver:open_xep0227(store_name, "archive", user_xml);
		local results_iter, results_err = source_archive:find(username);
		if results_iter then
			local count, errs = 0, 0;
			for id, item, when, with in results_iter do
				local ok, err = dest_archive:append(username, id, item, when, with);
				if ok then
					count = count + 1;
				else
					module:log("warn", "Error: %s", err);
					errs = errs + 1;
				end
				if ( count + errs ) % 100 == 0 then
					module:log("info", "%d items migrated, %d errors", count, errs);
				end
			end
		elseif results_err then
			module:log("warn", "Unable to read from '%s': %s", store_name, results_err);
			return 500;
		end
	end

	local xml_data = user_xml:get_user_xml(username, session.host);

	if not xml_data or not xml_data:find("host/user") then
		module:log("warn", "No data to export: %s", tostring(xml_data));
		return 204;
	end

	event.response.headers["Content-Type"] = "application/xml";
	return [[<?xml version="1.0" encoding="utf-8" ?>]]..tostring(xml_data);
end

local function generic_keyval_importer(username, host, store_name, source_store)
	-- Read the current data
	local data, err = source_store:get(username);
	if data ~= nil or not err then
		local target_store = sm.open(host, store_name);
		-- Transform the data and update user_xml (via the _set_user_xml callback)
		if not target_store:set(username, data == nil and {} or data) then
			return 500;
		end
		module:log("debug", "Imported data for '%s' store", store_name);
	elseif err then
		return nil, err;
	else
		module:log("debug", "No data for store '%s'", store_name);
	end
	return true;
end

local function generic_archive_importer(username, host, store_name, source_archive)
	local dest_driver = get_config_driver(store_name, host);
	local dest_archive = dest_driver:open(store_name, "archive");
	local results_iter, results_err = source_archive:find(username);
	if results_iter then
		local count, errs = 0, 0;
		for id, item, when, with in source_archive:find(username) do
			local ok, err = dest_archive:append(username, id, item, when, with);
			if ok then
				count = count + 1;
			else
				module:log("warn", "Error: %s", err);
				errs = errs + 1;
			end
			if ( count + errs ) % 100 == 0 then
				module:log("info", "%d items migrated, %d errors", count, errs);
			end
		end
	elseif results_err then
		module:log("warn", "Unable to read from '%s': %s", store_name, results_err);
		return nil, "error reading from source archive";
	end
	return true;
end

local special_keyval_importers = {};

function special_keyval_importers.pep(username, host, store_name, store) --luacheck: ignore 212/store_name
	local user_jid = jid_join(username, host);
	local pep_service = mod_pep.get_pep_service(username);
	local pep_nodes, store_err = store:get(username);
	if not pep_nodes and store_err then
		return nil, store_err;
	end

	local all_ok = true;
	for node_name, node_config in pairs(pep_nodes) do
		local ok, ret = pep_service:get_node_config(node_name, user_jid);
		if not ok and ret == "item-not-found" then
			-- Create node according to imported data
			if node_config == true then node_config = {}; end
			local create_ok, create_err = pep_service:create(node_name, user_jid, node_config.config);
			if not create_ok then
				module:log("warn", "Failed to create PEP node: %s", create_err);
				all_ok = false;
			end
		end
	end

	return all_ok;
end

local special_archive_importers = setmetatable({}, {
	__index = function (t, k)
		if k:match("^pep_") then
			return t.pep_data;
		end
	end;
});

function special_archive_importers.pep_data(username, host, store_name, source_archive)
	local user_jid = jid_join(username, host);
	local pep_service = mod_pep.get_pep_service(username);

	local node_name = store_name:match("^pep_(.+)$");
	if not node_name then
		return nil, "invalid store name";
	end

	local results_iter, results_err = source_archive:find(username);
	if results_iter then
		local count, errs = 0, 0;
		for id, item in source_archive:find(username) do
			local wrapped_item = st.stanza("item", { xmlns = xmlns_pubsub, id = id })
				:add_child(item);
			local ok, err = pep_service:publish(node_name, user_jid, id, wrapped_item);
			if not ok then
				module:log("warn", "Failed to publish PEP item to '%s': %s", node_name, err, tostring(wrapped_item));
			end
		end
		module:log("debug", "Imported %d PEP items (%d errors)", count, errs);
	elseif results_err then
		return nil, "store access error";
	end
	return true;
end

local function is_looking_like_xep227(xml_data)
	if not xml_data or xml_data.name ~= "server-data"
	or xml_data.attr.xmlns ~= "urn:xmpp:pie:0" then
		return false;
	end
	-- Looks like 227, but check it has at least one host + user element
	return not not xml_data:find("host/user");
end

local function handle_import_227(event)
	local session = assert(event.session, "No session found");
	local username = session.username;

	local input_xml_raw = event.request.body;
	local input_xml_parsed = xml.parse(input_xml_raw);

	-- Some sanity checks
	if not input_xml_parsed or not is_looking_like_xep227(input_xml_parsed) then
		module:log("warn", "No data to import");
		return 422;
	end

	-- Set the host and username of the import to the new account's user/host
	input_xml_parsed:find("host").attr.jid = session.host;
	input_xml_parsed:find("host/user").attr.name = username;

	local user_xml = new_user_xml(session.username, session.host);

	user_xml:set_user_xml(username, session.host, input_xml_parsed);

	local xep227_driver = sm.load_driver(session.host, "xep0227");

	local query_params = http.formdecode(event.request.url.query or "");
	local selected_stores = get_selected_stores(query_params);

	module:log("debug", "Importing %d keyval stores (%s)...", #selected_stores.keyval, table.concat(selected_stores.keyval, ", "));
	for _, store_name in ipairs(selected_stores.keyval) do
		module:log("debug", "Importing keyval store %s...", store_name);
		-- Initialize the destination store (XEP-0227 backed)
		local source_store = xep227_driver:open_xep0227(store_name, nil, user_xml);

		local importer = special_keyval_importers[store_name] or generic_keyval_importer;
		local ok, err = importer(username, session.host, store_name, source_store);
		if not ok then
			module:log("warn", "Importer for keyval store '%s' encountered error: %s", store_name, err or "<no error returned>");
			return 500;
		end
	end

	if selected_stores.export_pep_data then
		local pep_store = xep227_driver:open_xep0227("pep", nil, user_xml);
		local pep_node_list = pep_store:get(session.username);
		if pep_node_list then
			for node_name in it.keys(pep_node_list) do
				table.insert(selected_stores.archive, "pep_"..node_name);
			end
		end
	end

	module:log("debug", "Importing %d archive stores (%s)...", #selected_stores.archive, table.concat(selected_stores.archive, ", "));
	for store_name in it.values(selected_stores.archive) do
		module:log("debug", "Importing archive store %s...", store_name);
		local source_archive = xep227_driver:open_xep0227(store_name, "archive", user_xml);

		local importer = special_archive_importers[store_name] or generic_archive_importer;
		local ok, err = importer(username, session.host, store_name, source_archive);
		if not ok then
			module:log("warn", "Importer for archive store '%s' encountered error: %s", err or "<no error returned>");
			return 500;
		end
	end

	return 200;
end

---

local function check_credentials(request)
	local auth_type, auth_data = string.match(request.headers.authorization or "", "^(%S+)%s(.+)$");
	if not (auth_type and auth_data) then
		return false;
	end

	if auth_type == "Bearer" then
		return tokens.get_token_session(auth_data);
	end
	return nil;
end

local function check_auth(routes)
	local function check_request_auth(event)
		local session = check_credentials(event.request);
		if not session then
			event.response.headers.authorization = ("Bearer realm=%q"):format(module.host.."/"..module.name);
			return false, 401;
		end
		event.session = session;
		return true;
	end

	for route, handler in pairs(routes) do
		routes[route] = function (event, ...)
			local permit, code = check_request_auth(event);
			if not permit then
				return code;
			end
			return handler(event, ...);
		end;
	end
	return routes;
end

module:provides("http", {
	route = check_auth {
		["GET /export"] = handle_export_227;
		["PUT /import"] = handle_import_227;
	};
});
