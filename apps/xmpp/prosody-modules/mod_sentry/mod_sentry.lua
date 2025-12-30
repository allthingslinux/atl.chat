module:set_global();

local sentry_lib = module:require "sentry";

local hostname;
local have_pposix, pposix = pcall(require, "util.pposix");
if have_pposix and pposix.uname then
	hostname = pposix.uname().nodename;
end

local loggingmanager = require "core.loggingmanager";
local errors = require "util.error";
local format = require "util.format".format;

local default_config = assert(module:get_option("sentry"), "Please provide a 'sentry' configuration option");
default_config.server_name = default_config.server_name or hostname or "prosody";

local sentry = assert(sentry_lib.new(default_config));

local log_filters = {
	source = function (filter_source, name)
		local source = name:match(":(.+)$") or name;
		if filter_source == source then
			return true;
		end
	end;
	message_pattern = function (pattern, _, _, message)
		return not not message:match(pattern);
	end;
};

local serialize = require "util.serialization".serialize;

local function sentry_error_handler(e)
	module:log("error", "Failed to submit event to sentry: %s", e);
end

local function sentry_log_sink_maker(sink_config)
	local filters = sink_config.ignore or {};
	local n_filters = #filters;

	local submitting;
	return function (name, level, message, ...)
		-- Ignore any log messages that occur during sentry submission
		-- to avoid loops
		if submitting then return; end
		for i = 1, n_filters do
			local filter = filters[i];
			local matched;
			for filter_name, filter_value in pairs(filter) do
				local f = log_filters[filter_name];
				if f and f(filter_value, name, level, message) then
					matched = true;
				else
					matched = nil;
					break;
				end
			end
			if matched then
				return;
			end
		end
		if level == "warn" then
			level = "warning";
		end

		local event = sentry:event(level, name):message(format(message, ...));

		local params = { ... };
		for i = 1, select("#", ...) do
			if errors.is_error(params[i]) then
				event:add_exception(params[i]);
			end
		end

		submitting = true;
		event:send():catch(sentry_error_handler);
		submitting = false;
	end;
end

loggingmanager.register_sink_type("sentry", sentry_log_sink_maker);

function new(conf) --luacheck: ignore 131/new
	conf = conf or {};
	for k, v in pairs(default_config) do
		if conf[k] == nil then
			conf[k] = v;
		end
	end
	return sentry_lib.new(conf);
end
