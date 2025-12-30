---
summary: mod_http_upload to mod_http_file_share migrator
labels:
- Stage-Alpha
---


This is a migration script for converting records of [mod_http_upload]
into the format used by the new [mod_http_file_share][doc:modules:mod_http_file_share]
which will be available with Prosody 0.12 (currently in trunk).

# Usage

If your main `VirtualHost` is called "example.com" and your HTTP upload
`Component` is called "upload.example.com", then this command would
convert records of existing uploads via [mod_http_upload] to
[mod_http_file_share][doc:modules:mod_http_file_share]:

```bash
sudo prosodyctl mod_migrate_http_upload upload.example.com example.com
```

In order to preserve URLs you will need to configure the
[path][doc:http#path_configuration] to be the same as mod_http_upload:

```lua
Component "upload.example.com" "http_file_share"
http_paths = {
    file_share = "/upload"
}
```
