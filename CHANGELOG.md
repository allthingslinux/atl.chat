# Changelog

This project uses [semantic-release](https://semantic-release.gitbook.io/) to automate versioning and changelog generation. Every merge to `main` triggers a release pipeline that:

1. Analyzes commits using [Conventional Commits](https://www.conventionalcommits.org/) format
2. Determines the next version (major, minor, or patch)
3. Generates release notes from commit messages
4. Updates this file and creates a [GitHub release](https://github.com/allthingslinux/atl.chat/releases)

The release configuration lives in [`.releaserc.json`](.releaserc.json).

## Release history

See [GitHub Releases](https://github.com/allthingslinux/atl.chat/releases) for the full release history and changelogs.
