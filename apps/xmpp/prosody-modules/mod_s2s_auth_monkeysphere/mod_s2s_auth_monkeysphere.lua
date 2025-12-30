module:set_global();

local json = require"util.json";
local json_encode, json_decode = json.encode, json.decode;
local gettime = require"socket".gettime;
local serialize = require"util.serialization".serialize;
local async = require"util.async";
local http_request = require "net.http".request;

local msva_url = assert(os.getenv"MONKEYSPHERE_VALIDATION_AGENT_SOCKET",
	"MONKEYSPHERE_VALIDATION_AGENT_SOCKET is unset, please set it").."/reviewcert";

local function check_with_monkeysphere(event)
	local session, host, cert = event.session, event.host, event.cert;
	local post_body = json_encode {
		peer = {
			name = host;
			type = "peer";
		};
		context = "https";
		-- context = "xmpp"; -- Monkeysphere needs to be extended to understand this
		pkc = {
			type = "x509pem";
			data = cert:pem();
		};
	}
	local req = {
		method = "POST";
		headers = {
			["Content-Type"] = "application/json";
		};
		body = post_body;
	};
	session.log("debug", "Asking what Monkeysphere thinks about this certificate");
	local starttime = gettime();
	local wait, done = async.waiter();
	local body, code;
	http_request(msva_url, req, function (_, _code)
		body, code = body, _code;
		done();
	end);
	wait();
	module:log("debug", "Request took %fs", gettime() - starttime);
	if code == 200 and body then
		body = json_decode(body);
		if body then
			session.log(body.valid and "info" or "warn",
				"Monkeysphere thinks the cert is %salid: %s", body.valid and "V" or "Inv", body.message);
			if body.valid then
				session.cert_chain_status = "valid";
				session.cert_identity_status = "valid";
				return true;
			end
		end
	else
		module:log("warn", "Request failed: %s, %s", tostring(code), tostring(body));
		module:log("debug", serialize(req));
	end
end

module:hook("s2s-check-certificate", check_with_monkeysphere);
