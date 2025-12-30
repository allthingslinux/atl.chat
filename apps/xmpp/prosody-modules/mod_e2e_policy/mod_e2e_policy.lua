local st = require "util.stanza";
local jid_bare = require "util.jid".bare;
local host = module.host;
local e2e_policy_chat = module:get_option_string("e2e_policy_chat", "optional"); -- possible values: none, optional and required
local e2e_policy_muc = module:get_option_string("e2e_policy_muc", "optional"); -- possible values: none, optional and required
local e2e_policy_whitelist = module:get_option_set("e2e_policy_whitelist", {  }); -- make this module ignore messages sent to and from this JIDs or MUCs

local e2e_policy_message_optional_chat = module:get_option_string("e2e_policy_message_optional_chat", "For security reasons, OMEMO, OTR or PGP encryption is STRONGLY recommended for conversations on this server.");
local e2e_policy_message_required_chat = module:get_option_string("e2e_policy_message_required_chat", "For security reasons, OMEMO, OTR or PGP encryption is required for conversations on this server.");
local e2e_policy_message_optional_muc = module:get_option_string("e2e_policy_message_optional_muc", "For security reasons, OMEMO, OTR or PGP encryption is STRONGLY recommended for MUC on this server.");
local e2e_policy_message_required_muc = module:get_option_string("e2e_policy_message_required_muc", "For security reasons, OMEMO, OTR or PGP encryption is required for MUC on this server.");

function warn_on_plaintext_messages(event)
    -- check if JID is whitelisted
    if e2e_policy_whitelist:contains(jid_bare(event.stanza.attr.from)) or e2e_policy_whitelist:contains(jid_bare(event.stanza.attr.to)) then
        return nil;
    end
    local body = event.stanza:get_child_text("body");
    -- do not warn for status messages
    if not body or event.stanza.attr.type == "error" then
        return nil;
    end
    -- check otr
    if body and body:sub(1,4) == "?OTR" then
        return nil;
    end
    -- check omemo https://xmpp.org/extensions/inbox/omemo.html
    if event.stanza:get_child("encrypted", "eu.siacs.conversations.axolotl") or event.stanza:get_child("encrypted", "urn:xmpp:omemo:0") then
        return nil;
    end
    -- check xep27 pgp https://xmpp.org/extensions/xep-0027.html
    if event.stanza:get_child("x", "jabber:x:encrypted") then
        return nil;
    end
    -- check xep373 pgp (OX) https://xmpp.org/extensions/xep-0373.html
    if event.stanza:get_child("openpgp", "urn:xmpp:openpgp:0") then
        return nil;
    end
    -- no valid encryption found
    if e2e_policy_chat == "optional" and event.stanza.attr.type ~= "groupchat" then
        event.origin.send(st.message({ from = host, to = event.stanza.attr.from, type = "headline" }, e2e_policy_message_optional_chat));
    end
    if e2e_policy_chat == "required" and event.stanza.attr.type ~= "groupchat" then
        return event.origin.send(st.error_reply(event.stanza, "modify", "policy-violation", e2e_policy_message_required_chat));
    end
    if e2e_policy_muc == "optional" and event.stanza.attr.type == "groupchat" then
        event.origin.send(st.message({ from = host, to = event.stanza.attr.from, type = "headline" }, e2e_policy_message_optional_muc));
    end
    if e2e_policy_muc == "required" and event.stanza.attr.type == "groupchat" then
        return event.origin.send(st.error_reply(event.stanza, "modify", "policy-violation", e2e_policy_message_required_muc));
    end
end

module:hook("pre-message/bare", warn_on_plaintext_messages, 300);
module:hook("pre-message/full", warn_on_plaintext_messages, 300);
module:hook("pre-message/host", warn_on_plaintext_messages, 300);
