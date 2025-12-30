local count_registering = module:measure("user_registering", "rate");
local count_registered = module:measure("user_registered", "rate");

module:hook("user-registering", function ()
	count_registering();
end);

module:hook("user-registered", function ()
	count_registered();
end);
