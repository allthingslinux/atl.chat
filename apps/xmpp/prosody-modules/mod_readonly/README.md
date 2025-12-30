This module blocks configured queries that change server state.

E.g. to make vCard storage read-only:

``` lua
readonly_stores = {
	vcard = { "vcard-temp", "vCard" };
}
```
