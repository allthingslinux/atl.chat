# CI/CD Pipeline

Automated testing and deployment for atl.chat.

## Workflows

See `.github/workflows/`:

- **ci.yml** – Lint, security scan, Docker builds (per app)
- **docker.yml** – Reusable Docker image build
- **security.yml** – Trivy/Gitleaks scans

## Triggers

- `main`, `develop` – Push and PR
- Path filters: changes in `apps/irc/**`, `apps/xmpp/**`, etc. run only relevant jobs

## Local Checks

```bash
just lint      # Lefthook pre-commit
just irc test  # IRC pytest
```
