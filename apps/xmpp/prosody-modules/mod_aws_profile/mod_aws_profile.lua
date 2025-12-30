local http = require "net.http";
local json = require "util.json";
local parse_timestamp = require "util.datetime".parse;

module:set_global();

local current_credentials = module:shared("/*/aws_profile/credentials");

local function get_role_credentials(role_name, cb)
	http.request("http://169.254.169.254/latest/meta-data/iam/security-credentials/"..role_name, nil, function (credentials_json)
		local credentials = credentials_json and json.decode(credentials_json);
		if not credentials or not (credentials.AccessKeyId and credentials.SecretAccessKey) then
			module:log("warn", "Failed to fetch credentials for %q", role_name);
			cb(nil);
			return;
		end
		local expiry = parse_timestamp(credentials.Expiration);
		local ttl = os.difftime(expiry, os.time());
		cb({
			access_key = credentials.AccessKeyId;
			secret_key = credentials.SecretAccessKey;
			ttl = ttl;
			expiry = expiry;
		});
	end);
end

local function get_credentials(cb)
	http.request("http://169.254.169.254/latest/meta-data/iam/security-credentials", nil, function (role_name)
		role_name = role_name and role_name:match("%S+");
		if not role_name then
			module:log("warn", "Unable to discover role name");
			cb(nil);
			return;
		end
		get_role_credentials(role_name, cb);
	end);
end

function refresh_credentials(force)
	if not force and current_credentials.expiry and current_credentials.expiry - os.time() > 300 then
		return;
	end
	get_credentials(function (credentials)
		if not credentials then
			module:log("warn", "Failed to refresh credentials!");
			return;
		end
		current_credentials.access_key = credentials.access_key;
		current_credentials.secret_key = credentials.secret_key;
		current_credentials.expiry = credentials.expiry;
		module:add_timer(credentials.ttl or 240, refresh_credentials);
		module:fire_event("aws_profile/credentials-refreshed", current_credentials);
	end);
end

function module.load()
	refresh_credentials(true);
end
