local jid = require "util.jid"
local st = require "util.stanza"

local CHATSTATES_NS = "http://jabber.org/protocol/chatstates"
local domains = module:get_option_set("drop_chatstates_domains", {})

local function handle_pre_message(event)
    local stanza = event.stanza
    local to_host = jid.host(stanza.attr.to)
    if not to_host or not domains:contains(to_host) then return end
    if stanza:get_child(nil, CHATSTATES_NS) then return true end
end

module:hook("pre-message/bare", handle_pre_message)
