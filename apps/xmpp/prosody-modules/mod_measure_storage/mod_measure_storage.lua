module:set_global()

local function return_args_after_calling(f, ...)
	f();
	return ...
end

local function time_method(module, store_name, store_type, method_name, method_function)
	local opt_use_tags = module:get_option_boolean("measure_storage_tagged_metric", false);

	local metric_name, metric_tags;
	if opt_use_tags then
		metric_name, metric_tags = "storage_operation", ("store_name:%s,store_type:%s,store_operation:%s"):format(store_name, store_type, method_name);
	else
		metric_name = store_name.."_"..store_type.."_"..method_name;
	end
	local measure_operation_started = module:measure(metric_name, "times", metric_tags);

	return function (...)
		module:log("debug", "Measuring storage operation %s (%s)", metric_name, metric_tags or "no tags");
		local measure_operation_complete = measure_operation_started();
		return return_args_after_calling(measure_operation_complete, method_function(...));
	end;
end

local function wrap_store(module, store_name, store_type, store)
	local new_store = setmetatable({}, {
		__index = function (t, method_name)
			local original_method = store[method_name];
			if type(original_method) ~= "function" then
				if original_method then
					rawset(t, method_name, original_method);
				end
				return original_method;
			end
			local timed_method = time_method(module, store_name, store_type, method_name, original_method);
			rawset(t, method_name, timed_method);
			return timed_method;
		end;
	});
	return new_store;
end

local function hook_event(module)
	module:hook("store-opened", function(event)
		event.store = wrap_store(module, event.store_name, event.store_type or "keyval", event.store);
	end);
end

function module.load()
	hook_event(module);
end

function module.add_host(module)
	hook_event(module);
end
