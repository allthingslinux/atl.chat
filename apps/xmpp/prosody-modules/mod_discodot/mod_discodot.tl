local cm = require"core.configmanager";

local function format_host(host:string, conf:{string:any}) : string
	if host == "*" then
		return "Global";
	end
	local component_module = conf["component_module"];
	if component_module is string then
		if component_module == "component" then
			return string.format("Component %q", host);
		else
			return string.format("Component %q %q", host, component_module);
		end
	else
		return string.format("VirtualHost %q", host);
	end
end

function module.command(arg : { string }) : integer

	local config : { string : { string : any } } = cm.getconfig();

	print"digraph \"prosody\" {"
	for host, conf in pairs(config) do
		print(string.format("%q [label=%q]", host, format_host(host, conf)));
		local parent = host:match("%.(.*)");
		if parent and rawget(config, parent) then
			print(string.format("%q -> %q", parent, host));
		end
		local disco_items = conf["disco_items"]
		if disco_items is { { string, string } } then
			for _, pair in ipairs(disco_items) do
				print(string.format("%q -> %q", host, pair[1]));
			end
		end

	end

	print"}"

	return 0
end
