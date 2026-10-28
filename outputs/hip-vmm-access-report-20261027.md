# ROCm / WSL VMM access reduction — 2026-10-27

## New evidence

The expandable-segment failure has been reduced to a **standalone public HIP API program, with no PyTorch dependency**. On this WSL stack, a locally created device-memory allocation works with GPU access alone. Adding a host-access descriptor makes `hipMemSetAccess` return `hipErrorInvalidValue`.

This is a reproduced interoperability boundary, not yet proof of a newly discovered or universally supported-feature defect. Its relationship to known WSL host-memory limitations needs confirmation.

## Controlled results

The same compiled program ran in four independent processes. The only test argument changes the access-descriptor count and adds `{hipMemLocationTypeHost, id=0, ReadWrite}` alongside the unchanged GPU descriptor.

| Configuration | Repetitions | Access setup | Data verification | Explicit cleanup |
|---|---:|---|---|---|
| GPU descriptor only | 2 | `hipSuccess` | Full 2 MiB host-to-device/device-to-host byte comparison passed | Unmap, release, address free all passed |
| GPU + host descriptors | 2 | `hipErrorInvalidValue` (code 1) | Not attempted after the error | Unmap, release, address free all passed |

Both configurations successfully initialize HIP, reserve virtual space, create a physical allocation, and map it. Allocation size is 2,097,152 bytes; reported minimum granularity is 4,096 bytes. Each allocation is locally created and requests POSIX-fd exportability, as the PyTorch allocator does, but no handle is exported or imported and there is no second process participating in a test.

The physical allocation and virtual reservation are each just 2 MiB. This removes PyTorch's approximately 19 GB virtual reservation, large tensors, fragmentation, model execution, and IPC import as necessary triggers for this API-level symptom.

Runtime version reported directly by HIP: `71526333` (7.15.26333). The program links against the installed ROCm SDK's `libamdhip64.so.7`; its installed SDK headers define the access descriptors. The prior live device enumeration identified RX 7800 XT/gfx1101. WSL kernel is `6.18.33.2-microsoft-standard-WSL2`.

No kernel stop message appeared during any of the four cases. The final inspection found no GPU owners. Nothing was reset or updated.

## Reproduction

Source: `hip_vmm_access_probe.cpp`. No HIP compiler or custom kernel is required; the program uses a regular C++ compiler and public runtime APIs.

Inside WSL, with `$SDK` set to the installed `_rocm_sdk_core` directory, build from the task directory:

```bash
g++ -std=c++17 -O2 -D__HIP_PLATFORM_AMD__ -I"$SDK/include" \
  outputs/hip_vmm_access_probe.cpp "$SDK/lib/libamdhip64.so.7" \
  -Wl,-rpath,"$SDK/lib" -o work/hip-vmm-build/hip_vmm_access_probe
```

Then use the monitored runner with the ROCm Python interpreter substituted for `$ROCM_PYTHON`, from `outputs/`:

```bash
"$ROCM_PYTHON" run_rocm_probes.py --focus hip_device --out ../work/vmm-device-new
"$ROCM_PYTHON" run_rocm_probes.py --focus hip_host --out ../work/vmm-host-new
```

The runner refuses a busy GPU or an existing kernel stop condition. The GPU-only case exits 0. The host-descriptor case exits 10 after printing the access error and successful cleanup. All runtime calls emit address-free JSON lines. Keep run directories distinct.

## Upstream status and interpretation

- [ROCm PR #10879](https://github.com/ROCm/rocm-systems/pull/10879) is now closed **without merging**. Its final comment points to the replacement [PR #11380](https://github.com/ROCm/rocm-systems/pull/11380), which **is merged** and addresses imported-handle CPU-access behavior. That imported-handle issue is excluded from further pursuit. This local program never imports a handle, so equivalence is not established.
- The merged [PR #10458](https://github.com/ROCm/rocm-systems/pull/10458) addresses virtual-address-pool exhaustion. Reservation succeeds here with a 2 MiB range; this is a different observed failure stage.
- The merged [PR #11336](https://github.com/ROCm/rocm-systems/pull/11336) documents that WSL/DXG lacks host-memory VMM and skips host-pool cross-process tests. Our allocation is device-local, not a host-pool or cross-process allocation. Nevertheless, this is relevant capability context: a host-access restriction may be intentional. Do not label the result a new driver bug solely because the API returned an error.
- Current [HIP access-setup source](https://github.com/ROCm/rocm-systems/blob/develop/projects/clr/hipamd/src/hip_vm.cpp) accepts host descriptor types before dispatching deeper into the runtime. The installed binary was not rebuilt from this source, and source inspection alone does not establish support on WSL.

The useful integration question is now narrow: **should host access to a locally created device VMM allocation work on this WSL backend, or should PyTorch avoid requesting it / reject expandable segments clearly on this configuration?** No merged fix for that exact locally created allocation case was identified in the targeted searches, but the searches are not an exhaustive guarantee of novelty.

Verified application workaround remains leaving expandable segments disabled. No runtime fix was applied. A further diagnostic could compare an unexportable local handle and a supported reference stack, provided current upstream support and merge status justify the work.

## Evidence

`hip-vmm-access-results-20261027.json` contains all four API traces, exact variant arguments, durations, exit statuses, and filtered kernel deltas. Source and results are sanitized. No vendor package, production service, model, or private data was changed, and nothing was published upstream.
