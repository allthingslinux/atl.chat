module:depends("http")
local pubsub_service = module:depends("pubsub").service
local json = require "util.json"

function handle_GET(event)
	local request, response = event.request, event.response
	local query = request.url.query

	if query:sub(1, 5) ~= "node=" then return 400 end

	local node = query:sub(6)
	local ok, items = pubsub_service:get_items(node, true)

	if not ok then return 404 end
	response.status_code = 200
	return json.encode(items)
end

module:provides("http", {route = {GET = handle_GET}})
