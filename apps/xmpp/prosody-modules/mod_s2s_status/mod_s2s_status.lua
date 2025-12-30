local status_out = module:shared("out");

local errors = require "util.error";

local function get_session_info(session)
	local direction, peer_host = session.direction;
	if direction == "outgoing" then
		peer_host = session.to_host;
	elseif direction == "incoming" then
		peer_host = session.from_host;
	end
	return peer_host, direction, session.id;
end

local function get_domain_log_out(peer_domain)
	local domain_log = status_out[peer_domain];
	if not domain_log then
		domain_log = {};
		status_out[peer_domain] = domain_log;
	end
	return domain_log;
end

local function get_connection_record(domain_log, id)
	for _, record in ipairs(domain_log) do
		if record.id == id then
			return record;
		end
	end
	-- No record for this connection yet, create it
	local record = { id = id };
	table.insert(domain_log, 1, record);
	return record;
end

local function log_new_connection_out(peer_domain, id)
	local domain_log = get_domain_log_out(peer_domain);
	local record = get_connection_record(domain_log, id);
	record.status, record.time_started = "connecting", os.time();
end

local function log_successful_connection_out(peer_domain, id)
	local domain_log = get_domain_log_out(peer_domain);
	local record = get_connection_record(domain_log, id);
	record.status, record.time_connected = "connected", os.time();
end

local function log_ended_connection_out(peer_domain, id, reason)
	local domain_log = get_domain_log_out(peer_domain);
	local record = get_connection_record(domain_log, id);

	if record.status == "connecting" then
		record.status = "failed";
	elseif record.status == "connected" then
		record.status = "disconnected";
	end
	if reason then
		local e_reason = errors.new(reason);
		record.error = {
			type = e_reason.type;
			condition = e_reason.condition;
			text = e_reason.text;
		};
		if not record.error.text and type(reason) == "string" then
			record.error.text = reason;
		end
	end
	local now = os.time();
	record.time_ended = now;
end

local function s2sout_established(event)
	local peer_domain, _, id = get_session_info(event.session);
	log_successful_connection_out(peer_domain, id);
end

local function s2sout_destroyed(event)
	local peer_domain, _, id = get_session_info(event.session);
	log_ended_connection_out(peer_domain, id);
end

local function s2s_created(event)
	local peer_domain, direction, id = get_session_info(event.session);
	if direction == "outgoing" then
		log_new_connection_out(peer_domain, id);
	end
end

module:hook("s2s-created", s2s_created);
module:hook("s2sout-established", s2sout_established);
module:hook("s2sout-destroyed", s2sout_destroyed);
