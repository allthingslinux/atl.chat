# relaymsg-atl — atl.chat fork

Fork of [Valware's relaymsg](https://github.com/ValwareIRC/valware-unrealircd-mods) with `require-separator` / `allow-clean-nicks` config options for stateless bridging.

## Why relaymsg-atl (not third/relaymsg)?

UnrealIRCd's build runs `unrealircd -m upgrade` which **overwrites** any `third/relaymsg` source with the upstream version from unrealircd-contrib. Using `third/relaymsg-atl` avoids this: the module manager leaves unknown modules untouched.

## Files

| File | Purpose |
|------|---------|
| `relaymsg-atl.c` | Built into image as `third/relaymsg-atl` |

## Config

```conf
loadmodule "third/relaymsg-atl";

relaymsg {
    hostmask "bridge@example.com";
    require-separator no;   /* optional: allow clean nicks (no / suffix) */
}
```

## Bridge

Set `irc_relaymsg_clean_nicks: true` in bridge config only when `require-separator no` is set above.
