module:set_global();

local config = require "core.configmanager";
local modulemanager = require "core.modulemanager";
local argparse = require "util.argparse";
local dns = require"net.adns".resolver();
local async = require "util.async";
local set = require "util.set";
local nameprep = require"util.encodings".stringprep.nameprep;
local idna_to_ascii = require"util.encodings".idna.to_ascii;

local services = { "xmpp-client"; "xmpps-client"; "xmpp-server"; "xmpps-server" }

local function validate_dnsname_option(options, option_name, default)
	local host = options[option_name];
	if host == nil then return default end
	local normalized = nameprep(host);
	if not normalized then
		module:log("error", "--%s %q fails normalization");
		return;
	end
	local alabel = idna_to_ascii(normalized);
	if not alabel then
		module:log("error", "--%s %q fails IDNA");
		return;
	end
	return alabel;
end

function module.command(arg)
	local opts = argparse.parse(arg, {
		short_params = { d = "domain"; p = "primary"; t = "target"; l = "ttl"; h = "help"; ["?"] = "help" };
		value_params = { domain = true; primary = true; target = true; ttl = true };
	});

	if not arg[1] or arg[2] or not opts or opts.help or not opts.domain then
		local out = opts.help and io.stdout or io.stderr;
		out:write("prosodyctl mod_dnsupdate [options] virtualhost\n");
		out:write("\t-d --domain\tbase domain name *required*\n");
		out:write("\t-p --primary\tprimary DNS name server\n");
		out:write("\t-t --target\ttarget hostname for SRV\n");
		out:write("\t-l --ttl\tTTL to use\n");
		out:write("\t--each\tremove and replace individual SRV records\n");
		out:write("\t--reset\tremove and replace all SRV records\n");
		out:write("\t--remove\tremove all SRV records\n");
		return opts and opts.help and 0 or 1;
	end

	local vhost = nameprep(arg[1]); -- TODO loop over arg[]?
	if not vhost then
		module:log("error", "Host %q fails normalization", arg[1]);
		return 1;
	end
	local ihost = idna_to_ascii(vhost);
	if not ihost then
		module:log("error", "Host %q fails IDNA", vhost);
		return 1;
	end
	if not config.get(vhost, "component_module") and not config.get(vhost, "defined") then
		module:log("error", "Host %q is not defined in the config", vhost);
		return 1;
	end

	local domain = validate_dnsname_option(opts, "domain");
	if not domain then
		module:log("error", "--domain is required");
		return 1;
	end
	local primary = validate_dnsname_option(opts, "primary")
		or async.wait_for(dns:lookup_promise(domain, "SOA"):next(function(ret) return ret[1].soa.mname; end));
	if not primary then
		module:log("error", "Could not discover primary name server, specify it with --primary");
		return 1;
	end
	local target = validate_dnsname_option(opts, "target", module:context(vhost):get_option_string("xmpp_host", ihost));
	-- TODO validate that target has A/AAAA

	local configured_ports = {
		["xmpp-client"] = module:get_option_array("c2s_ports", { 5222 });
		["xmpp-server"] = module:get_option_array("s2s_ports", { 5269 });
		["xmpps-client"] = module:get_option_array("c2s_direct_tls_ports", {});
		["xmpps-server"] = module:get_option_array("s2s_direct_tls_ports", {});
	};

	local modules_enabled = modulemanager.get_modules_for_host(vhost);
	if not modules_enabled:contains("c2s") then
		configured_ports["xmpp-client"] = {};
		configured_ports["xmpps-client"] = {};
	end
	if not modules_enabled:contains("s2s") then
		configured_ports["xmpp-server"] = {};
		configured_ports["xmpps-server"] = {};
	end

	if modules_enabled:contains("net_multiplex") then
		for opt, ports in pairs(configured_ports) do
			ports:append(module:get_option_array(opt:sub(1, 5) == "xmpps" and "ssl_ports" or "ports", {}));
		end
	end

	local existing_srv = {};
	for _, service in ipairs(services) do
		existing_srv[service] = dns:lookup_promise(("_%s._tcp.%s"):format(service, ihost), "SRV");
	end

	print("zone", domain);
	print("server", primary);
	print("ttl " .. tostring(opts.ttl or 60 * 60));

	for _, service in ipairs(services) do
		local config_ports = set.new(configured_ports[service]);
		local dns_ports = set.new();

		if (opts.reset or opts.remove) and not opts.each then
			print(("del _%s._tcp.%s IN SRV"):format(service, ihost));
		else
			local records = (async.wait_for(existing_srv[service]));
			for _, rr in ipairs(records) do
				if target == nameprep(rr.srv.target):gsub("%.$", "") then
					dns_ports:add(rr.srv.port)
				elseif opts.each then
					print(("del _%s._tcp.%s IN SRV %s"):format(service, ihost, rr));
				end
			end
		end

		if not opts.remove then
			if config_ports:empty() then
				print(("add _%s._tcp.%s IN SRV 0 0 0 ."):format(service, ihost));
			else
				for port in (config_ports - dns_ports) do
					print(("add _%s._tcp.%s IN SRV 1 1 %d %s"):format(service, ihost, port, target));
				end
			end
		end
	end

	print("show");
	print("send");
	print("answer");
end
