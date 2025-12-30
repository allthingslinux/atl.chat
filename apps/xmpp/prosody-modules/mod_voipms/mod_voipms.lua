local http = require "net.http"
local json = require "util.json"
local st = require "util.stanza"

local api_username = module:get_option_string("voipms_api_username")
local api_password = module:get_option_string("voipms_api_password")
local query_key = module:get_option("voipms_query_key")
local jid_map = module:get_option("voipms_jid_map") or {}
local rest_endpoint = "https://voip.ms/api/v1/rest.php"

if not api_username or not api_password or not query_key then
    module:log("error", "Missing required config values (voipms_api_username, voipms_api_password, voipms_query_key)")
    return
end

for jid, dids in pairs(jid_map) do
    if type(dids) ~= "table" then
        module:log("error", "Invalid voipms_jid_map entry for %s: must be a list of DIDs", jid)
        return
    end
end

module:depends("http")

local function normalize_number(num)
    if not num then return nil end
    if num:sub(1, 1) ~= "+" then
        return "+1" .. num
    end
    return num
end

local function extract_query_key(event)
    return (event.request.url.query or ""):match("key=([^&]+)")
end

module:provides("http", {
    route = {
        ["POST"] = function(event)
            local req = event.request
            local body = req.body or ""

            if extract_query_key(event) ~= query_key then
                module:log("warn", "Unauthorized webhook: missing or invalid key")
                return { status_code = 403 }
            end

            local json_payload, err = json.decode(body)
            if not json_payload then
                module:log("warn", "Invalid JSON: %s", err or "unknown error")
                return { status_code = 400 }
            end

            local payload = json_payload.data and json_payload.data.payload
            if not payload then
                module:log("warn", "Missing payload in JSON")
                return { status_code = 400 }
            end

            local from = payload.from and payload.from.phone_number
            local to_list = payload.to or {}
            local to = #to_list > 0 and to_list[1].phone_number or nil

            if not from or not to then
                module:log("warn", "Missing phone numbers (from: %s, to: %s)", tostring(from), tostring(to))
                return { status_code = 400 }
            end

            local normalized_from = normalize_number(from)
            local normalized_to = normalize_number(to)
            local target_jid = nil

            for jid, dids in pairs(jid_map) do
                for _, did in ipairs(dids) do
                    if normalize_number(did) == normalized_to then
                        target_jid = jid
                        break
                    end
                end
                if target_jid then break end
            end

            if not target_jid then
                module:log("warn", "No JID mapping for DID %s", normalized_to)
                return { status_code = 404 }
            end

            local message_text = payload.text or ""
            local from_jid = normalized_from .. "%" .. normalized_to .. "@" .. module.host

            if message_text ~= "" then
                local text_message = st.message({
                    from = from_jid,
                    to = target_jid,
                    type = "chat"
                }):tag("body"):text(message_text):up()

                module:send(text_message)
                module:log("info", "Delivered text SMS from %s to %s", normalized_from, target_jid)
            end

            if payload.media and #payload.media > 0 then
                for _, media_item in ipairs(payload.media) do
                    if media_item.url then
                        local media_message = st.message({
                            from = from_jid,
                            to = target_jid,
                            type = "chat"
                        })
                        :tag("body"):text(media_item.url):up()
                        :tag("x", { xmlns = "jabber:x:oob" })
                            :tag("url"):text(media_item.url):up()
                        :up()

                        module:send(media_message)
                        module:log("info", "Delivered media URL from %s to %s: %s", normalized_from, target_jid, media_item.url)
                    end
                end
            end

            return { status_code = 204 }
        end
    }
})

module:hook("message/bare", function(event)
    local stanza = event.stanza
    if stanza.attr.type ~= "chat" then return end

    local from_jid = stanza.attr.from
    local to_jid = stanza.attr.to
    local body = stanza:get_child_text("body")
    if not body or body == "" then return end

    local to_node = to_jid:match("^(.-)@")
    if not to_node then
        module:log("warn", "Malformed JID in message.to: %s", to_jid)
        return
    end

    local dst_number, from_number = to_node:match("([^%%]+)%%(.+)")
    if not dst_number or not from_number then
        module:log("warn", "Malformed to JID node: %s", to_node)
        return
    end

    dst_number = normalize_number(dst_number)
    from_number = normalize_number(from_number)

    local media_urls = {}
    for line in body:gmatch("[^\r\n]+") do
        if line:match("^https?://") then
            table.insert(media_urls, line)
        end
    end

    local method = (#media_urls > 0) and "sendMMS" or "sendSMS"
    local query = {
        api_username = api_username,
        api_password = api_password,
        method = method,
        did = from_number,
        dst = dst_number,
        message = body
    }

    if method == "sendMMS" then
        for i, url in ipairs(media_urls) do
            query["media_url[" .. (i - 1) .. "]"] = url
        end
    end

    local query_str = http.formencode(query)

    http.request(rest_endpoint .. "?" .. query_str, {
        method = "GET";
    }, function(response_body, code)
        if code == 200 then
            local resp, err = json.decode(response_body)
            if not resp or resp.status ~= "success" then
                local err_msg = string.format("Failed to send %s: %s", method, err or (resp and resp.status) or "unknown")
                module:log("error", "%s", err_msg)
                local err_reply = st.error_reply(stanza, "cancel", "remote-server-error", err_msg)
                module:send(err_reply)
            else
                module:log("info", "Sent %s from %s to %s", method, from_number, dst_number)
            end
        else
            local err_msg = string.format("HTTP error sending %s: code %s", method, tostring(code))
            module:log("error", "%s", err_msg)
            local err_reply = st.error_reply(stanza, "cancel", "remote-server-error", err_msg)
            module:send(err_reply)
        end
    end)

    return true
end)
