# ROCDXG PR runtime-directory helper: CPU fixture audit

2026-10-28 UTC. [PR #13576](https://github.com/ROCm/rocm-systems/pull/13576) remains open and unmerged, with unchanged head `65313194df87e824f2d3a3cd8f13dbcc22f8707a`.

The actual `active_hsa_runtime_dir()` function was extracted verbatim from Git blob `e730ea33a068f9610c5ee2b49ddedb67d1ed3dc0`, verified before compilation, and exercised through real Linux `dl_iterate_phdr`. Every deliberately loaded ELF library was a newly compiled inert fixture exporting only a marker function. No real AMD library, profiler, GPU device, production process, or installed package was accessed or changed.

| Generated fixture case | Result |
|---|---|
| No HSA-named object loaded | Correctly returns no directory |
| Absolute path to versioned fixture | Correct directory |
| Bare name resolved through private absolute search directory | Correct directory |
| Relative path to fixture | Correct relative directory |
| Absolute path to unversioned fixture symlink | Correct directory |
| Only an unrelated `libhsa-runtime64.so.backup` fixture loaded | Selects its directory despite the non-runtime suffix |
| Same prefix fixture loaded before the valid-name fixture | Selects the prefix fixture's directory |

Five ordinary controls pass. The last two cases isolate the helper's prefix-only filename comparison: `rfind("libhsa-runtime64.so", 0) == 0`. This is a **synthetic source-level edge case**, with no evidence that a similarly named unrelated library is present in the installed profiler process. It does not establish an installed ROCm failure, GPU instability, or a new reportable defect. No duplicate upstream report or speculative patch was created.

The batch comprised seven fresh processes with five-second deadlines; each completed in under 15 ms in this run. Each inert object was checked for the private marker immediately after loading, and every acquired fixture handle was closed. All generated libraries and build intermediates remain in the extracted work directory. The function was compiled separately, so full rocprofiler initialization, namespace selection, real HSA dependencies, and GPU topology remain untested. Kernel-log delta and GPU telemetry were not collected for this CPU-only batch; this result makes no hardware-health claim.

CPU test fingerprint: Python 3.14.4, g++ 15.2.0, glibc 2.43, WSL kernel `6.18.33.2-microsoft-standard-WSL2`. The GPU/runtime version fingerprint was not refreshed because this batch did not use those components.

To reproduce on Linux with Python 3 and g++, extract `rocdxg-runtime-dir-fixtures.zip` into a disposable directory and run:

```bash
python3 audit_runtime_dir.py
```

Expected: five `expected_directory_selected=true` ordinary cases and two `false` prefix-decoy cases. The script asserts this exact observed pattern and writes `runtime-dir-results.json`. It never searches for or loads an installed AMD library: the bare-name case has a prevalidated private fixture in its exclusive `LD_LIBRARY_PATH`, and preload/audit variables are removed from fixture subprocesses.

Next: advance package-resolution or output-contract source work. Retain this edge case as low-priority corroboration work, rather than presenting an artificial filename as a hardware bug.
