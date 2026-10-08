#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
size_mb="${1:-512}"

create_payload() {
  local target_dir="$1"
  mkdir -p "${target_dir}/payload"

  if command -v fallocate >/dev/null 2>&1; then
    fallocate -l "${size_mb}M" "${target_dir}/payload/demo.bin"
  else
    dd if=/dev/zero of="${target_dir}/payload/demo.bin" bs=1M count="${size_mb}" status=progress
  fi

  printf 'Created %s/payload/demo.bin (%s MB)\n' "${target_dir}" "${size_mb}"
}

create_payload "${root_dir}/broken"
create_payload "${root_dir}/fixed"
