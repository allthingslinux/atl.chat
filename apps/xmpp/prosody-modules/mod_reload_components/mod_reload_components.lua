module:set_global();

local configmanager = require "core.configmanager";
local hostmanager = require"core.hostmanager";

local function reload_components()

        --- Check if host configuration is a component
        --- @param h hostname
        local function config_is_component(h)
            return h ~= nil and configmanager.get(h, "component_module") ~= nil; -- If a host has a component module defined within it, then it is a component
        end;

        --- Check if host / component configuration is active
        --- @param h hostname / component name
        local function component_is_new(h)
                return h ~= "*" and not hosts[h]; -- If a host is not defined in hosts and it is not global, then it is new
        end

        --- Search for new components that are not activated
        for h, c in pairs(configmanager.getconfig()) do
            if config_is_component(h) and component_is_new(h) then
                module:log ("debug", "Loading new component %s", h );
                hostmanager.activate(h, c);
            end
        end

        --- Search for active components that are not enabled in the configmanager anymore
        local enabled = {}
        for h in pairs(configmanager.getconfig()) do
            enabled[h] = true; -- Set true if it is defined in the configuration file
        end
        for h, c in pairs(hosts) do
            if not enabled[h] then -- Deactivate if not present in the configuration file
                hostmanager.deactivate(h,c);
            end
        end
end

module:hook("config-reloaded", reload_components);
