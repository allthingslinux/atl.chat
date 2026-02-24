#!/usr/bin/env bash
# Docker workflow helper scripts
# Usage: docker.sh <command> [args...]

set -euo pipefail

generate_pr_version() {
  local pr_number="${1}"
  local sha="${2}"
  local sha_prefix_length="${3:-7}"
  local pr_version="pr-${pr_number}-$(echo "$sha" | cut -c1-"${sha_prefix_length}")"
  echo "version=$pr_version" >> "$GITHUB_OUTPUT"
  echo "Generated PR version: $pr_version"
}

generate_release_version() {
  local github_ref="${1:-}"
  github_ref="${github_ref#"${github_ref%%[![:space:]]*}"}"
  github_ref="${github_ref%"${github_ref##*[![:space:]]}"}"
  local tag_version="${github_ref#refs/tags/}"
  local clean_version="${tag_version#v}"
  local release_version="${clean_version:-dev}"
  echo "version=$release_version" >> "$GITHUB_OUTPUT"
  echo "Generated release version: $release_version"
}

validate_build_config() {
  local git_sha="${1}"
  if [ -z "$git_sha" ]; then
    echo "Error: GIT_SHA is required"
    exit 1
  fi
  echo "✓ Build configuration validated"
}

calculate_source_date_epoch() {
  local commit_timestamp="${1:-}"
  local repo_created_at="${2:-}"
  local source_date_epoch
  if [ -n "$commit_timestamp" ]; then
    source_date_epoch=$(date -d "$commit_timestamp" +%s)
  elif [ -n "$repo_created_at" ]; then
    source_date_epoch=$(date -d "$repo_created_at" +%s)
  else
    source_date_epoch=$(date +%s)
  fi
  echo "epoch=$source_date_epoch" >> "$GITHUB_OUTPUT"
  echo "SOURCE_DATE_EPOCH=$source_date_epoch"
}

generate_build_date() {
  date -u +'%Y-%m-%dT%H:%M:%SZ'
}

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
  generate-pr-version)        generate_pr_version "$@" ;;
  generate-release-version)   generate_release_version "$@" ;;
  validate-build-config)      validate_build_config "$@" ;;
  calculate-source-date-epoch) calculate_source_date_epoch "$@" ;;
  generate-build-date)        generate_build_date "$@" ;;
  *)
    echo "Usage: docker.sh {generate-pr-version|generate-release-version|validate-build-config|calculate-source-date-epoch|generate-build-date} [args...]"
    exit 1
    ;;
esac
