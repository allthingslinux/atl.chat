---
labels:
- 'Stage-Alpha'
summary: Cloud Native Storage
...

::: {.alert .alert-danger}
This storage driver is fully async and requires that all storage access happens in an async-compatible context. As of 2023-10-14 this work in Prosody
is not yet complete. For now, this module is primarily suited for testing and finding areas where async work is incomplete.
:::

::: {.alert .alert-danger}
The data layout in S3 is not final and may change at any point in incompatible ways.
:::

This module provides storage in Amazon S3 compatible things. It has been tested primarily with MinIO.

``` lua
s3_bucket = "prosody"
s3_base_uri = "http://localhost:9000"
s3_region = "us-east-1"
s3_access_key = "YOUR-ACCESS-KEY-HERE"
s3_secret_key = "YOUR-SECRET-KEY-HERE"
```
