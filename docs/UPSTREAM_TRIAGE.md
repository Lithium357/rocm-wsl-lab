# Upstream triage

The lab does not file an upstream issue merely because an error string contains
`dxg`, ROCm, or WSL. An issue becomes a candidate only after a synthetic control
and affected run establish a repeatable difference.

## Current destination

The former `ROCm/librocdxg` repository is deprecated; its maintainers direct
new WSL ROCDXG issues and pull requests to `ROCm/rocm-systems`. Search the
existing `rocm-systems` issue tracker before opening anything new.

## Minimum evidence package

1. Run `scripts/capture_environment.sh`; review the ignored artifact and copy
   only sanitized version fields into a result note.
2. Run `scripts/run_hip_smoke.sh` only with no production GPU workload active.
3. Repeat the same command at least twice, then change exactly one documented
   variable for the affected run.
4. Include the synthetic command, expected versus actual behavior, exact
   component versions, and a short relevant log excerpt. Never attach a raw
   system-log bundle.

## High-value contribution sequence

1. Establish WSL-001 and WSL-002 as clean baselines.
2. Confirm or disprove one existing WSL report on the locally installed
   versions; add a comment with a concise result instead of creating a
   duplicate issue.
3. If a result differs from its clean control, create a sanitized result note
   in this repository and link it from a focused `rocm-systems` issue.
4. Only after an upstream maintainer agrees on the affected layer, prepare a
   small test or documentation pull request. Do not speculate about a fix or
   reverse engineer proprietary components.

## Multi-GPU boundary

Multi-GPU work remains blocked until two physical adapters are available. The
first useful test is discovery only: enumerate adapters independently through
WSL, ROCDXG, HSA, and HIP. Do not claim pooled VRAM, launch a distributed job,
or open an mGPU bug until that baseline is recorded.
