local http_files = require "net.http.files";

local mime_map = module:shared("/*/http_files/mime").types or {
	css = "text/css",
	js = "application/javascript",
};

local libjs_path = module:get_option_string("libjs_path", "/usr/share/javascript");

do -- sanity check
	local lfs = require "lfs";

	local exists, err = lfs.attributes(libjs_path, "mode");
	if exists ~= "directory" then
		module:log("error", "Problem with 'libjs_path': %s", err or "not a directory");
	end
end

module:provides("http", {
		default_path = "/share";
		route = {
			["GET /*"] = http_files.serve({ path = libjs_path, mime_map = mime_map });
		}
	});
