local io_open = io.open;
local dm = require "core.storagemanager".olddm;

-- Append a blob of data to a file
function dm.append_raw(username, host, datastore, ext, data)
	if type(data) ~= "string" then return; end
	local filename = dm.getpath(username, host, datastore, ext, true);

	local ok;
	local f, msg = io_open(filename, "r+");
	if not f then
		-- File did probably not exist, let's create it
		f, msg = io_open(filename, "w");
		if not f then
			return nil, msg, "open";
		end
	end

	local pos = f:seek("end");

	ok, msg = f:write(data);
	if not ok then
		f:close();
		return ok, msg, "write";
	end

	ok, msg = f:close();
	if not ok then
		return ok, msg;
	end

	return true, pos;
end

