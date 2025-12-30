local modulemanager = require "core.modulemanager";
local config = require "core.configmanager";

module.host = "*";

local function reload_components()
        local defined_hosts = config.getconfig();

        for host in pairs(defined_hosts) do
                if (not hosts[host] and host ~= "*") then
                        module:log ("debug", "loading new component %s", host);
                        modulemanager.load(host, config.get(host, "core", "component_module"));
                end
        end;

        return;
end

module:hook("config-reloaded", reload_components);

