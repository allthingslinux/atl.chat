local captcha_options = module:get_option("captcha_options", {});
local nodeprep = require "util.encodings".stringprep.nodeprep;
local usermanager = require "core.usermanager";
local datamanager = require "util.datamanager";
local http = require "net.http";
local path_sep = package.config:sub(1,1);
local json = require "util.json".decode;
local t_concat = table.concat;

pcall(function ()
	module:depends("register_limits");
end);

module:depends"http";

local extra_fields = {
	nick = true; name = true; first = true; last = true; email = true;
	address = true; city = true; state = true; zip = true;
	phone = true; url = true; date = true;
}

local template_path = module:get_option_string("register_web_template", "templates");
function template(data)
	-- Like util.template, but deals with plain text
	return { apply = function(values) return (data:gsub("{([^}]+)}", values)); end }
end

local function get_template(name)
	local fh = assert(module:load_resource(template_path..path_sep..name..".html"));
	local data = assert(fh:read("*a"));
	fh:close();
	return template(data);
end

local function render(template, data)
	return tostring(template.apply(data));
end

local register_tpl = get_template "register";
local success_tpl = get_template "success";

-- COMPAT `or request.conn:ip()`

if next(captcha_options) ~= nil then
	local provider = captcha_options.provider;
	if provider == nil or provider == "recaptcha" then
		local recaptcha_tpl = get_template "recaptcha";

		function generate_captcha(display_options)
			return recaptcha_tpl.apply(setmetatable({
				recaptcha_display_error = display_options and display_options.recaptcha_error
				and ("&error="..display_options.recaptcha_error) or "";
			}, {
				__index = function (_, k)
					if captcha_options[k] then return captcha_options[k]; end
					module:log("error", "Missing parameter from captcha_options: %s", k);
				end
			}));
		end
		function verify_captcha(request, form, callback)
			http.request("https://www.google.com/recaptcha/api/siteverify", {
				body = http.formencode {
					secret = captcha_options.recaptcha_private_key;
					remoteip = request.ip or request.conn:ip();
					response = form["g-recaptcha-response"];
				};
			}, function (verify_result, code)
				local result = json(verify_result);
				if not result then
					module:log("warn", "Unable to decode response from recaptcha: [%d] %s", code, verify_result);
					callback(false, "Captcha API error");
				elseif result.success == true then
					callback(true);
				else
					callback(false, t_concat(result["error-codes"]));
				end
			end);
		end
	elseif provider == "hcaptcha" then
		local captcha_tpl = get_template "hcaptcha";

		function generate_captcha(display_options)
			return captcha_tpl.apply(setmetatable({
				captcha_display_error = display_options and display_options.captcha_error
				and ("&error="..display_options.captcha_error) or "";
			}, {
				__index = function (_, k)
					if captcha_options[k] then return captcha_options[k]; end
					module:log("error", "Missing parameter from captcha_options: %s", k);
				end
			}));
		end
		function verify_captcha(request, form, callback)
			http.request("https://hcaptcha.com/siteverify", {
				body = http.formencode {
					secret = captcha_options.captcha_private_key;
					remoteip = request.ip or request.conn:ip();
					response = form["h-captcha-response"];
				};
			}, function (verify_result, code)
				local result = json(verify_result);
				if not result then
					module:log("warn", "Unable to decode response from hcaptcha: [%d] %s", code, verify_result);
					callback(false, "Captcha API error");
				elseif result.success == true then
					callback(true);
				else
					callback(false, t_concat(result["error-codes"]));
				end
			end);
		end
	end
else
	module:log("debug", "No captcha options set, using fallback captcha")
	local random = math.random;
	local hmac_sha1 = require "util.hashes".hmac_sha1;
	local secret = require "util.uuid".generate()
	local ops = { '+', '-' };
	local captcha_tpl = get_template "simplecaptcha";
	function generate_captcha()
		local op = ops[random(1, #ops)];
		local x, y = random(1, 9)
		repeat
			y = random(1, 9);
		until x ~= y;
		local answer;
		if op == '+' then
			answer = x + y;
		elseif op == '-' then
			if x < y then
				-- Avoid negative numbers
				x, y = y, x;
			end
			answer = x - y;
		end
		local challenge = hmac_sha1(secret, answer, true);
		return captcha_tpl.apply {
			op = op, x = x, y = y, challenge = challenge;
		};
	end
	function verify_captcha(request, form, callback)
		if hmac_sha1(secret, form.captcha_reply or "", true) == form.captcha_challenge then
			callback(true);
		else
			callback(false, "Captcha verification failed");
		end
	end
end

function generate_page(event, display_options)
	local request, response = event.request, event.response;

	response.headers.content_type = "text/html; charset=utf-8";
	return render(register_tpl, {
		path = request.path; hostname = module.host;
		notice = display_options and display_options.register_error or "";
		captcha = generate_captcha(display_options);
	})
end

function register_user(form, origin)
	local username = form.username;
	local password = form.password;
	local confirm_password = form.confirm_password;
	local jid = nil;
	form.username, form.password, form.confirm_password = nil, nil, nil;

	local prepped_username = nodeprep(username, true);
	if not prepped_username then
		return nil, "Username contains forbidden characters";
	end
	if #prepped_username == 0 then
		return nil, "The username field was empty";
	end
	if usermanager.user_exists(prepped_username, module.host) then
		return nil, "Username already taken";
	end
	local registering = { username = prepped_username , host = module.host, additional = form, ip = origin.ip or origin.conn:ip(), allowed = true }
	module:fire_event("user-registering", registering);
	if not registering.allowed then
		return nil, registering.reason or "Registration not allowed";
	end
	if confirm_password ~= password then
		return nil, "Passwords don't match";
	end
	local ok, err = usermanager.create_user(prepped_username, password, module.host);
	if ok then
		jid = prepped_username.."@"..module.host
		local extra_data = {};
		for field in pairs(extra_fields) do
			local field_value = form[field];
			if field_value and #field_value > 0 then
				extra_data[field] = field_value;
			end
		end
		if next(extra_data) ~= nil then
			datamanager.store(prepped_username, module.host, "account_details", extra_data);
		end
		module:fire_event("user-registered", {
			username = prepped_username,
			host = module.host,
			source = module.name,
			ip = origin.ip or origin.conn:ip(),
		});
	end
	return jid, err;
end

function generate_success(event, jid)
	return render(success_tpl, { jid = jid });
end

function generate_register_response(event, jid, err)
	event.response.headers.content_type = "text/html; charset=utf-8";
	if jid then
		return generate_success(event, jid);
	else
		return generate_page(event, { register_error = err });
	end
end

function handle_form(event)
	local request, response = event.request, event.response;
	local form = http.formdecode(request.body);
	verify_captcha(request, form, function (ok, err)
		if ok then
			local jid, register_err = register_user(form, request);
			response:send(generate_register_response(event, jid, register_err));
		else
			response:send(generate_page(event, { register_error = err }));
		end
	end);
	return true; -- Leave connection open until we respond above
end

module:provides("http", {
	title = module:get_option_string("register_web_title", "Account Registration");
	route = {
		GET = generate_page;
		["GET /"] = generate_page;
		POST = handle_form;
		["POST /"] = handle_form;
	};
});
