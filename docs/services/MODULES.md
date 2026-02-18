# Module Management Across ATL Chat Services

This document explains how modules (plugins, extensions) are handled for UnrealIRCd and Prosody in the atl.chat stack.

For more IRC-specific details (runtime commands, troubleshooting, etc.), see [IRC MODULES.md](irc/MODULES.md).

---

## Overview

| Service   | Module Type        | Config File              | When Loaded | Location in Image                    |
|-----------|--------------------|--------------------------|-------------|-------------------------------------|
| UnrealIRCd| Third-party        | `third-party-modules.list` | Build time  | Compiled into `/home/unrealircd/unrealircd/` |
| Prosody   | Community modules  | `modules.list`           | Build time  | `/usr/local/lib/prosody/prosody-modules-enabled/` |
| Prosody   | Custom plugins     | N/A                      | Runtime     | `/var/lib/prosody/custom_plugins/` (volume) |

---

## UnrealIRCd Modules

### Flow

1. **Config**: `apps/unrealircd/third-party-modules.list` lists modules to install (one per line, `#` for comments).
2. **Build**: During `docker build`, the Containerfile runs `unrealircd module install <name>` for each module.
3. **Runtime**: Modules are compiled C code; they live in the UnrealIRCd install directory. No symlinks or separate dirs.

### Adding/Removing Modules

1. Edit `apps/unrealircd/third-party-modules.list`.
2. Rebuild the image: `docker compose build atl-irc-server`.

### Key Paths

- **Config**: `apps/unrealircd/third-party-modules.list`
- **Catalog**: https://modules.unrealircd.org/
- **List installed**: `docker compose exec atl-irc-server unrealircd module list`

---

## Prosody Modules

### Two-Layer System

Prosody uses a **source** directory and an **enabled** directory:

| Directory                | Purpose                                                                 |
|--------------------------|-------------------------------------------------------------------------|
| `prosody-modules`        | Full clone of community modules from https://hg.prosody.im/prosody-modules/ |
| `prosody-modules-enabled`| Symlinks to only the modules we want (from `modules.list`)              |

Prosody loads modules from `prosody-modules-enabled` via `plugin_paths` in `prosody.cfg.lua`.

### Build-Time Flow (Docker)

1. **Config**: `apps/prosody/modules.list` lists which community modules to enable.
2. **Containerfile** (builder stage):
   - Clones full `prosody-modules` repo from Mercurial.
   - Deletes modules *not* in `modules.list` (reduces image size).
   - Creates `prosody-modules-enabled/` with symlinks: `mod_foo` → `../prosody-modules/mod_foo`.
   - Handles community modules with subdirs (e.g. `mod_foo/foo/mod_foo.lua`).
   - Creates empty LuaRocks manifest at `prosody-modules-enabled/lib/luarocks/rocks/manifest` to silence modulemanager errors.
3. **Runtime stage**: Copies both dirs into `/usr/local/lib/prosody/` in the image.

### Runtime Configuration

- **plugin_paths** in `prosody.cfg.lua`:
  - `/usr/local/lib/prosody/prosody-modules-enabled` (community modules from image)
  - `/var/lib/prosody/custom_plugins` (custom Lua plugins; persisted via volume)
- **modules_enabled**: List in `prosody.cfg.lua` of which modules to actually load. A module can exist in `prosody-modules-enabled` but only load if listed in `modules_enabled`.

### Adding/Removing Community Modules

1. Edit `apps/prosody/modules.list` (add or remove module names).
2. Rebuild: `docker compose build atl-xmpp-server`.

### Custom Plugins (Runtime)

- Place Lua files in `/var/lib/prosody/custom_plugins/` (mounted from host if you add a volume).
- Add the module name to `modules_enabled` in `prosody.cfg.lua`.
- No image rebuild needed; restart Prosody to load.

---

## LuaRocks Manifest (Prosody)

Prosody’s modulemanager looks for a LuaRocks manifest at `prosody-modules-enabled/lib/luarocks/rocks/manifest`. We don’t use LuaRocks; we use symlinks from the Mercurial repo. To avoid "Could not load manifest" errors, the Containerfile creates an empty manifest:

```
commands = {}
dependencies = {}
modules = {}
repository = {}
```

---

## Summary

| Question                               | Answer                                                                 |
|----------------------------------------|------------------------------------------------------------------------|
| Do we need `prosody-modules` in the image? | Yes. It’s the source for community modules.                           |
| Do we need `prosody-modules-enabled` in the image? | Yes. Prosody loads from here via `plugin_paths`.                  |
| Do we need them on the host?            | No. Modules are baked into the image at build time.                |
| How to add a Prosody community module? | Add to `modules.list`, rebuild image.                                 |
| How to add an UnrealIRCd third-party module? | Add to `third-party-modules.list`, rebuild image.               |
