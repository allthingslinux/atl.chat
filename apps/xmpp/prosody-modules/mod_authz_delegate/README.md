---
summary: Authorization delegation
rockspec: {}
...

This module allows delegating authorization questions (role assignment and
role policies) to another host within prosody.

The primary use of this is for a group of virtual hosts to use a common
authorization database, for example to allow a MUC component to grant
administrative access to an admin on a corresponding user virtual host.

## Configuration

The following example will make all role assignments for local and remote JIDs
from domain.example effective on groups.domain.example:

```
VirtualHost "domain.example"

Component "groups.domain.example" "muc"
    authorization = "delegate"
    authz_delegate_to = "domain.example"
```
