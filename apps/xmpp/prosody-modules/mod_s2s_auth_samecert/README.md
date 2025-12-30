This module authenticates server-to-server connections by looking for an already established connection that uses the exact same certificate, reusing
the earlier validation results and letting Prosody skip performing slower validation methods such as [POSH][mod_s2s_auth_posh] twice.
