# ROCm WSL Lab

Sanitized, minimal reproductions and controlled baselines for ROCm/HIP machine
learning workloads on Windows Subsystem for Linux.

This is a staging ground for issues that may involve the chain below. It is
not an AMD product, a model repository, or a copy of any application code.

```text
Windows display driver → Hyper-V / GPU-PV → WSL /dev/dxg
→ ROCDXG + DXCore → HIP/HSA → framework → synthetic workload
```

## Goals

- Reduce a suspect failure to the smallest synthetic, repeatable test.
- Preserve an unaffected control run alongside every changed-variable run.
- Separate framework, ROCm, ROCDXG, WSL, Windows, driver, filesystem, and
  thermal hypotheses instead of guessing a single owner.
- Produce privacy-scrubbed evidence suitable for an upstream issue only after
  it can be reproduced.

## What belongs here

- Small scripts that use generated tensors or public test inputs.
- Version manifests, sanitized `dmesg` deltas, and benchmark summaries.
- Reproduction instructions with a control and a clear stop condition.
- Links to already-public upstream issues.

## What never belongs here

- Model weights, adapters, datasets, prompts, conversations, or checkpoints.
- Private application/dashboard source code.
- Personal paths, account names, serial numbers, IP/MAC addresses, or raw
  unreviewed system-log bundles.
- Driver installers, large binaries, or automated overclocking/power tools.

## Working method

Read [the protocol](docs/REPRODUCTION_PROTOCOL.md) before running a probe.
Use [the experiment registry](docs/EXPERIMENTS.md) to avoid rerunning a known
bad configuration. The [data policy](docs/DATA_POLICY.md) applies to every
commit and issue attachment.

The initial focus is GPU-PV/ROCDXG reliability under sustained training-like
workloads: default control, one-variable attention experiment, allocation
boundary, WSL-mounted I/O, and fresh-versus-aged WSL uptime.

## Included harness

`scripts/capture_environment.sh` writes a scrubbed, ignored version snapshot.
`scripts/run_hip_smoke.sh` compiles a tiny generated-buffer HIP probe that
enumerates adapters and verifies allocation, a kernel launch, synchronization,
and a copy-back. It refuses to run while a recognizable production trainer owns
the GPU. See [upstream triage](docs/UPSTREAM_TRIAGE.md) before publishing a
result.

The separate [mGPU roadmap](docs/MGPU_ROADMAP.md) describes the path from
two-adapter discovery to independent compute, host-staged collectives, and
eventual PyTorch DDP. It does not promise pooled VRAM or supported mGPU today.

## Status

Repository scaffold only. No test result is published until it is reproduced
with synthetic inputs and reviewed for private data.

## Upstream references

- [AMD ROCm on WSL compatibility matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html)
- [AMD ROCDXG project](https://github.com/ROCm/librocdxg/)
- [Microsoft WSL GPU synchronization tracker](https://github.com/microsoft/WSL/issues/41017)
