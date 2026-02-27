# CI/CD Pipeline

This guide covers the comprehensive CI/CD pipeline for IRC.atl.chat, including automated testing, building, security scanning, and deployment workflows using GitHub Actions.

## Overview

### Pipeline Architecture

IRC.atl.chat uses GitHub Actions for a complete CI/CD pipeline with the following workflows:

```
CI/CD Workflows:
├── ci.yml           - Continuous Integration (linting, validation)
├── docker.yml       - Docker building and publishing
├── security.yml     - Security scanning and vulnerability checks
├── release.yml      - Release automation and tagging
├── deploy.yml       - Deployment automation
├── maintenance.yml  - Automated maintenance tasks
└── cleanup.yml      - Cleanup and artifact management
```

### Key Features

- **Multi-stage validation**: Linting, testing, security scanning
- **Automated building**: Docker image creation and publishing
- **Security-first**: Vulnerability scanning and secret detection
- **Release automation**: Semantic versioning and changelog generation
- **Maintenance automation**: Dependency updates and cleanup

## CI Workflow (ci.yml)

### Purpose

Primary CI workflow that runs on every push and pull request to validate code quality, security, and functionality.

### Triggers

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### Jobs Overview

#### 1. File Detection (`changes`)

Detects which types of files have changed to optimize workflow execution:

```yaml
jobs:
  changes:
    outputs:
      docker: ${{ steps.docker_changes.outputs.any_changed }}
      shell: ${{ steps.shell_changes.outputs.any_changed }}
      workflows: ${{ steps.workflow_changes.outputs.any_changed }}
      yaml: ${{ steps.yaml_changes.outputs.any_changed }}
```

**Detection Rules:**

- **Docker**: Containerfile, Dockerfile, compose.yaml, .dockerignore
- **Shell**: *.sh,*.bash, *.zsh, scripts/ directory
- **Workflows**: .github/workflows/ files
- **YAML**: *.yml,*.yaml, .github/ files

#### 2. Shell Linting (`shell`)

Runs when shell scripts change (excluding Renovate bot):

```yaml
shell:
  needs: [changes]
  if: needs.changes.outputs.shell == 'true' && github.actor != 'renovate[bot]'
```

**Tools:**

- **shellcheck**: Static analysis for shell scripts
- **shfmt**: Shell script formatting and validation

#### 3. Workflow Validation (`workflows`)

Validates GitHub Actions workflow syntax:

```yaml
workflows:
  needs: [changes]
  if: needs.changes.outputs.workflows == 'true' && github.actor != 'renovate[bot]'
```

**Tools:**

- **actionlint**: GitHub Actions workflow linter

#### 4. Docker Linting (`docker`)

Validates Docker and container configurations:

```yaml
docker:
  needs: [changes]
  if: needs.changes.outputs.docker == 'true' && github.actor != 'renovate[bot]'
```

**Tools:**

- **hadolint**: Dockerfile linter with security checks
- **dclint**: Docker Compose linter

#### 5. YAML Validation (`yaml`)

Validates YAML syntax and structure:

```yaml
yaml:
  needs: [changes]
  if: needs.changes.outputs.yaml == 'true' && github.actor != 'renovate[bot]'
```

**Tools:**

- **yamllint**: YAML syntax and style validation

#### 6. Security Scanning (`security`)

Runs security checks on all changes:

```yaml
security:
  needs: [changes]
  if: always() && github.actor != 'renovate[bot]'
```

**Tools:**

- **gitleaks**: Secret detection and credential scanning

## Docker Workflow (docker.yml)

### Purpose

Handles Docker image building, validation, publishing, and maintenance for all IRC.atl.chat services.

### Triggers

```yaml
on:
  push:
    tags: [v*]          # Release tags
  pull_request:
    branches: [main]    # PR validation
  workflow_dispatch:     # Manual trigger
  schedule:
    - cron: 0 2 15 * *  # Monthly cleanup
```

### Jobs Overview

#### 1. File Detection (`changes`)

Detects Docker-related file changes to optimize builds.

#### 2. Validation (`validate`)

Validates Docker builds without publishing (runs on PRs):

```yaml
validate:
  strategy:
    matrix:
      service: [unrealircd, atheme, atl-irc-webpanel]
```

**Per-Service Validation:**

- Build container images
- Cache layers for faster builds
- Security scanning with Trivy
- PR-specific tagging (pr-123-service)

#### 3. Build & Push (`build`)

Builds and publishes Docker images (runs on releases):

```yaml
build:
  if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
```

**Publishing Strategy:**

- **Registry**: GitHub Container Registry (ghcr.io)
- **Tagging**: Semantic versioning (v1.0.0, v1.0, latest)
- **Metadata**: OCI image labels and annotations
- **Security**: Final image vulnerability scanning

#### 4. Cleanup (`cleanup`)

Monthly maintenance to clean old container images:

```yaml
cleanup:
  if: github.event_name == 'schedule'
```

**Cleanup Policy:**

- Keep last 15 versions
- Remove untagged images
- Automated monthly execution

### Build Configuration

#### Multi-Service Matrix

```yaml
strategy:
  matrix:
    service: [unrealircd, atheme, atl-irc-webpanel]
```

#### Build Arguments

```yaml
build-args: |
  VERSION=${{ steps.release_version.outputs.version }}
  GIT_SHA=${{ github.sha }}
  BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
```

#### Image Metadata

```yaml
labels: |
  org.opencontainers.image.title=IRC.atl.chat - ${{ matrix.service }}
  org.opencontainers.image.description=IRC server infrastructure for All Things Linux Community
  org.opencontainers.image.source=https://github.com/allthingslinux/irc.atl.chat
  org.opencontainers.image.licenses=GPL-3.0
```

## Security Workflow (security.yml)

### Purpose

Comprehensive security scanning and vulnerability assessment.

### Triggers

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: 0 6 * * 1  # Weekly security scan
```

### Security Tools

#### CodeQL Analysis

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: javascript,python,shell

- name: Autobuild
  uses: github/codeql-action/autobuild@v3

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3
```

#### Dependency Scanning

```yaml
- name: Dependency Review
  uses: actions/dependency-review-action@v4
```

#### Container Scanning

```yaml
- name: Container Scan
  uses: anchore/scan-action@v3
  with:
    image: ghcr.io/allthingslinux/irc.atl.chat-atl-irc-server:latest
```

#### Secret Detection

```yaml
- name: Secret Scan
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: main
    head: HEAD
```

## Release Workflow (release.yml)

### Purpose

Automated release creation, versioning, and changelog generation.

### Triggers

```yaml
on:
  push:
    tags: [v*]
```

### Release Process

#### 1. Version Extraction

```yaml
- name: Get Version
  run: |
    VERSION=${GITHUB_REF#refs/tags/v}
    echo "version=$VERSION" >> $GITHUB_OUTPUT
```

#### 2. Changelog Generation

```yaml
- name: Generate Changelog
  uses: tj-actions/git-cliff@v1
  with:
    configuration: cliff.toml
    args: --latest --strip header
  env:
    OUTPUT: CHANGELOG.md
```

#### 3. Release Creation

```yaml
- name: Create Release
  uses: actions/create-release@v1
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  with:
    tag_name: ${{ github.ref }}
    release_name: Release ${{ github.ref }}
    body_path: CHANGELOG.md
```

#### 4. Artifact Publishing

```yaml
- name: Upload Release Assets
  uses: actions/upload-release-asset@v1
  with:
    upload_url: ${{ steps.create_release.outputs.upload_url }}
    asset_path: ./artifacts/release.zip
    asset_name: irc-atl-chat-${{ env.VERSION }}.zip
```

## Deployment Workflow (deploy.yml)

### Purpose

Automated deployment to production environment.

### Triggers

```yaml
on:
  release:
    types: [published]
  workflow_dispatch:
```

### Deployment Strategy

#### Environment-Based Deployment

```yaml
jobs:
  deploy:
    environment: production
    runs-on: ubuntu-latest
```

#### Deployment Steps

```yaml
- name: Deploy to ${{ env.ENVIRONMENT }}
  run: |
    # Update deployment
    kubectl set image deployment/irc-atl-chat \
      irc-atl-chat=ghcr.io/allthingslinux/irc.atl.chat:latest

    # Wait for rollout
    kubectl rollout status deployment/irc-atl-chat

    # Health check
    curl -f https://irc.atl.chat/health
```

## Maintenance Workflow (maintenance.yml)

### Purpose

Automated maintenance tasks including dependency updates and health checks.

### Triggers

```yaml
on:
  schedule:
    - cron: 0 2 * * *  # Daily at 2 AM
  workflow_dispatch:
```

### Maintenance Tasks

#### Dependency Updates

```yaml
- name: Update Dependencies
  uses: renovatebot/github-action@v39
  with:
    configurationFile: .github/renovate.json
```

#### Health Checks

```yaml
- name: Health Check
  run: |
    # Check service status
    curl -f https://irc.atl.chat/status

    # Verify SSL certificate
    openssl s_client -connect irc.atl.chat:6697 -servername irc.atl.chat < /dev/null

    # Check container health
    docker ps --filter "name=irc-atl-chat"
```

#### Log Rotation

```yaml
- name: Rotate Logs
  run: |
    # Compress old logs
    find /var/log/irc -name "*.log" -mtime +7 -exec gzip {} \;

    # Clean old compressed logs
    find /var/log/irc -name "*.gz" -mtime +30 -delete
```

## Cleanup Workflow (cleanup.yml)

### Purpose

Automated cleanup of artifacts, caches, and temporary files.

### Triggers

```yaml
on:
  schedule:
    - cron: 0 3 * * 0  # Weekly on Sunday
  workflow_dispatch:
```

### Cleanup Tasks

#### Artifact Cleanup

```yaml
- name: Clean Artifacts
  uses: actions/github-script@v7
  with:
    script: |
      const artifacts = await github.rest.actions.listArtifactsForRepo({
        owner: context.repo.owner,
        repo: context.repo.repo,
      });

      // Delete artifacts older than 30 days
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - 30);

      for (const artifact of artifacts.data.artifacts) {
        if (new Date(artifact.created_at) < cutoff) {
          await github.rest.actions.deleteArtifact({
            owner: context.repo.owner,
            repo: context.repo.repo,
            artifact_id: artifact.id,
          });
        }
      }
```

#### Cache Cleanup

```yaml
- name: Clean Cache
  run: |
    # Clean GitHub Actions cache
    gh extension install actions/gh-actions-cache
    gh actions-cache delete --all --confirm
```

#### Registry Cleanup

```yaml
- name: Clean Registry
  uses: actions/delete-package-versions@v5
  with:
    package-name: irc-atl-chat-*
    package-type: container
    min-versions-to-keep: 10
```

## Workflow Configuration

### Common Configuration

#### Environment Variables

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  DOCKER_BUILD_SUMMARY: true
  DOCKER_BUILD_CHECKS_ANNOTATIONS: true
```

#### Permissions

```yaml
permissions:
  contents: read
  packages: write
  pull-requests: write
  security-events: write
```

### Reusable Workflows

#### Testing Workflow

```yaml
jobs:
  test:
    uses: ./.github/workflows/test.yml
    secrets: inherit
```

#### Security Workflow

```yaml
jobs:
  security:
    uses: ./.github/workflows/security.yml
    secrets: inherit
```

## Monitoring and Alerts

### Workflow Status Monitoring

#### Status Badges

```markdown
![CI](https://github.com/allthingslinux/irc.atl.chat/workflows/CI/badge.svg)
![Docker](https://github.com/allthingslinux/irc.atl.chat/workflows/Docker/badge.svg)
![Security](https://github.com/allthingslinux/irc.atl.chat/workflows/Security/badge.svg)
```

#### Alert Configuration

```yaml
- name: Notify on Failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Performance Monitoring

#### Workflow Metrics

```yaml
- name: Workflow Telemetry
  uses: codacy/git-version@2.7.1
  with:
    release-branch: main
    dev-branch: develop
```

#### Resource Usage

```yaml
- name: Monitor Resources
  run: |
    # Check runner disk space
    df -h

    # Check runner memory
    free -h

    # Log workflow duration
    echo "Workflow completed in $SECONDS seconds"
```

## Troubleshooting

### Common CI/CD Issues

#### Workflow Not Triggering

```yaml
# Check trigger conditions
on:
  push:
    branches: [main]  # Must push to main branch
  pull_request:
    branches: [main]  # Must target main branch
```

#### Permission Errors

```yaml
# Check permissions
permissions:
  contents: read      # Required for checkout
  packages: write     # Required for GHCR publishing
  pull-requests: write # Required for reviews
```

#### Cache Issues

```yaml
# Clear cache manually
gh actions-cache delete --all --confirm

# Check cache usage
gh actions-cache list
```

#### Build Failures

```yaml
# Check build logs
# Look for:
# - Missing dependencies
# - Network timeouts
# - Disk space issues
# - Permission problems
```

### Debug Mode

#### Enable Debug Logging

```yaml
- name: Enable Debug
  run: |
    echo "ACTIONS_RUNNER_DEBUG=true" >> $GITHUB_ENV
    echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV
```

#### Manual Workflow Dispatch

```yaml
# Trigger workflow manually
gh workflow run ci.yml --ref main
```

## Best Practices

### Workflow Organization

#### Naming Conventions

```yaml
# Consistent naming
name: CI Pipeline          # Clear, descriptive names
name: Docker Build         # Specific to function
name: Security Scan        # Purpose-driven naming
```

#### Job Structure

```yaml
jobs:
  lint:                    # Fast, parallel jobs first
  test:                    # Core validation
  build:                   # Artifact creation
  deploy:                  # Deployment (conditional)
```

### Security Best Practices

#### Secret Management

```yaml
# Use GitHub secrets
secrets:
  DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}
  SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}

# Never hardcode secrets
# Use environment variables for non-sensitive config
```

#### Access Control

```yaml
# Restrict workflow triggers
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  # No manual triggers for sensitive workflows
```

### Performance Optimization

#### Caching Strategy

```yaml
- name: Cache Dependencies
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}

- name: Cache Docker Layers
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
```

#### Parallel Execution

```yaml
strategy:
  matrix:
    service: [unrealircd, atheme, webpanel]
  max-parallel: 3  # Control parallelism
```

## Integration with External Tools

### Renovate Integration

#### Dependency Updates

```json
{
  "extends": ["config:base"],
  "schedule": ["before 4am on Monday"],
  "labels": ["dependencies"],
  "reviewers": ["team:maintainers"]
}
```

### CodeQL Integration

#### Advanced Configuration

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: javascript,python
    queries: security-and-quality
```

### Slack Integration

#### Notification Configuration

```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,commit,author,action,eventName,ref,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

## Related Documentation

- [TESTING.md](TESTING.md) - Test suite documentation
- [DOCKER.md](DOCKER.md) - Container setup details
- [README.md](../README.md) - Quick start guide
- [GitHub Actions Documentation](https://docs.github.com/en/actions) - Official docs
