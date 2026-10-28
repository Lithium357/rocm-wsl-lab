# HIP pool-lifetime investigation — 2026-10-27

**Prepared, not executed on the GPU.** A production `scratchtag llm-train` process acquired `/dev/dxg` before the guarded run started. The guard rejected the batch without launching either candidate case. No new ROCm defect is claimed.

Read-only inspection associated the process with the existing GPU workload project and `/init.scope`, rather than the previously disabled `erp-qwen3-4b-cpt-v2.service`. That service remained disabled and inactive. No training process was stopped or changed.

## Research decision

The open [ROCm #11693](https://github.com/ROCm/rocm-systems/issues/11693) originally reported corruption around freshly mapped allocations and async pools. A later analysis traces its failure to native Linux's in-tree amdgpu mapping/TLB path. WSL uses a different graphics bridge, so reproducing that exact native-driver diagnosis is not a WSL research priority. Targeted searches found no open WSL-specific `hipMallocAsync` report; that is not a guarantee of absence.

Instead, the prepared probe checks the local public HIP stream-ordered allocation contract directly, with no models or custom kernels.

## Queued experiment

Source: `hip_pool_lifecycle_probe.cpp`, built successfully with the installed public HIP headers, `libamdhip64.so.7`, and g++.

- Query memory-pool and VMM capability flags.
- Classic allocation control, then async allocation only if pool support is advertised.
- One nonblocking stream, 16 MiB device buffer and pinned host buffer, 64 iterations per case.
- Write a known byte pattern and enqueue a device-to-host copy.
- In the async case, enqueue the free after the copy but before stream synchronization, then verify every host byte after synchronization.
- Inspect live/retained pool memory and request a trim after all stream work completes.
- Explicitly free host memory and destroy the stream.

This is single-stream lifetime coverage. It does not reproduce the source report's custom kernels, native driver, or concurrent-stream race, and it does not claim a thermal or sustained-load qualification.

From the output scripts' directory, once the GPU is idle and kernel logs are clear:

```bash
"$ROCM_PYTHON" run_rocm_probes.py --focus hip_pool --out ../work/hip-pool-new-run
```

The compiled binary is under the task's `work/hip-vmm-build/`. The source remains the user-facing deliverable; the binary is not published.

## Harness isolation improvements

The unexpected workload arrival revealed a useful guard requirement. The runner now also checks for another GPU owner while a probe is active and stops only its own child if one appears. It rechecks existing kernel stop conditions immediately before each case. Its ownership scan tolerates an individual disappearing file descriptor without skipping the rest of that process.

Two no-GPU regression tests passed: a simulated trainer appearing during a probe causes termination of that probe and prevents the next case; a kernel warning appearing between the initial gate and case launch prevents any child launch. These tests validate orchestration behavior, not HIP runtime behavior.

GPU testing can resume automatically after live ownership checks are clear. Until then, research and probe preparation can continue. No reset, driver/runtime update, log clearing, or production-service change was performed.
