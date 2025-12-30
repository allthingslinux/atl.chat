-- simple installer for mod_register with dependicies

files = {"util/dataforms.lua", "modules/mod_register.lua", "FiraSans-Regular.ttf"}

default_path = "/usr/lib/prosody"


function exists(name)
	if type(name) ~= "string" then return false end
	return os.rename(name, name) and true or false
end

function copy_file(name, target)
	local file = io.open(name)
	local data = file:read("*all")
	file:close()
	local file = io.open(target, "w")
	file:write(data)
	file:close()
end

function copy_files(path)
	for index = 1, #files do
		local filename = files[index]
		os.remove(default_path.."/"..filename)
		copy_file(filename, default_path.."/"..filename)
		print("copied: "..default_path.."/"..filename)
	end
end

if not exists(default_path) then
	io.write("\nEnter prosody path [/usr/lib/prosody]: ")
	path = io.read("*line")
end

copy_files(path or default_path)