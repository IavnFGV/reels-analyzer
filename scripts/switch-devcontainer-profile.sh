#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  cat <<'USAGE'
Usage:
  ./scripts/switch-devcontainer-profile.sh cpu
  ./scripts/switch-devcontainer-profile.sh gpu
USAGE
  exit 1
fi

profile="$1"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

source_file="${repo_root}/.devcontainer/devcontainer.${profile}.json"
target_file="${repo_root}/.devcontainer/devcontainer.json"

if [[ ! -f "${source_file}" ]]; then
  echo "Unknown profile: ${profile}" >&2
  echo "Expected file not found: ${source_file}" >&2
  exit 1
fi

cp "${source_file}" "${target_file}"
echo "Switched devcontainer profile to: ${profile}"
echo "Rebuild container in VS Code: Dev Containers: Rebuild Container"
