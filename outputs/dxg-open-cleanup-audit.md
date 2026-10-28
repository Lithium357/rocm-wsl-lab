# DXG failed-open cleanup: CPU-only source regression

2026-10-28 UTC. The actual upstream `hsaKmtOpenKFD()` function leaves its stored descriptor referring to a closed entry after an injected DXCore-loader failure. Existing [PR #10738](https://github.com/ROCm/rocm-systems/pull/10738) fixes this cleanup. It remains **open and unmerged**, checked at head `06d49e43db342c6a73e87e55589e3da4ba201193` before testing.

This reproduces a known proposed fix at the source level. It is not a new upstream discovery, a failure of the installed runtime, or a GPU result. No real DXCore/AMD library was loaded, no OS descriptor was opened or closed, and no production process or GPU was accessed.

| Injected scenario | Current upstream function | PR function |
|---|---|---|
| Healthy first open | Pass | Pass |
| Device open fails | Pass: no descriptor retained | Pass |
| Already open | Pass: reference count increments, no reopen/reset | Pass |
| Fresh open, DXCore initialization fails | Closed fake descriptor remains stored | Pass: descriptor closed and stored value reset |
| Existing stored fake descriptor, DXCore fails | Attempts fake close of local `-1`, retaining stored entry | Pass: closes stored entry and resets it |
| Loader failure followed by successful fake initialization | Skips reopen and reports success with a closed fake descriptor stored | Pass: obtains a fresh fake descriptor |

The first failing operation is the cleanup after `DxcoreLoader::Initialize()` returns false. Baseline closes local `fd` but does not reset `dxg_runtime->dxg_fd`. The proposed cleanup closes a nonnegative stored descriptor and sets it to `-1`. Both variants still return an error for the original injected loader failure. The recovery scenario is a second call inside a private fake state machine; no actual failing runtime configuration was retried.

All 12 processes completed within five-second per-case deadlines. Baseline failed three state invariants; the PR version passed all six cases. Healthy, device-open-failure, and already-open controls passed on both variants. Symbolic descriptor values belong only to an in-memory set. Fake open/close, environment initialization, page setup, suballocator reset, atfork registration, and DXCore initialization replace the dependencies; the open function itself is extracted verbatim. This does not validate real locking contention, fork behavior, suballocator semantics, DXCore side effects, or a complete library build.

Source pins for `projects/rocr-runtime/libhsakmt/src/dxg/openclose.cpp`:

- Baseline Git blob: `68b051017441e32a158901cb63719d59e50576ee`.
- PR Git blob: `4e7c623aee1d6d09861d25cac9bda881ada0b9be`.

The harness verifies both blob identities before extraction. The compared function differs only in failure cleanup. Runtime packages were not changed; the existing installed-stack fingerprint remains separate and was not refreshed for this CPU-only batch. The CPU harness uses Python 3.14.4 and g++ 15.2.0 on the previously recorded WSL environment. Kernel-log delta and GPU telemetry were not collected; no hardware-health claim follows.

Reproduction: extract `dxg-open-cleanup-fixtures.zip` into a disposable Linux directory with Python 3 and g++, then run:

```bash
python3 -I run_cleanup_audit.py
```

Expected summary: `baseline_failures=3`, `proposed_failures=0`. The ZIP contains only the harness, original pinned sources with license notices, and sanitized results. Compilation intermediates remain under its `build/` directory. Exact per-case results are also in `dxg-open-cleanup-results.json`.

Tested mitigation: the existing upstream PR cleanup passes this isolated contract. It has not been installed or submitted locally. Do not patch production libraries or induce an actual DXCore failure to validate it while work is running. Next off-GPU batch: examine the same open PR's topology metadata correction using actual source and deterministic synthetic device properties, keeping it separate from runtime/hardware reproduction.
