--
-- A module to indicate if a MUC message qualifies as historic based on XEP-0334 hints
--

module:depends"muc_mam"

module:log("debug", "Module loaded");

module:hook("muc-message-is-historic", function (event)
  if (event.stanza:get_child("no-store", "urn:xmpp:hints") or
    event.stanza:get_child("no-permanent-store", "urn:xmpp:hints")) then
      module:log("debug", "Not archiving stanza: %s (urn:xmpp:hints)", event.stanza)
    return false
  elseif event.stanza:get_child("store", "urn:xmpp:hints") then
    return true
  else
    return nil
  end
end)
