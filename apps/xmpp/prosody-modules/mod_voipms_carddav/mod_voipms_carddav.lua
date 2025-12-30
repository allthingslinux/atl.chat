local http = require "net.http"
local mime = require "mime"

local carddav_domain = module:get_option("voipms_carddav_domain") or module.host
local carddav_contact_format = module:get_option("voipms_carddav_contact_format") or "[%alias] %name (%type)"
local carddav_jid_map = module:get_option("voipms_carddav_jid_map") or {}
local carddav_sync_interval = module:get_option_number("voipms_carddav_sync_interval") or 86400
local contact_cache = {}

for jid, config in pairs(carddav_jid_map) do
    local carddav = config.carddav
    local dids = config.dids

    local has_dids = dids and type(dids) == "table" and next(dids) ~= nil
    local has_carddav = carddav and type(carddav) == "table"
    local has_url = has_carddav and type(carddav.url) == "string" and carddav.url ~= ""
    local has_username = has_carddav and type(carddav.username) == "string" and carddav.username ~= ""
    local has_password = has_carddav and type(carddav.password) == "string" and carddav.password ~= ""

    if not has_dids then
        module:log("error", "Config for %s missing or empty 'dids' table", jid)
    end
    if not has_carddav then
        module:log("error", "Config for %s missing 'carddav' table", jid)
    else
        if not has_url then
            module:log("error", "Config for %s missing CardDAV URL", jid)
        end
        if not has_username then
            module:log("error", "Config for %s missing CardDAV username", jid)
        end
        if not has_password then
            module:log("error", "Config for %s missing CardDAV password", jid)
        end
    end

    if not (has_dids and has_carddav and has_url and has_username and has_password) then
        module:log("warning", "Incomplete config for %s, skipping", jid)
        carddav_jid_map[jid] = nil
    end
end

local function parse_contacts(response_body)
    local contacts = {}

    local function clean_string(s)
        if not s then return "" end
        s = s:gsub("&#13;", "")
        s = s:gsub("[\r\n]+", "")
        return s
    end

    for vcard_block in response_body:gmatch("BEGIN:VCARD(.-)END:VCARD") do
        local fn = vcard_block:match("FN:(.-)\r?\n") or "Unknown"
        fn = clean_string(fn)

        for tel_type, tel_number in vcard_block:gmatch("TEL;TYPE=([^:]+):([^\r\n]+)") do
            tel_type = clean_string(tel_type):lower()
            tel_number = clean_string(tel_number)

            table.insert(contacts, {
                name = fn,
                phone = {
                    type = tel_type,
                    number = tel_number,
                }
            })
        end
    end

    return contacts
end

local function sync_carddav_contacts()
    for jid, config in pairs(carddav_jid_map) do
        local carddav = config.carddav
        local auth = "Basic " .. mime.b64(carddav.username .. ":" .. carddav.password)

        local headers = {
            ["Content-Type"] = "application/xml; charset=utf-8",
            ["Depth"] = "1",
            ["Authorization"] = auth,
        }

        local body = [[<?xml version="1.0" encoding="UTF-8"?>
        <card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
            <d:prop>
                <d:getetag/>
                <card:address-data/>
            </d:prop>
        </card:addressbook-query>]]

        http.request(carddav.url, {
            method = "REPORT",
            headers = headers,
            body = body,
        }, function(response_body, code)
            if code == 207 then
                contact_cache[jid] = parse_contacts(response_body)
            else
                module:log("error", "CardDAV query failed for %s: HTTP %s", jid, tostring(code))
            end
        end)
    end
end

sync_carddav_contacts()
module:log("debug", "Scheduling contact sync every %d seconds", carddav_sync_interval)
module:add_timer(carddav_sync_interval, sync_carddav_contacts)

module:hook("roster-load", function(event)
    local jid = event.username .. "@" .. event.host
    local roster = event.roster
    local config = carddav_jid_map[jid]
    if not config then return end

    local dids = config.dids
    local carddav = config.carddav
    local contacts = contact_cache[jid]

    if not contacts then return end

    local function format_contact_display(template, values)
        return (template:gsub("%%(%w+)", function(key)
            return values[key] or ""
        end))
    end

    for _, contact in ipairs(contacts) do
        for to_number, to_number_alias in pairs(dids) do
            local from_number = contact.phone.number
            local contact_jid = from_number .. "%" .. to_number .. "@" .. carddav_domain
--            local contact_name = contact.name .. " (" .. contact.phone.type .. ") [" .. to_number_alias .. "]"
            local contact_name = format_contact_display(carddav_contact_format, {
                name = contact.name,
                type = contact.phone.type,
                alias = to_number_alias
            })

            roster[contact_jid] = {
                name = contact_name,
                subscription = "none",
                groups = { [to_number_alias] = true },
                persist = false
            }
        end
    end

    if roster[false] then
        roster[false].version = true
    end
end)
