-- Copyright (C) 2021 Kim Alvefur
--
-- This file is MIT licensed.

local lfs = require "lfs";
local st = require "util.stanza";
local jid = require "util.jid";
local paths = require "util.paths";
local unpack = table.unpack or _G.unpack;

function module.command(arg)
	local sm = require "core.storagemanager";
	local dm = sm.olddm;

	local component, user_host = unpack(arg);

	sm.initialize_host(component);

	local new_uploads = sm.open(component, "uploads", "archive");

	local legacy_storage_path = module:context(component):get_option_string("http_upload_path", paths.join(prosody.paths.data, "http_upload"));

	local legacy_uploads = {};
	for user in assert(dm.users(user_host, "http_upload", "list")) do
		legacy_uploads[user] = dm.list_load(user, user_host, "http_upload");
	end
	while true do
		local oldest_uploads, uploader;
		for user, uploads in pairs(legacy_uploads) do
			if uploads[1] and (not oldest_uploads or uploads[1].time < oldest_uploads[1].time) then
				oldest_uploads, uploader = uploads, jid.join(user, user_host);
			end
		end
		if not oldest_uploads then break end
		local item = table.remove(oldest_uploads, 1);
		local source_directory = paths.join(legacy_storage_path, item.dir);
		local source_filename = paths.join(source_directory, item.filename);
		local target_filename = dm.getpath(item.dir, component, "http_file_share", "bin", true);
		if not lfs.attributes(source_filename, "mode") then
			print("Not migrating missing file " .. source_filename);
		else
			print("Moving " .. source_filename .. " to " .. target_filename .. " for " .. uploader);
			local upload = st.stanza("request", {
				xmlns = "urn:xmpp:http:upload:0";
				filename = item.filename;
				size = string.format("%d", item.size);
				-- content-type not included with mod_http_upload
			});
			assert(new_uploads:append(nil, item.dir, upload, item.time, uploader));
			assert(os.rename(source_filename, target_filename));
		end
		os.remove(source_directory); -- failure not fatal
	end
	for user, uploads in pairs(legacy_uploads) do
		assert(dm.list_store(user, user_host, "http_upload", uploads));
	end
	os.remove(legacy_storage_path);
	return 0;
end
