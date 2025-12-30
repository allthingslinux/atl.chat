local dm_load = require "util.datamanager".load;
local st = require "util.stanza";
local nodeprep = require "util.encodings".stringprep.nodeprep;
local usermanager = require "core.usermanager";
local http = require "net.http";
local vcard = module:require "vcard";
local datetime = require "util.datetime";
local timer = require "util.timer";
local jidutil = require "util.jid";

-- SMTP related params. Readed from config
local os_time = os.time;
local smtp = require "socket.smtp";
local smtp_server = module:get_option_string("smtp_server", "localhost");
local smtp_port = module:get_option_string("smtp_port", "25");
local smtp_ssl = module:get_option_boolean("smtp_ssl", false);
local smtp_user = module:get_option_string("smtp_username");
local smtp_pass = module:get_option_string("smtp_password");
local smtp_address = module:get_option("smtp_from") or ((smtp_user or "no-responder").."@"..(smtp_server or module.host));
local mail_subject = module:get_option_string("msg_subject")
local mail_body = module:get_option_string("msg_body");
local url_path = module:get_option_string("url_path", "/resetpass");


-- This table has the tokens submited by the server
tokens_mails = {};
tokens_expiration = {};

-- URL
local https_host = module:get_option_string("https_host");
local http_host = module:get_option_string("http_host");
local https_port = module:get_option("https_ports", { 443 });
local http_port = module:get_option("http_ports", { 80 });

local timer_repeat = 120;		-- repeat after 120 secs

function enablessl()
    local sock = socket.tcp()
    return setmetatable({
        connect = function(_, host, port)
            local r, e = sock:connect(host, port)
            if not r then return r, e end
            sock = ssl.wrap(sock, {mode='client', protocol='tlsv1'})
            return sock:dohandshake()
        end
    }, {
        __index = function(t,n)
            return function(_, ...)
                return sock[n](sock, ...)
            end
        end
    })
end

function template(data)
	-- Like util.template, but deals with plain text
	return { apply = function(values) return (data:gsub("{([^}]+)}", values)); end }
end

local function get_template(name, extension)
	local fh = assert(module:load_resource("templates/"..name..extension));
	local data = assert(fh:read("*a"));
	fh:close();
	return template(data);
end

local function render(template, data)
	return tostring(template.apply(data));
end

function send_email(address, smtp_address, message_text, subject)
	local rcpt = "<"..address..">";

	local mesgt = {
		headers = {
			to = address;
			subject = subject or ("Jabber password reset "..jid_bare(from_address));
		};
		body = message_text;
	};
	local ok, err = nil;

	if not smtp_ssl then
		ok, err = smtp.send{ from = smtp_address, rcpt = rcpt, source = smtp.message(mesgt),
		        server = smtp_server, user = smtp_user, password = smtp_pass, port = 25 };
	else
		ok, err = smtp.send{ from = smtp_address, rcpt = rcpt, source = smtp.message(mesgt),
                server = smtp_server, user = smtp_user, password = smtp_pass, port = smtp_port, create = enablessl };
	end

	if not ok then
		module:log("error", "Failed to deliver to %s: %s", tostring(address), tostring(err));
		return;
	end
	return true;
end

local vCard_mt = {
	__index = function(t, k)
		if type(k) ~= "string" then return nil end
		for i=1,#t do
			local t_i = rawget(t, i);
			if t_i and t_i.name == k then
				rawset(t, k, t_i);
				return t_i;
			end
		end
	end
};

local function get_user_vcard(user, host)
        local vCard = dm_load(user, host or base_host, "vcard");
        if vCard then
                vCard = st.deserialize(vCard);
                vCard = vcard.from_xep54(vCard);
                return setmetatable(vCard, vCard_mt);
        end
end

local changepass_tpl = get_template("changepass",".html");
local sendmail_success_tpl = get_template("sendmailok",".html");
local reset_success_tpl = get_template("resetok",".html");
local token_tpl = get_template("token",".html");

function generate_page(event, display_options)
	local request = event.request;

	return render(changepass_tpl, {
		path = request.path; hostname = module.host;
		notice = display_options and display_options.register_error or "";
	})
end

function generate_token_page(event, display_options)
        local request = event.request;

        return render(token_tpl, {
                path = request.path; hostname = module.host;
				token = request.url.query;
                notice = display_options and display_options.register_error or "";
        })
end

function generateToken(address)
	math.randomseed(os.time())
	length = 16
    if length < 1 then return nil end
        local array = {}
        for i = 1, length, 2 do
            array[i] = string.char(math.random(48,57))
			array[i+1] = string.char(math.random(97,122))
        end
	local token = table.concat(array);
	if not tokens_mails[token] then

		tokens_mails[token] = address;
		tokens_expiration[token] = os.time();
		return token
	else
		module:log("error", "Reset password token collision: '%s'", token);
		return generateToken(address)
	end
end

function isExpired(token)
	if not tokens_expiration[token] then
		return nil;
	end
	if os.difftime(os.time(), tokens_expiration[token]) < 86400 then -- 86400 secs == 24h
		-- token is valid yet
		return nil;
	else
		-- token invalid, we can create a fresh one.
		return true;
	end
end

-- Expire tokens
expireTokens = function()
	for token,value in pairs(tokens_mails) do
		if isExpired(token) then
			module:log("info","Expiring password reset request from user '%s', not used.", tokens_mails[token]);
			tokens_mails[token] = nil;
			tokens_expiration[token] = nil;
		end
	end
	return timer_repeat;
end

-- Check if a user has a active token not used yet.
function hasTokenActive(address)
	for token,value in pairs(tokens_mails) do
		if address == value and not isExpired(token) then
			return token;
		end
	end
	return nil;
end

function generateUrl(token)
	local url;

	if https_host then
		url = "https://" .. https_host;
	else
		url = "http://" .. http_host;
	end

	if https_port then
		url = url .. ":" .. https_port[1];
	else
		url = url .. ":" .. http_port[1];
	end

	url = url .. url_path .. "token.html?" .. token;

	return url;
end

function sendMessage(jid, subject, message)
  local msg = st.message({ from = module.host; to = jid; }):
	    tag("subject"):text(subject):up():
	    tag("body"):text(message);
  module:send(msg);
end

function send_token_mail(form, origin)
	local prepped_username = nodeprep(form.username);
	local prepped_mail = form.email;
	local jid = prepped_username .. "@" .. module.host;

    if not prepped_username then
    	return nil, "El usuario contiene caracteres incorrectos";
    end
    if #prepped_username == 0 then
    	return nil, "El campo usuario está vacio";
    end
    if not usermanager.user_exists(prepped_username, module.host) then
    	return nil, "El usuario NO existe";
    end

	if #prepped_mail == 0 then
    	return nil, "El campo email está vacio";
    end

	local vcarduser = get_user_vcard(prepped_username, module.host);

	if not vcarduser then
		return nil, "User has not vCard";
	else
		if not vcarduser.EMAIL then
			return nil, "Esa cuente no tiene ningún email configurado en su vCard";
		end

		email = string.lower(vcarduser.EMAIL[1]);

		if email ~= string.lower(prepped_mail) then
			return nil, "Dirección eMail incorrecta";
		end

		-- Check if has already a valid token, not used yet.
		if hasTokenActive(jid) then
			local valid_until = tokens_expiration[hasTokenActive(jid)] + 86400;
			return nil, "Ya tienes una petición de restablecimiento de clave válida hasta: " .. datetime.date(valid_until) .. " " .. datetime.time(valid_until);
		end

		local url_token = generateToken(jid);
		local url = generateUrl(url_token);
		local email_body =  render(get_template("sendtoken",".mail"), {jid = jid, url = url} );

		module:log("info", "Sending password reset mail to user %s", jid);
		send_email(email, smtp_address, email_body, mail_subject);
		return "ok";
	end

end

function reset_password_with_token(form, origin)
	local token = form.token;
	local password = form.newpassword;

	if not token then
		return nil, "El Token es inválido";
	end
	if not tokens_mails[token] then
		return nil, "El Token no existe o ya fué usado";
	end
	if not password then
		return nil, "La campo clave no puede estar vacio";
	end
	if #password < 5 then
		return nil, "La clave debe tener una longitud de al menos 5 caracteres";
	end
	local jid = tokens_mails[token];
	local user, host, resource = jidutil.split(jid);

	usermanager.set_password(user, password, host);
	module:log("info", "Password changed with token for user %s", jid);
	tokens_mails[token] = nil;
	tokens_expiration[token] = nil;
	sendMessage(jid, mail_subject, mail_body);
	return "ok";
end

function generate_success(event, form)
	return render(sendmail_success_tpl, { jid = nodeprep(form.username).."@"..module.host });
end

function generate_register_response(event, form, ok, err)
	local message;
	if ok then
		return generate_success(event, form);
	else
		return generate_page(event, { register_error = err });
	end
end

function handle_form_token(event)
	local request, response = event.request, event.response;
	local form = http.formdecode(request.body);

	local token_ok, token_err = send_token_mail(form, request);
        response:send(generate_register_response(event, form, token_ok, token_err));

	return true; -- Leave connection open until we respond above
end

function generate_reset_success(event, form)
        return render(reset_success_tpl, { });
end

function generate_reset_response(event, form, ok, err)
        local message;
        if ok then
                return generate_reset_success(event, form);
        else
                return generate_token_page(event, { register_error = err });
        end
end

function handle_form_reset(event)
	local request, response = event.request, event.response;
        local form = http.formdecode(request.body);

        local reset_ok, reset_err = reset_password_with_token(form, request);
        response:send(generate_reset_response(event, form, reset_ok, reset_err));

        return true; -- Leave connection open until we respond above

end

timer.add_task(timer_repeat, expireTokens);

module:provides("http", {
	default_path = url_path;
	route = {
	    ["GET /style.css"] = render(get_template("style",".css"), {});
		["GET /token.html"] = generate_token_page;
		["GET /"] = generate_page;
		["POST /token.html"] = handle_form_reset;
		["POST /"] = handle_form_token;
	};
});


