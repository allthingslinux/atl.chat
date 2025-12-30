# Introduction

This module adds support for reading AWS IAM access credentials from EC2 instance metadata,
to allow Prosody modules to gain role-based access to AWS services.

# Configuring

``` {.lua}
modules_enabled = {
    "aws_profile";
}
```

There is no other configuration.

# Usage in other modules

Other modules can import the credentials as a shared table:

``` {.lua}
local aws_credentials = module:shared("/*/aws_profile/credentials");
do_something(aws_credentials.access_key, aws_credentials.secret_key);
```

Note that credentials are time-limited, and will change periodically. The
shared table will automatically be updated. If you need to know when this
happens, you can also hook the `'aws_profile/credentials-refreshed'` event:

``` {.lua}
module:hook_global("aws_profile/credentials-refreshed", function (new_credentials)
  -- do something with new_credentials.access_key/secret_key
end);
```

# Compatibility

Meant for use with Prosody 0.11.x, may work in older versions.
