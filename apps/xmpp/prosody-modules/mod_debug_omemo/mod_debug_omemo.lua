local array = require "util.array";
local jid = require "util.jid";
local set = require "util.set";
local st = require "util.stanza";
local url_escape = require "util.http".urlencode;

local base_url = "https://"..module.host.."/";

local render_html_template = require"util.interpolation".new("%b{}", st.xml_escape, {
	urlescape = url_escape;
	lower = string.lower;
	classname = function (s) return (s:gsub("%W+", "-")); end;
	relurl = function (s)
		if s:match("^%w+://") then
			return s;
		end
		return base_url.."/"..s;
	end;
});
local render_url = require "util.interpolation".new("%b{}", url_escape, {
	urlescape = url_escape;
	noscheme = function (url)
		return (url:gsub("^[^:]+:", ""));
	end;
});

local mod_pep = module:depends("pep");

local mam = module:open_store("archive", "archive");

local function get_user_omemo_info(username)
	local everything_valid = true;
	local any_device = false;
	local omemo_status = {};
	local omemo_devices;
	local pep_service = mod_pep.get_pep_service(username);
	if pep_service and pep_service.nodes then
		local ok, _, device_list = pep_service:get_last_item("eu.siacs.conversations.axolotl.devicelist", true);
		if ok and device_list then
			device_list = device_list:get_child("list", "eu.siacs.conversations.axolotl");
		end
		if device_list then
			omemo_devices = {};
			for device_entry in device_list:childtags("device") do
				any_device = true;
				local device_info = {};
				local device_id = tonumber(device_entry.attr.id or "");
				if device_id then
					device_info.id = device_id;
					local bundle_id = ("eu.siacs.conversations.axolotl.bundles:%d"):format(device_id);
					local have_bundle, _, bundle = pep_service:get_last_item(bundle_id, true);
					if have_bundle and bundle and bundle:get_child("bundle", "eu.siacs.conversations.axolotl") then
						device_info.have_bundle = true;
						local config_ok, bundle_config = pep_service:get_node_config(bundle_id, true);
						if config_ok and bundle_config then
							device_info.bundle_config = bundle_config;
							if bundle_config.max_items == 1
							and bundle_config.access_model == "open"
							and bundle_config.persist_items == true
							and bundle_config.publish_model == "publishers" then
								device_info.valid = true;
							end
						end
					end
				end
				if device_info.valid == nil then
					device_info.valid = false;
					everything_valid = false;
				end
				table.insert(omemo_devices, device_info);
			end

			local config_ok, list_config = pep_service:get_node_config("eu.siacs.conversations.axolotl.devicelist", true);
			if config_ok and list_config then
				omemo_status.config = list_config;
				if list_config.max_items == 1
				and list_config.access_model == "open"
				and list_config.persist_items == true
				and list_config.publish_model == "publishers" then
					omemo_status.config_valid = true;
				end
			end
			if omemo_status.config_valid == nil then
				omemo_status.config_valid = false;
				everything_valid = false;
			end
		end
	end
	omemo_status.valid = everything_valid and any_device;
	return {
		status = omemo_status;
		devices = omemo_devices;
	};
end

local access_model_text = {
	open = "Public";
	whitelist = "Private";
	roster = "Contacts only";
	presence = "Contacts only";
};

local function get_message(username, message_id)
	if mam.get then
		return mam:get(username, message_id);
	end
	-- COMPAT
	local message;
	for _, result in mam:find(username, { key = message_id }) do
		message = result;
	end
	return message;
end

local function render_message(event, path)
	local username, message_id = path:match("^([^/]+)/(.+)$");
	if not username then
		return 400;
	end
	local message = get_message(username, message_id);
	if not message then
		return 404;
	end

	local user_omemo_status = get_user_omemo_info(username);

	local user_rids = set.new(array.pluck(user_omemo_status.devices or {}, "id")) / tostring;

	local message_omemo_header = message:find("{eu.siacs.conversations.axolotl}encrypted/header");
	local message_rids = set.new();
	local rid_info = {};
	if message_omemo_header then
		for key_el in message_omemo_header:childtags("key") do
			local rid = key_el.attr.rid;
			if rid then
				message_rids:add(rid);
				local prekey = key_el.attr.prekey;
				rid_info = {
					prekey = prekey and (prekey == "1" or prekey:lower() == "true");
				};
			end
		end
	end

	local rids = user_rids + message_rids;

	local direction = jid.bare(message.attr.to) == (username.."@"..module.host) and "incoming" or "outgoing";

	local is_encrypted = not not message_omemo_header;

	local sender_id = message_omemo_header and message_omemo_header.attr.sid or nil;

	local f = module:load_resource("view.tpl.html");
	if not f then
		return 500;
	end
	local tpl = f:read("*a");

	local data = { user = username, rids = {} };
	for rid in rids do
		data.rids[rid] = {
			status = message_rids:contains(rid) and "Encrypted" or user_rids:contains(rid) and "Missing" or nil;
			prekey = rid_info.prekey;
		};
	end

	data.message = {
		type = message.attr.type or "normal";
		direction = direction;
		encryption = is_encrypted and "encrypted" or "unencrypted";
		has_any_keys = not message_rids:empty();
		has_no_keys = message_rids:empty();
	};

	data.omemo = {
		sender_id = sender_id;
		status = user_omemo_status.status.valid and "no known issues" or "problems";
	};

	data.omemo.devices = {};
	if user_omemo_status.devices then
		for _, device_info in ipairs(user_omemo_status.devices) do
			data.omemo.devices[("%d"):format(device_info.id)] = {
				status = device_info.valid and "OK" or "Problem";
				bundle = device_info.have_bundle and "Published" or "Missing";
				access_model = access_model_text[device_info.bundle_config and device_info.bundle_config.access_model or nil];
			};
		end
	else
		data.omemo.devices[false] = { status = "No devices have published OMEMO keys on this account" };
	end

	event.response.headers.content_type = "text/html; charset=utf-8";
	return render_html_template(tpl, data);
end

local function check_omemo_fallback(event)
	local message = event.stanza;

	local message_omemo_header = message:find("{eu.siacs.conversations.axolotl}encrypted/header");
	if not message_omemo_header then return; end

	local to_bare = jid.bare(message.attr.to);

	local archive_stanza_id;
	for stanza_id_tag in message:childtags("stanza-id", "urn:xmpp:sid:0") do
		if stanza_id_tag.attr.by == to_bare then
			archive_stanza_id = stanza_id_tag.attr.id;
		end
	end
	if not archive_stanza_id then
		return;
	end

	local debug_url = render_url(module:http_url().."/view/{username}/{message_id}", {
		username = jid.node(to_bare);
		message_id = archive_stanza_id;
	});

	local body = message:get_child("body");
	if not body then
		body = st.stanza("body")
			:text("This message is encrypted using OMEMO, but could not be decrypted by your device.\nFor more information see: "..debug_url);
		message:reset():add_child(body);
	else
		body:text("\n\nOMEMO debug information: "..debug_url);
	end
end

module:hook("message/bare", check_omemo_fallback, -0.5);
module:hook("message/full", check_omemo_fallback, -0.5);

module:depends("http")
module:provides("http", {
	route = {
		["GET /view/*"] = render_message;
	};
});
