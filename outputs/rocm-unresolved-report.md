# ROCm / WSL unresolved-issue hunt — 2026-10-26

Update 2026-10-27: [the standalone HIP reduction](hip-vmm-access-report-20261027.md) isolates the failure to adding a host-access descriptor for locally created device memory. It also corrects the current upstream status: PR #10879 was superseded by merged #11380 for imported handles. The historical status checks below describe the earlier run.

## Actionable result: four-byte allocation fails with expandable segments

**Confidence: reproduced locally, runtime cause not yet confirmed.** On RX 7800 XT / gfx1101, PyTorch `2.13.0+rocm10.0.0`, HIP `7.15.26333`, Python `3.14.4`, WSL kernel `6.18.33.2-microsoft-standard-WSL2`, enabling expandable segments makes the first four-byte GPU allocation fail. Disabling the setting makes the identical allocation, fill, synchronization, and copy-back pass.

| Case | Configuration | Result |
|---|---|---|
| Allocation/free control | `expandable_segments:False` | 36 cycles passed; no retries or OOMs; maximum live tensors 2.875 GiB |
| Same allocation/free sequence | `expandable_segments:True` | Failed on the first 128 MiB allocation with `hipErrorInvalidValue` |
| Reduced control | `expandable_segments:False` | One FP32 element allocated, filled, synchronized, copied back correctly |
| Reduced affected run, diagnostic logging enabled | `expandable_segments:True` | First four-byte allocation failed |
| Reduced affected run, diagnostic logging absent | `expandable_segments:True` | Same first-allocation failure |

The larger control started with 15,248,211,968 free device-memory bytes. Its peak reserved memory was 3,491,758,080 bytes. This did not require an OOM, model weights, another process, or an IPC import. No monitored kernel-instability message appeared during these allocator cases.

### Minimal reproduction

Use the existing ROCm environment's interpreter in place of `$ROCM_PYTHON`, inside Ubuntu/WSL. Start a fresh process for each setting. Clear legacy allocator aliases so only one setting controls the test:

```bash
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_HIP_ALLOC_CONF
PYTORCH_ALLOC_CONF=expandable_segments:False "$ROCM_PYTHON" -c 'import torch; x=torch.empty(1,device="cuda"); x.fill_(357); torch.cuda.synchronize(); print(x.cpu().item())'
PYTORCH_ALLOC_CONF=expandable_segments:True "$ROCM_PYTHON" -c 'import torch; x=torch.empty(1,device="cuda"); x.fill_(357); torch.cuda.synchronize(); print(x.cpu().item())'
```

Expected: both print `357.0`. Observed: False passes; True raises `torch.AcceleratorError: CUDA error: invalid argument` from the allocation. This minimal command is equivalent to the tested reduced probe; the measured runs used the guarded runner and its JSON-emitting probe.

To reproduce with GPU ownership and kernel-log guards, place all three supplied Python files together and run from that directory:

```bash
"$ROCM_PYTHON" run_rocm_probes.py --focus minimal_control --out ./results/minimal-control
"$ROCM_PYTHON" run_rocm_probes.py --focus minimal_changed --out ./results/minimal-affected
```

Do not run probes on a session with the kernel warning described below. The guarded runner refuses that session. No reset or update was performed to bypass this gate.

### Failure localized by public runtime diagnostics

One affected run used `AMD_LOG_LEVEL=4`. A compact, address-free summary of the trace is:

```text
hipMemAddressReserve(size=19281215488) -> hipSuccess
hipMemCreate(size=2097152) -> hipSuccess
hipMemMap(size=2097152) -> hipSuccess
hipMemSetAccess(size=2097152, descriptor_count=2) -> hipErrorInvalidValue
```

The four-byte tensor uses a 2 MiB allocator page and a larger virtual-address reservation. The reserved virtual range is not a physical allocation of that size. The trace distinguishes this from failures in virtual-address reservation or physical memory creation.

Upstream [PyTorch v2.13 allocator source](https://github.com/pytorch/pytorch/blob/v2.13.0/c10/cuda/CUDACachingAllocator.cpp) constructs a GPU-plus-host access-descriptor pair on sufficiently recent ROCm. That is consistent with the observed descriptor count, but it does not prove which descriptor fails in the installed AMD wheel. A device-only versus device-plus-host HIP control would be the next diagnostic step in a healthy session. No descriptor contents were modified or vendor binaries patched.

### Upstream status and contribution value

[PyTorch #200608](https://github.com/pytorch/pytorch/issues/200608) is open and describes an allocator assertion on the same GPU under a different stack and a large-model workload. Its proposed [fix #200774](https://github.com/pytorch/pytorch/pull/200774) was **not merged** when checked. This run did **not** reproduce its `!handles_.at(i)` assertion. It supplies a smaller, earlier access-setup failure worth comparing with that report, not proof of the same root cause.

[ROCm #11185](https://github.com/ROCm/rocm-systems/issues/11185) reports host-access setup failures for imported VMM handles on different hardware. The related [PR #10879](https://github.com/ROCm/rocm-systems/pull/10879) was also **not merged** when checked. Our case has no cross-process import, so equivalence is unproven.

An already-fixed address-reservation issue, [ROCm #10453](https://github.com/ROCm/rocm-systems/issues/10453), was excluded from further investigation. Its merged fix enlarges a virtual-address pool; the observed reservation succeeds here, with failure later at access setup.

**Verified workaround:** leave expandable segments disabled; both the reduced allocation and larger synthetic allocation/free control pass. A full fix needs runtime-level confirmation of the rejected access request and an appropriate compatibility or access-setup correction. No permanent fix has been validated on this hardware. The current evidence is sufficient for a focused comparison request, not a claim of a new upstream defect.

## Concurrent-copy observation — stopped, not attributed as a new hang

The unresolved [ROCDXG #84](https://github.com/ROCm/librocdxg/issues/84) motivated a separate synthetic copy test. That report concerns gfx1200; this machine is gfx1101.

- Control: one thread, 400 exact-checked round trips, 1 MiB per direction, two alternating buffers. Passed.
- Changed run: two threads, 200 round trips each, one independent buffer per thread, per-thread GPU streams. A new kernel warning appeared, and the harness terminated the child after 4.21 seconds.
- Remaining planned one-stream/eight-stream event-ordering cases were **not run**.

Relevant warning, at guest uptime 81.139499 seconds:

```text
memcpy: detected field-spanning write (size 4) of single field "current_pos"
at drivers/hv/dxgkrnl/dxgvmbus.c:3095 (size 0)
WARNING ... dxgvmb_send_wait_sync_object_gpu
Comm: python
Call Trace: dxgkio_wait_sync_object_gpu -> dxgk_ioctl -> dxgk_unlocked_ioctl
```

This is one warning observation with a passing single-thread control. It does not demonstrate the original report's context-creation failure, an application hang, or a new ROCm defect. No test completion or corrupted result was captured for the two-thread case. The `-15` child exit is the harness sending SIGTERM, not an application crash.

The signature matches [WSL #40580](https://github.com/microsoft/WSL/issues/40580), where a maintainer stated a fix was forthcoming. In accordance with the request to skip fixed problems, this known warning is not being pursued as a fresh finding. GPU testing stopped at its first appearance under the repository protocol. No test was automatically retried after it, and the final read-only check found no GPU owners.

## Evidence and scope

The exported `rocm-unresolved-results.json` records seven started case processes: three passing controls, three allocator exceptions, and one warning-triggered stop. Some cases intentionally return nonzero; these are preserved as findings rather than labeled passing tests. Timings, exact case arguments, relevant environment values, filtered kernel deltas, and sanitized error summaries are included. No models, private project source, raw diagnostic bundle, or upstream publication is included.

The previously identified idle CPU polling issue was not retested. No packages, drivers, production settings, or clocks were changed. These results apply to the installed stack; no supported reference-stack comparison was performed.
