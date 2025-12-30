local actions = {};

function actions.auth(data)
	local user, host, pass = data:match("^([^:]+):([^:]+):(.+)$");
	if user == "someone" then
		return "1";
	end
end

for line in io.lines() do
	local action, data = line:match("^([^:]+)(.*)$");
	print(actions[action] and actions[action](data) or "0");
end
