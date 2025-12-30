module:set_global()

local hosts = prosody.hosts;

module:hook("s2s-check-certificate", function(event)
	local session, cert = event.session, event.cert;
	if not cert or session.direction ~= "incoming" then return end

	local outgoing = hosts[session.to_host].s2sout[session.from_host];
	if outgoing and outgoing.type == "s2sout" and outgoing.secure and outgoing.conn:socket():getpeercertificate():pem() == cert:pem() then
		session.log("debug", "Certificate matches that of s2sout%s", tostring(outgoing):match("[a-f0-9]+$"));
		session.cert_identity_status = outgoing.cert_identity_status;
		session.cert_chain_status = outgoing.cert_chain_status;
		return true;
	end
end, 1000);
