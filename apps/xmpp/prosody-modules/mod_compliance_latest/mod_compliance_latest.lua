local success, err = pcall(function() module:depends("compliance_2023") end)

if not success then
module:log_status( "error", "Error, can't load module: mod_compliance_2023. Is this module downloaded into a folder readable by prosody?" )
return false
end
