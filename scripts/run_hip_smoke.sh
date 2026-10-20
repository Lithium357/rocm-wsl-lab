#!/usr/bin/env bash
# Build and run the smallest HIP device/allocator/kernel smoke probe.
set -euo pipefail

usage() {
  echo "Usage: $0 [--out <ignored-artifact-directory>]" >&2
}

out="artifacts/hip-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
if [[ $# -gt 0 ]]; then
  [[ $# -eq 2 && $1 == "--out" ]] || { usage; exit 2; }
  out=$2
fi

if pgrep -af 'scratchtag.*llm-train|train_cpt_rocm|accelerate.*train' >/dev/null; then
  echo "Refusing HIP smoke probe: a production training process owns the GPU." >&2
  echo "Stop training intentionally, preserve a checkpoint, then retry." >&2
  exit 3
fi

command -v hipcc >/dev/null || { echo "hipcc is required but was not found." >&2; exit 127; }

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$out"
binary="$out/hip_device_smoke"
log="$out/result.txt"

{
  printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  hipcc -O2 -std=c++17 "$repo_root/probes/hip_device_smoke.cpp" -o "$binary"
  timeout 60s "$binary"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$log"

printf 'Synthetic smoke result: %s\n' "$log"
