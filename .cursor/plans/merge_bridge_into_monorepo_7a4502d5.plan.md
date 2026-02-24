---
name: Merge Bridge Into Monorepo
overview: Commit pending bridge changes (dev/prod irc_tls_verify support), then merge the bridge repo into atl.chat as regular files while preserving full bridge commit history via git subtree merge.
todos: []
isProject: false
---

# Merge Bridge Repo Into atl.chat Monorepo

## Current State

- **Bridge submodule** at `apps/bridge` (from `git@github.com:allthingslinux/bridge.git`)
- **Uncommitted bridge changes** (5 files): dev/prod `irc_tls_verify` support, `IRCPuppetManager`/`IRCPuppet` updates, config template
- **Uncommitted atl.chat changes**: `prepare-config.sh`, `bridge.yaml`, `.env.example` (bridge env vars)
- Bridge has its own CI (`.github/workflows/`), `pyproject.toml`, `Containerfile`, tests

## Phase 1: Commit Bridge Changes (Pre-Merge)

Commit the pending bridge work **inside the bridge submodule** so it becomes part of bridge history. If using tomono, also commit atl.chat changes first—tomono runs `git checkout .` and would discard uncommitted work.

1. **In `apps/bridge`**:
  - `git add config.template.yaml src/bridge/adapters/irc.py src/bridge/adapters/irc_puppet.py src/bridge/config.py tests/test_irc_puppet.py`
  - `git commit -m "feat(irc): add irc_tls_verify for dev/prod self-signed cert support"`
  - `git push origin main` (recommended so merge fetches latest)
2. **In atl.chat** (parent): Commit integration changes before tomono (prepare-config.sh, bridge.yaml, .env.example). Optionally update submodule pointer:
  - `git add apps/bridge`
  - `git commit -m "chore(bridge): update submodule for irc_tls_verify"`
   Or defer this—the subtree merge will bring in the latest bridge content anyway.

## Phase 2: Merge Bridge (Preserve History)

Two options: **tomono** (recommended, from [tomono.0brg.net](https://tomono.0brg.net)) or **manual subtree merge**. tomono uses the same technique (explicit move commit + merge) and handles branches; it runs `git checkout .` at the end—commit all changes first.

### Option A: tomono (recommended)

1. **Remove submodule** (after Phase 1):
  - `git submodule deinit -f apps/bridge`
  - `git rm -f apps/bridge`  # removes submodule entry; directory may stay
  - Remove `[submodule "apps/bridge"]` block from `[.gitmodules](.gitmodules)`
  - Delete `.git/modules/apps/bridge` if it exists
  - Ensure `apps/bridge/` directory is gone (or empty) so merge can populate it
2. **Run tomono** (from parent of atl.chat):

```bash
   cd /path/to/parent/of/atl.chat
   echo "git@github.com:allthingslinux/bridge.git bridge apps/bridge" | MONOREPO_NAME=atl.chat tomono --continue


```

1. **Verify**: `git log --oneline apps/bridge/` shows bridge commits.

### Option B: Manual subtree merge

1. `git remote add bridge-repo git@github.com:allthingslinux/bridge.git && git fetch bridge-repo main`
2. Remove submodule (same as Option A step 1).
3. `git merge -s ours --no-commit --allow-unrelated-histories bridge-repo/main`
4. `git read-tree --prefix=apps/bridge/ -u bridge-repo/main`
5. `git commit -m "Merge bridge repo into apps/bridge (preserving history)"`
6. **Verify**: `git log --oneline apps/bridge/` and `git log --follow apps/bridge/src/bridge/config.py`

## Phase 3: Post-Merge Cleanup

1. **Remove bridge remote** (optional):

```bash
   git remote remove bridge-repo


```

1. **Commit atl.chat integration changes** (if not already committed):
  - `[.env.example](.env.example)` – bridge dev/prod notes
  - `[infra/compose/bridge.yaml](infra/compose/bridge.yaml)` – `ATL_ENVIRONMENT`, `BRIDGE_IRC_TLS_VERIFY`
  - `[scripts/prepare-config.sh](scripts/prepare-config.sh)` – `IRC_TLS_VERIFY` export
2. **Update docs** that mention "submodule":
  - [README.md](README.md), [docs/bridges/README.md](docs/bridges/README.md), [infra/compose/bridge.yaml](infra/compose/bridge.yaml)
  - Replace "submodule" with "in-repo" or remove the note
3. **Bridge CI integration**:
  - Move or adapt `apps/bridge/.github/workflows/`* into atl.chat `.github/workflows/` (e.g. `bridge-ci.yml`) with path filters: `apps/bridge/`**
  - Or keep workflows and ensure checkout uses `path: apps/bridge` where needed
4. **uv workspace** (optional):
  - Add `apps/bridge` to `members` in root [pyproject.toml](pyproject.toml) if you want unified `uv sync`:

```toml
   [tool.uv.workspace]
   members = ["apps/bridge"]


```

## Phase 4: Bridge Repo Disposition

- **Option A**: Archive the bridge repo on GitHub (read-only, link to atl.chat)
- **Option B**: Add a README redirect: "This project has moved to allthingslinux/atl.chat (apps/bridge)"

## Files to Update After Merge


| File                        | Change                                           |
| --------------------------- | ------------------------------------------------ |
| `.gitmodules`               | Remove `[submodule "apps/bridge"]`               |
| `README.md`                 | "submodule" → "in-repo"                          |
| `docs/bridges/README.md`    | Same                                             |
| `infra/compose/bridge.yaml` | Comment: "apps/bridge in-repo"                   |
| `.github/workflows/`        | Add bridge CI with path filter or adapt existing |


## Risk Mitigation

- **Backup**: Create a branch before starting (`git checkout -b merge-bridge-backup`)
- **Submodule pointer**: If you need to roll back, the pre-merge submodule commit is still in bridge repo history
- **Path conflicts**: Subtree merge uses `--prefix=apps/bridge/`; no path clashes expected

