
assert(require"ssl.core".info, "Incompatible LuaSec version");

local function hook(event_name, typ, policy)
	if not policy then return end
	if policy == "FS" then
		policy = { cipher = "^E?C?DHE%-" };
	elseif type(policy) == "string" then
		policy = { cipher = policy };
	end

	module:hook(event_name, function (event)
		local origin = event.origin;
		if origin.conn and origin.conn:ssl() then
			local info = origin.conn:socket():info();
			for key, what in pairs(policy) do
				module:log("debug", "Does info[%q] = %s match %s ?", key, tostring(info[key]), tostring(what));
				if (type(what) == "number" and what < info[key] ) or (type(what) == "string" and not info[key]:match(what)) then
					origin:close({ condition = "policy-violation", text = ("TLS %s '%s' not acceptable"):format(key, tostring(info[key])) });
					return false;
				end
				module:log("debug", "Seems so");
			end
			module:log("debug", "Policy matches");
		end
	end, 1000);
end

local policy = module:get_option(module.name, {});

if type(policy) == "string" then
	policy = { c2s = policy, s2s = policy };
end

hook("stream-features", "c2s", policy.c2s);
hook("s2s-stream-features", "s2sin", policy.s2sin or policy.s2s);
hook("stanza/http://etherx.jabber.org/streams:features", "s2sout", policy.s2sout or policy.s2s);
