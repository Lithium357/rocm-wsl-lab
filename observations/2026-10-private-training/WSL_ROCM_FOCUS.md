# WSL–ROCm training boundary: investigation order

Last reviewed: **2026-10-19**

This page narrows the external-runtime work to the path used by the private training project training:

```text
Windows AMD driver → Hyper-V / WSL GPU virtualization → /dev/dxg
→ ROCDXG + DXCore → HIP/HSA → PyTorch → training workload
```

It does not treat an error near this path as proof that any particular layer
caused it. Production CPT continues on the known-stable configuration; no
probe below is to run while the trainer owns the GPU.

## What is confirmed

- The WSL guest exposes `/dev/dxg`, Microsoft DXCore, and AMD's ROCDXG bridge.
- The active training process maps system ROCDXG 1.2.2 and the HIP/HSA
  libraries supplied by its PyTorch ROCm wheel. That composition matches the
  bridge architecture described by AMD, rather than demonstrating a library
  collision.
- Stable default-SDPA training has sustained roughly 565–570 tokens/second
  without a new dxg kernel error.

AMD documents ROCDXG as the userspace library that enables ROCm workloads in
WSL and says the runtime loads it through the WSL path. Their current Radeon
WSL matrix lists the RX 7800 XT, but its production PyTorch pairing is 2.9.1 /
ROCm 7.2.1; the observed PyTorch 2.13 / ROCm 10 stack is therefore a real
workload environment, not yet a supported-stack regression.

Sources: [ROCDXG architecture and validation](https://github.com/ROCm/librocdxg/),
[AMD WSL support matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html).

## Evidence by layer

| Priority | Boundary | Observation | Current classification | Next decisive comparison |
| --- | --- | --- | --- | --- |
| 1 | Experimental attention → dxg synchronization | AOTriton enabled produced field-spanning-write and sync-wait warnings after two steps; default SDPA completed its control. | Candidate external bug; experimental and outside published support. | Repeat one short run in AMD's published WSL runtime after CPT is safely stopped. |
| 2 | PyTorch allocation → dxg allocation | Disabling activation checkpointing emitted `get_user_pages_fast` and `Ioctl -12`, without a useful PyTorch OOM. | Candidate external error-reporting failure; capacity exhaustion is also plausible. | Reproduce the allocation boundary with a fixed geometry and capture both framework error and dxg delta. |
| 3 | WSL memory → Hyper-V VMBus | Historical high-order allocation warnings occurred under a memory-constrained guest, without demonstrated trainer failure. | WSL observation, not an actionable GPU defect. | Correlate only if it causes a new-session, interop, or workload failure. |
| 4 | Windows-mounted filesystem → WSL training reader | A packed cache on `/mnt/d` hit `Errno 5`; the same cache on WSL ext4 is stable. | Mitigated WSL/filesystem reliability issue. | Read-only checksum/scan comparison after production stops. |
| 5 | dxg feature/adapter queries | `-22` / `-2` ioctl noise appears in WSL logs, while normal compute continues. | Observed diagnostic noise. | Minimal device-query versus fresh-session delta; no report unless functional impact appears. |
| 6 | Hyper-V firewall telemetry | Event 285 warnings occur without a trainer restart, GPU reset, or failed interop. | Telemetry lead only; Windows-owned. | Ignore unless network/VM symptoms correlate. |

The individual evidence records are [0001](rocm-wsl/0001-experimental-aotriton-dxg-sync.md),
[0002](rocm-wsl/0002-wsl-allocation-error-reporting.md),
[0003](wsl/0003-mnt-d-errno5-packed-cache.md),
[0004](wsl/0004-hv-vmbus-channel-allocation.md),
[0005](wsl/0005-dxg-adapter-query-ioctl-noise.md), and
[0006](wsl/0006-hyperv-vmswitch-event-285-telemetry.md).

## Cross-vendor upstream correlation

The field-spanning-write portion of the AOTriton observation has an exact
function-and-line match with [Microsoft WSL issue 41017](https://github.com/microsoft/WSL/issues/41017):
`dxgvmb_send_wait_sync_object_gpu` at `dxgvmbus.c:3095`. That report involved
an NVIDIA-backed PyTorch training workload, and Microsoft pointed a duplicate
report to it. This supports a *possible* shared GPU-PV/WSL synchronization
surface; it does not demonstrate that AMD hardware, ROCm, or this training run
shares the same root cause.

Another user report, [WSL issue 41701](https://github.com/microsoft/WSL/issues/41701),
describes throughput degradation with accumulating dxg synchronization errors
after multi-day uptime on the same WSL release family. It is not maintainer
confirmation and uses different hardware. The right response here is the
documented fresh-versus-aged uptime control, not a GPU reset or a claim of a
match.

## Non-matches worth avoiding

- The public RX 7800 XT detection report in ROCDXG issue 34 is not a match:
  its reporter had not completed setup, and the maintainer notes its DXG
  detection environment variable was needed only for releases before ROCm
  7.13. This training process already discovers the GPU and executes kernels.
- The public WSL `hipMemGetInfo` report concerns a guest-versus-native memory
  accounting gap. No such measurement has been made here, so it is a watch
  item—not evidence about this machine.

Sources: [ROCDXG issue 34](https://github.com/ROCm/librocdxg/issues/34),
[ROCDXG issue 57](https://github.com/ROCm/librocdxg/issues/57).

## Safe next sequence

1. Wait for a durable production checkpoint and intentionally stop CPT before
   any GPU probe or runtime installation.
2. Capture a pre-change bridge wiring audit: WSL version, Windows driver,
   ROCDXG package version, `/dev/dxg`, DXCore, and a sanitized library map.
3. Update WSL from the recorded 2.7.11 / 6.18.33.2 baseline to a current stable
   release only after that stop, then repeat the wiring audit and a fixed SDPA
   control. This is a test variable: do not call it a fix without evidence.
4. Create a separate, disposable AMD-published reference environment. Do not
   modify the existing training environment or model/data directories.
5. Run the SDPA control first, then one changed variable per test. Stop at the
   first dxg synchronization, host, thermal, or filesystem error.
6. Publish only a privacy-scrubbed minimal reproducer if a result survives the
   reference-stack comparison. Never include the private training project data, weights, checkpoints,
   personal paths, or the private monitoring dashboard.

## What does not belong in a vendor report yet

- A slow training step by itself.
- Expected loss variability or model-quality observations.
- The healthy-training Event 285 count.
- Any claim that the mixed ROCDXG/framework library mapping is broken.
- A failure observed solely in unsupported experimental attention without a
  supported-stack reproduction.
