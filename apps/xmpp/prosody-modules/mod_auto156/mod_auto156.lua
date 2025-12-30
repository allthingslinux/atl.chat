-- Synthesize XEP-0156 JSON from DNS
local array = require "util.array";
local encodings = require "util.encodings";
local json = require "util.json";
local promise = require "util.promise";

local dns = require"net.adns".resolver();

local function check_dns(domain)
	return dns:lookup_promise("_xmppconnect." .. domain, "TXT");
end

local function check_domain(domain)
	return promise.resolve(domain):next(encodings.stringprep.nameprep):next(encodings.idna.to_ascii):next(
		function(domain_A)
			if not domain_A then
				return promise.reject(400);
			else
				return domain_A;
			end
		end):next(check_dns):next(function(txt)
		local uris = array();
		for _, cm in ipairs(txt) do
			local kind, uri = tostring(cm.txt):match("^_xmpp%-client%-(%w+)=([hpstw]+s?://.*)");
			if kind then
				uris:push({rel = "urn:xmpp:alt-connections:" .. kind, href = uri});
			end
		end
		if #uris == 0 then
			return promise.reject(404);
		end
		return {links=uris};
	end);
end

module:depends("http");
module:provides("http", {
	route = {
		["GET /*"] = function(_, domain)
			return check_domain(domain):next(function(altmethods)
				return {headers = {content_type = "application/json"}, body = json.encode(altmethods)};
			end);
		end,
	},
});

function module.command(args)
	local async = require "util.async";
	for _, domain in ipairs(args) do
		print(assert(async.wait_for(check_domain(domain):next(json.encode))));
	end
end
