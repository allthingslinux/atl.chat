-- CLI script to ease templates writing
-- must be launched with `lua test.lua` after setting the following env vars,
-- (assuming prosody has been clone in ../../prosody-0.12)
-- LUA_CPATH=../../prosody-0.12/\?.so
-- LUA_PATH=../../prosody-0.12/\?.lua\;\?.lua
-- allow loading ".lib.lua" modules
local function loadlib(modulename)
	local filename = modulename .. ".lib.lua"
	local file = io.open(filename, "rb")
	if file then
		return load(file:read("a")), modulename
	else
		return filename .. " not found"
	end
end

table.insert(package.searchers, loadlib)

local json = require "util.json"
local format = require "format"
local templates = require "templates"

local function read_json(fname)
	local f = io.open(fname)
	assert(f ~= nil, fname)
	local data = json.decode(f:read("a"))
	f:close()
	return data
end

local function read_payload(dirname)
	return read_json("./webhook-examples/" .. dirname .. "/content.json")
end

local function pprint(stanza) print(stanza:indent(1, "  "):pretty_print()) end

pprint(format(read_payload("push"), templates.push))
pprint(format(read_payload("pull_request"), templates.pull_request))
-- pprint(format(read_payload("push_tag"), templates.push))  -- this is a push with 0 commits. It's ugly!
pprint(format(read_payload("release"), templates.release))
