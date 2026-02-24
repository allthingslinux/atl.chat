# Update AGENTS.md Files

## Overview

**When invoked:** Compare all project AGENTS.md files against the live codebase; **fix existing** and **create missing** as needed. No report — apply edits directly. End with a brief summary of changes in conventional commit form.

**Scope:** All project AGENTS.md — exclude `.cursor/skills/*/AGENTS.md` (external skill repos).

**Included:** `find . -name AGENTS.md -not -path './.cursor/*' -not -path './node_modules/*'` — root, `apps/*`, `docs/`, `infra/`, `scripts/`, `tests/`, anywhere.

## Project Layout (Monorepo)

- **Root:** `justfile` (mods: `xmpp`, `irc`, `web`, `bridge`), `pyproject.toml`, `package.json`, `pnpm-workspace.yaml`
- **apps:** `atheme/`, `bridge/`, `gamja/`, `prosody/`, `unrealircd/`, `web/`, `webpanel/` — each may have its own `justfile` via `mod`
  - `unrealircd/` — IRC server (config, Lua)
  - `atheme/` — IRC services (NickServ, ChanServ, etc.)
  - `prosody/` — XMPP server (Lua config)
  - `webpanel/` — UnrealIRCd web admin
  - `web/` — Next.js web app
  - `bridge/` — Discord↔IRC↔XMPP bridge (Python)
  - `gamja/` — IRC web client (planned)
- **infra:** `compose/` (irc, xmpp, bridge, cert-manager, networks)
- **scripts:** `init.sh`, `prepare-config.sh`, `gencloak-update-env.sh`
- **tests:** Root `tests/` + per-app `tests/` (e.g. `apps/bridge/tests/`)

## Research-First (MANDATORY)

Before making any edit, verify against the actual codebase:

- **Paths** — Confirm `apps/*/`, `src/`, `infra/`, `scripts/` exist and match documented structure
- **Structure** — List actual dirs/files; don't assume. Compare documented structure with filesystem
- **Commands** — Cross-reference root `justfile`, app `justfile` (via `mod`), `pyproject.toml`, `package.json`; don't assume command names exist
- **Patterns** — Read existing AGENTS.md style (Scope, Related, Finish the Task, Files tables); preserve or match it

Don't fix what you think is wrong — verify it first. Cross-reference code, not docstrings.

## Flow

1. Locate all project AGENTS.md files (`find . -name AGENTS.md` excluding `.cursor/skills`, `node_modules`)
2. **Identify missing AGENTS.md** — directories that should have one but don't (see Create Missing below)
3. For each existing file, **verify** against codebase (paths, structure, commands)
4. **Create** any missing AGENTS.md
5. **Apply fixes** as you find issues — don't batch or defer
6. Self-audit: confirm all edits match reality
7. Summarize what was changed at the end

## What to Fix

### 1. Locate Files

**Existing:** Run `find . -name AGENTS.md -not -path './.cursor/*' -not -path './node_modules/*'`

**Missing:** Identify directories that warrant AGENTS.md but don't have one:
- App roots: `apps/unrealircd/`, `apps/atheme/`, `apps/prosody/`, `apps/webpanel/`, `apps/web/`, `apps/bridge/`, `apps/gamja/` — if the app has substantial code
- App subdirs: `apps/unrealircd/config/`, `apps/prosody/config/`, `apps/bridge/src/bridge/adapters/`, `apps/web/app/`, etc. — if they contain multiple modules or are a distinct subdomain
- Root `tests/` if it has structure worth documenting
- `docs/` if it has subdirs with distinct responsibilities

**Create missing AGENTS.md** when:
- A directory has 3+ source files or a clear subdomain (e.g. `adapters/`, `gateway/`)
- A sibling directory in the same app already has AGENTS.md (maintain consistency)
- The root `docs/` or an app root has no agent guidance yet — create a minimal one

### 2. Create Missing AGENTS.md

When a directory warrants AGENTS.md but doesn't have one, **create it**:

- **App root** (e.g. `apps/unrealircd/AGENTS.md`, `apps/prosody/AGENTS.md`, `apps/web/AGENTS.md`): Title, Scope, Tech Stack, Repository Structure (from filesystem), Key Commands (from justfile/package.json), Related links to subdir AGENTS.md
- **Subdir** (e.g. `apps/unrealircd/config/`, `apps/prosody/config/`, `apps/bridge/src/bridge/adapters/`): Title, Scope (inherits parent), Files table (list actual files + purpose), Related links to siblings and parent
- **Match existing style** — read any existing AGENTS.md in the repo (e.g. `apps/bridge/AGENTS.md`); for additional patterns see Style Examples (portal, tux) in `~/dev/allthingslinux/`
- **Minimal is fine** — a short Files table and Related links is enough to start; avoid placeholder fluff

### 3. Module Paths — Fix Immediately

- **Python** (bridge): `from bridge.adapters.X` / `from bridge.gateway.Y` match `pyproject.toml` and actual imports
- **Node** (web): Import paths match `tsconfig.json` or `package.json` exports
- **Lua** (unrealircd, prosody): Module paths match config files (e.g. `prosody.cfg.lua`, UnrealIRCd modules)
- **Config** (unrealircd, atheme, prosody): Document config file layout, env vars, templates
- Fix relative links between AGENTS.md files (paths must resolve)

### 4. What Lives Here — Fix Immediately

- Add entries for new dirs/files that exist but aren't documented
- Remove entries for dirs/files that no longer exist
- Update file-level docs in module AGENTS.md to match actual files

### 5. Structure & References — Fix Immediately

- Root / app root: Update `Repository Structure` / `Architecture` tree if it doesn't match actual layout
- Root: Add/update Documentation Duties in Finish the Task if missing
- Per-dir: Fix broken links to other AGENTS.md (paths, add missing)
- Per-dir: Fix `> Scope:` if wrong; add inheritance wording if absent — **only when the project already uses this pattern**
- Per-dir: Add Finish the Task with module-appropriate update rule if missing — **only when the project already uses this pattern**

### 6. Commands & Paths

- Remove or correct any `just *` commands that don't exist in root `justfile` or app `justfile` (loaded via `mod` — e.g. `just irc`, `just xmpp`, `just web`, `just bridge`)
- Remove or correct any `uv run *` / `pnpm *` / `docker compose *` commands that don't exist in `pyproject.toml` / `package.json` / app config
- Fix event/class names if they've moved or been renamed

## Do Not

- Produce an audit report or pass/fail summary
- List issues without fixing — fix in the same pass
- Skip fixes to "report later"
- Add Scope / Related / Finish the Task if the project doesn't use that pattern — match existing style
- Add unrelated improvements or "enhancements" — only fix what's wrong

## Error Handling

| Situation | Action |
|-----------|--------|
| AGENTS.md missing for a module that should have one | **Create it** — see Create Missing AGENTS.md above; match existing style from siblings |
| Broken link to non-existent AGENTS.md | Fix path or remove link; don't create placeholder files |
| Ambiguous module path (could resolve multiple ways) | Verify in `pyproject.toml`, `tsconfig.json`, or actual imports in codebase |
| Generated block (`<!-- *-AGENTS-MD-* -->`) | Don't modify; leave as-is |

## Self-Audit (Before Summarizing)

- [ ] All module/file paths match actual filesystem (per app: unrealircd, atheme, prosody, webpanel, web, bridge, gamja)
- [ ] What Lives Here / Files / Repository Structure entries match reality
- [ ] Newly created AGENTS.md match existing style and have valid Related links
- [ ] No new patterns introduced that contradict existing AGENTS.md style
- [ ] Edits verified against codebase — not assumed

## End

After applying all fixes, output a short summary:

```
docs(agents): update AGENTS.md — add apps/unrealircd, apps/prosody, apps/web AGENTS.md; sync structure across apps
```

(or similar conventional commit style)

## Style Examples (Sibling Projects)

When creating or matching style, reference AGENTS.md in `~/dev/allthingslinux/`:

| Project | Path | Style |
|---------|------|-------|
| **portal** | `portal/AGENTS.md` | Scope, Quick Facts, Repository Structure with subdir links, Import Aliases, Finish the Task |
| **portal** | `portal/src/features/*/AGENTS.md` | What Lives Here (table + key files), Usage Patterns, Related |
| **tux** | `tux/AGENTS.md` | Comprehensive single-app root: Tech Stack, Project Structure (text tree), Code Standards, Quality checks, Conventional Commits |

**Note:** `ui/AGENTS.md` contains `<!-- NEXT-AGENTS-MD-* -->` — generated block; don't modify.

## See Also

- [README.md](../../README.md) — Monorepo overview
- [apps/bridge/AGENTS.md](../../apps/bridge/AGENTS.md) — In-repo example (bridge has AGENTS.md today; other apps should get them)
