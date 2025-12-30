-- Prosody IM
-- Copyright (C) 2012 Kim Alvefur
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

module:set_global();
local server = require"net.http.server";
local lfs = require "lfs";
local stat = lfs.attributes;
local build_path = require"socket.url".build_path;
local base64_encode = require"util.encodings".base64.encode;
local tag = require"util.stanza".stanza;
local template = require"util.template";

local mime = module:shared("/*/http_files/mime");

local function get_resource(resource)
	local fh = assert(module:load_resource(resource));
	local data = fh:read"*a";
	fh:close();
	return data;
end

local dir_index_template = template(get_resource("resources/template.html"));
local style = get_resource("resources/style.css"):gsub("url%((.-)%)", function(url)
	--module:log("debug", "Inlineing %s", url);
	return "url(data:image/png;base64,"..base64_encode(get_resource("resources/"..url))..")";
end);

local function generate_directory_index(path, full_path)
	local filelist = tag("ul", { class = "filelist" } ):text"\n";
	if path ~= "/" then
		filelist:tag("li", { class = "parent directory" })
			:tag("a", { href = "..", rel = "up" }):text("Parent Directory"):up():up():text"\n"
	end
	local mime_map = mime.types;
	for file in lfs.dir(full_path) do
		if file:sub(1,1) ~= "." then
			local attr = stat(full_path..file) or {};
			local path = { file };
			local file_ext = file:match"%.([^.]+)$";
			local type = attr.mode == "file" and file_ext and mime_map and mime_map[file_ext] or nil;
			local class = table.concat({ attr.mode or "unknown", file_ext, type and type:match"^[^/]+" }, " ");
			path.is_directory = attr.mode == "directory";
			filelist:tag("li", { class = class })
				:tag("a", { href = build_path(path), type = type }):text(file):up()
			:up():text"\n";
		end
	end
	return "<!DOCTYPE html>\n"..tostring(dir_index_template.apply{
		path = path,
		style = style,
		filelist = filelist,
		footer = "Prosody "..prosody.version,
	});
end

module:hook_object_event(server, "directory-index", function (event)
	local ok, data = pcall(generate_directory_index, event.path, event.full_path);
	if ok then return data end
	module:log("warn", data);
end);
