-- this module is deprecated, log an error and load the superseding modules instead
module:depends"smacks"
module:depends"nooffline_noerror"

module:log("error", "mod_smacks_noerror is deprecated! Just use mod_smacks and load mod_nooffline_noerror if you explicitly disabled offline storage (mod_offline)");