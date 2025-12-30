-- mod_file_management
--
-- Copyright (C) 2019 Emmanuel Gil Peyrot
--
-- This file is MIT/X11 licensed.
--

module:depends("http_upload");
local dataform_new = require "util.dataforms".new;
local adhoc_new = module:require "adhoc".new;
local adhoc_simple_form = require "util.adhoc".new_simple_form;
local adhoc_initial_data_form = require "util.adhoc".new_initial_data_form;
local url = require "socket.url";
local lfs = require "lfs";
local datamanager = require "util.datamanager";
local jid_prepped_split = require "util.jid".prepped_split;
local join_path = require "util.paths".join;
local t_concat = table.concat;
local t_insert = table.insert;

local storage_path = module:get_option_string("http_upload_path", join_path(prosody.paths.data, "http_upload"));

local function get_url(dir, filename)
	local slot_url = url.parse(module:http_url("upload"));
	slot_url.path = url.parse_path(slot_url.path or "/");
	t_insert(slot_url.path, dir);
	t_insert(slot_url.path, filename);
	slot_url.path.is_directory = false;
	slot_url.path = url.build_path(slot_url.path);
	return url.build(slot_url);
end

local list_form = dataform_new {
	title = "List files for user";
	instructions = "Select the JID of a user to list the files they have uploaded.";
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "http://prosody.im/protocol/file_management#list";
	};
	{
		type = "jid-single";
		name = "accountjid";
		required = true;
		label = "JID";
	};
};

module:provides("adhoc", adhoc_new("File Management", "http://prosody.im/protocol/file_management#list", adhoc_simple_form(list_form, function (data, errors)
	if errors then
		local errmsg = {};
		for name, text in pairs(errors) do
			errmsg[#errmsg + 1] = name .. ": " .. text;
		end
		return { status = "completed", error = { message = t_concat(errmsg, "\n") } };
	end

	local jid = data.accountjid;
	local user, host = jid_prepped_split(jid);

	local uploads, err = datamanager.list_load(user, host, "http_upload");
	if err then
		return { status = "completed", error = "File upload data not found for user "..jid.."." };
	end

	local result = {};
	for i, upload in ipairs(uploads) do
		module:log("debug", "http_upload_management#list %d %q", i, upload);
		if upload.dir ~= nil then
			t_insert(result, get_url(upload.dir, upload.filename));
		else
			-- upload.filename was pointing to a path on the file system…
			-- TODO: Try to guess the URL from that.
		end
	end

	return { status = "completed", info = t_concat(result, "\n") };
end), "admin"));
