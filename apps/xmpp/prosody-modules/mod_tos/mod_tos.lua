local array = require"util.array";
local st = require"util.stanza";

local tos_version = assert(module:get_option("tos_version"), "tos_version must be set")

local status_storage;
if prosody.process_type == "prosody" or prosody.shutdown then
	status_storage = module:open_store("tos_status", "keyval")
end

local documents = array{};

local function validate_doc(doc)
	if not doc.title or not doc.sources or #doc.sources < 1 then
		return false, "document needs to have a title and at least one source"
	end
	for _, source in ipairs(doc.sources) do
		if not source.url or not source.type then
			return false, "document " .. doc.title .. " has a source without url or type"
		end
	end
	return true, doc
end

for _, doc in ipairs(assert(module:get_option("tos_documents"), "tos_documents option is required")) do
	local ok, doc_or_err = validate_doc(doc)
	if not ok then
		error("invalid TOS document: "..doc_or_err)
	end
	documents:push(doc);
end

local function send_tos_push(session)
	local to = session.username .. "@" .. session.host .. "/" .. session.resource;
	local push = st.message({
		type = "headline",
		to = to,
	}, "In order to continue to use the service, you have to accept the current version of the Terms of Service.");
	local tos = push:tag("tos-push", { xmlns = "urn:xmpp:tos:0" }):tag("tos", { version = tos_version });
	for _, doc in ipairs(documents) do
		local doc_tag = tos:tag("document"):text_tag("title", doc.title);
		for _, source in ipairs(doc.sources) do
			doc_tag:tag("source", { url = source.url,  type = source.type }):up();
		end
		doc_tag:up();
	end
	tos:up():up();
	module:send(push);
end

local function check_tos(event)
	local user = event.origin.username
	assert(user)
	local tos_status = status_storage:get(user)
	if tos_status and tos_status.version and tos_status.version == tos_version then
		module:log("debug", "user %s has signed the current tos", user);
		return
	end
	module:log("debug", "user %s has not signed the current tos, sending tos push", user);
	send_tos_push(event.origin)
end

local function handle_accept_tos_iq(event)
	local user = event.origin.username;
	assert(user);
	local accept = event.stanza.tags[1];
	local version = accept.attr["version"];
	module:log("debug", "user %s has accepted ToS version %s", user, version);
	if version ~= tos_version then
		local reply = st.error_reply(event.stanza, "modify", "not-allowed", "Only the most recent version of the ToS can be accepted");
		module:log("debug", "%s is not the most recent version (%s), rejecting", version, tos_version);
		event.origin.send(reply);
		return true;
	end

	status_storage:set(user, { version = tos_version });
	local reply = st.reply(event.stanza);
	event.origin.send(reply);
	return true;
end

module:hook("presence/initial", check_tos, -100);
module:hook("iq-set/bare/urn:xmpp:tos:0:accept", handle_accept_tos_iq);
