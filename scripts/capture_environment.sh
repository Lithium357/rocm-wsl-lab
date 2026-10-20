#!/usr/bin/env bash
# Capture a privacy-scrubbed WSL/ROCm environment snapshot. Output is ignored.
set -euo pipefail

usage() {
  echo "Usage: $0 [--out <ignored-artifact-directory>]" >&2
}

out="artifacts/environment-$(date -u +%Y%m%dT%H%M%SZ)"
if [[ $# -gt 0 ]]; then
  [[ $# -eq 2 && $1 == "--out" ]] || { usage; exit 2; }
  out=$2
fi

mkdir -p "$out"
report="$out/environment.txt"

command_block() {
  local title=$1
  shift
  printf '\n## %s\n' "$title"
  "$@" 2>&1 || printf '[unavailable or returned %s]\n' "$?"
}

{
  printf '# ROCm WSL Lab environment snapshot\n'
  printf 'captured_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  command_block "kernel" uname -a
  command_block "os-release" cat /etc/os-release
  command_block "dxg-device" ls -l /dev/dxg
  command_block "ROCDXG-library" sh -c 'ldconfig -p | grep -i librocdxg || true'
  command_block "ROCm-info" rocminfo
  command_block "AMD-SMI" amd-smi version
  command_block "HIP-compiler" hipcc --version
  command_block "Python" python3 --version
} > "$report"

# Remove common identity-bearing path forms before a reviewer ever sees it.
sed -E -i \
  -e 's#/(home|mnt/[[:alpha:]]/Users)/[^[:space:]:]+#/<redacted>#g' \
  -e 's#(USER|USERNAME|HOSTNAME)=[^[:space:]]+#\1=<redacted>#g' \
  "$report"

printf 'Wrote sanitized snapshot: %s\n' "$report"
