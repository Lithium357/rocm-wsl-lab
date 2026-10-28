# Read-only ROCm / WSL profiler triage — 2026-10-27

**No GPU test or new local defect finding.** The live GPU remains owned by the previously identified production trainer. The last goal turn made progress by preparing a bounded pool test and validating its guard behavior. This turn revalidated the ownership gate and investigated an additional boundary-specific candidate without loading GPU libraries or attaching a profiler.

## Candidate: ROCDXG loader name mismatch

[ROCm issue #12495](https://github.com/ROCm/rocm-systems/issues/12495) remains open. It reports missing GPU profiler agents with a versioned-only ROCDXG library in a newer wheel on RX 7800 XT/gfx1101.

Current upstream [dxg_thunk.hpp](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocprofiler-sdk/source/lib/rocprofiler-sdk/platform/wsl/dxg_thunk.hpp) still defines the profiler's library name as `librocdxg.so`. The fetched file blob SHA was `dceb8e885c2af624448eb36b245747f780c0ffcf`. Its explanatory comment still assumes that this matches ROCr's loader name. The issue describes a different versioned-first ROCr loader and a measured private-loader-directory workaround.

Targeted searches for merged PRs referencing this issue or the versioned profiler library name found no matching fix. This is not an exhaustive guarantee that no fix exists. No upstream claim was posted.

### Local eligibility checks

Filename-only inspection found:

- The installed SDK wheel library directory contains `librocdxg.so.1`.
- The system library directory contains `librocdxg.so`, `librocdxg.so.1`, and `librocdxg.so.1.2.2`.
- Profiler executables and libraries are present, including `rocprofv3`, `rocprofv3-avail`, `librocprofiler-sdk.so.1`, and the registration library. They are shipped within the core SDK, so absence of a separate Python profiler package is not evidence that the profiler is missing.
- A read-only byte-string inspection of the installed `librocprofiler-sdk.so.1` found neither the reported `wsl topology:` diagnostic nor either exact null-terminated ROCDXG soname literal. The installed stack is older than the report's 10.2 nightly. Missing string literals alone do not prove absence of all WSL code or establish supported profiling behavior.

The system's unversioned library could mask the wheel-only loader problem, or could select an unintended thunk. A simple trace run in the production environment would therefore be a poor control even if the GPU were idle. No profiler was launched, attached, preloaded, or configured.

### Useful future comparison

Only pursue after confirming a WSL-capable compatible profiler/runtime pairing and rechecking current merge status. Use a separate environment, not the production wheel installation. Keep the generated workload and runtime fixed; compare a versioned-only library lookup against a private directory providing the unversioned alias. Check both exit status and actual kernel-trace rows with valid timestamps; an exit code of zero alone is insufficient. Avoid accidentally resolving the system's unversioned thunk in the versioned-only control. Do not modify system symlinks or publish raw profiler output.

## Lower-priority candidate excluded from immediate testing

[ROCm #12490](https://github.com/ROCm/rocm-systems/issues/12490) remains open, but its reported PMC collection failure uses gfx1201 and a specific newer profiler build. The report itself questions architecture support, and its discussion identifies a possible build-policy-induced abort when `/dev/kfd` is absent on WSL. Those conditions have not been established for this gfx1101 installation. It is not being treated as a matching local failure.

## Next action

The already-built `hip_pool` case remains the first queued GPU experiment once ownership and kernel gates permit it. The loader candidate is a separate isolated-environment investigation. The production process was left untouched. No repeated tests or unchanged-blocker notification are needed while the GPU remains busy.
