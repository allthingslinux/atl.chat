-- (C) 2011, Marco Cirillo (LW.Org)
-- Exposes stats on HTTP for the stanza counter module.

module:depends("http")

local base_path = module:get_option_string("stanza_counter_basepath", "/stanza-counter/")

-- http handlers

local r_200 = "\n<html>\n<head>\n<title>Prosody's Stanza Counter</title>\n<meta name=\"robots\" content=\"noindex, nofollow\" />\n</head>\n\n<body>\n<h3>Incoming and Outgoing stanzas divided per type</h3>\n<p><strong>Incoming IQs</strong>: %d<br/>\n<strong>Outgoing IQs</strong>: %d<br/>\n<strong>Incoming Messages</strong>: %d<br/>\n<strong>Outgoing Messages</strong>: %d<br/>\n<strong>Incoming Presences</strong>: %d<br/>\n<strong>Outgoing Presences</strong>: %d<p>\n</body>\n\n</html>\n"

local r_err = "\n<html>\n<head>\n<title>Prosody's Stanza Counter - Error %s</title>\n<meta name=\"robots\" content=\"noindex, nofollow\" />\n</head>\n\n<body>\n<h3>%s</h3>\n</body>\n\n</html>\n"

local function res(event, code, body, extras)
	local response = event.response

        if extras then
		for header, data in pairs(extras) do response.headers[header] = data end
	end

	response.status_code = code
	response:send(body)
end

local function req(event)
	if not prosody.stanza_counter then
		local err500 = r_err:format(event, 500, "Stats not found, is the counter module loaded?")
		return res(500, err500) end
	if method == "GET" then
		local forge_res = r_200:format(prosody.stanza_counter.iq["incoming"],
					       prosody.stanza_counter.iq["outgoing"],
					       prosody.stanza_counter.message["incoming"],
					       prosody.stanza_counter.message["outgoing"],
					       prosody.stanza_counter.presence["incoming"],
					       prosody.stanza_counter.presence["outgoing"])
		return res(event, 200, forge_res)
	else
		local err405 = r_err:format(405, "Only GET is supported")
		return res(event, 405, err405, {["Allow"] = "GET"})
	end
end

-- initialization.

module:provides("http", {
	default_path = base_path,
        route = {
                ["GET /"] = req,
		["POST /"] = req
        }
})
