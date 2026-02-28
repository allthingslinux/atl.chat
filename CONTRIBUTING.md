# Contributing to atl.chat

Thanks for your interest in contributing to atl.chat! This document gets you started quickly — the full guide lives in the [docs site](https://docs.atl.chat/docs/development/contributing).

## Quick start

1. **Fork and clone** the repository.
2. **Create a branch** from `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

3. **Set up the dev environment**:

   ```bash
   cp .env.example .env && cp .env.dev.example .env.dev
   just dev
   ```

4. **Make your changes.** Run tests and linting before committing:

   ```bash
   just test
   just lint
   ```

5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/) format:

   ```bash
   feat(bridge): add XMPP MUC room join/part relay
   ```

6. **Push and open a pull request** against `main`.

## Commit conventions

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/). A commitlint hook enforces this automatically. Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`. Use the app name as scope (e.g., `irc`, `bridge`, `web`, `docs`).

Run `pnpm exec cz` for an interactive commit prompt.

## Pre-commit hooks

The repo uses [pre-commit](https://pre-commit.com/) for automated linting and formatting. Set up hooks after cloning:

```bash
uv sync
git config --unset-all core.hooksPath   # if your environment sets this
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

## Code style

| Language | Tool |
|---|---|
| Python | [ruff](https://docs.astral.sh/ruff/) |
| TypeScript/JSX | [Biome](https://biomejs.dev/) via ultracite |
| Lua | [luacheck](https://luacheck.readthedocs.io/) |
| Shell | [shellcheck](https://www.shellcheck.net/) + shfmt |

## Full guide

For the complete contributing guide — PR workflow, branch naming, code review expectations, and detailed code style references — see the [Contributing](https://docs.atl.chat/docs/development/contributing) page in the documentation site.
