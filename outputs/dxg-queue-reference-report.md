# DXG queue-buffer lookup reports success for an absent allocation

## Finding

The WSL/DXG helpers `queue_acquire_buffer()` and `queue_release_buffer()` return `HSAKMT_STATUS_ERROR` when a non-null address is absent from the allocation map. Their return type is `bool`, and that status is defined as **1**, so the result converts to **true**.

The actual caller `hsaKmtCreateQueueV2()` checks `queue_acquire_buffer(QueueAddress) == false` before constructing its queue. The wrong Boolean result bypasses this rejection even though no queue reference was acquired. The release helper similarly reports success without finding or releasing a buffer reference.

**Confidence: reproduced in pinned upstream source, with inert native dependencies.** This is an additional unresolved source-level reliability defect in the shared WSL/DXG path relevant to gfx1101 as well as other GPUs. It is not evidence of a failure on the installed RX 7800 XT, a hardware instability, a security exploit, or a normal PyTorch workload triggering this path. No real queue or GPU operation was created.

## Controlled reduction

The harness extracts both complete helpers and the complete `hsaKmtCreateQueueV2()` function without changing their baseline bodies. A generated stack buffer is either present or absent in a private allocation map. Native memory objects, DXCore/HSA readiness, device queries, and queue constructors are inert substitutes. The candidate changes only the two erroneous missing-entry returns to `false`.

| Scenario | Upstream | Candidate |
|---|---|---|
| Null helper input | Correctly rejects | Correctly rejects |
| Registered buffer acquire/release | Correctly balances reference | Correctly balances reference |
| Null queue buffer | Returns invalid parameter; no constructor | Same |
| Registered queue buffer | Constructs once with acquired reference | Same |
| Non-null buffer absent from map: acquire | Incorrectly returns true | Returns false |
| Non-null buffer absent from map: release | Incorrectly returns true | Returns false |
| Same absent buffer passed to actual queue-create function | Returns success and reaches inert constructor with zero acquired references | Returns invalid parameter (3); constructor never called |

All 14 cases completed within five-second per-process deadlines. Upstream failed three contract checks; the candidate passed all seven. The registered-buffer cases provide the passing controls. No model, private input, installed AMD library, or GPU was used. The tested mitigation is a two-line source patch; it has not been installed.

## Source and deduplication

Checked October 27, 2026 (America/Denver; October 28 UTC). The problem is present in the fetched `develop` files:

- [memory.cpp](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/dxg/memory.cpp#L388), Git blob `f66d0b982514f8b5d439ff3ebd4a317c3e9c126d`: helpers, particularly lines 398 and 419.
- [queues.cpp](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/dxg/queues.cpp#L110), Git blob `f8fb999b8d0fa9d97f40ebc8c420177829c19a5a`: rejection guard and queue construction.
- [hsakmttypes.h](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/include/hsakmt/hsakmttypes.h#L98), Git blob `b6eaf4e8609f709468de767fdf28eac773942837`: `HSAKMT_STATUS_ERROR = 1`.

Exact helper-name searches across ROCm issues and pull requests returned no matches. Broader queue/reference/DXG searches were reviewed; related open [PR #10739](https://github.com/ROCm/rocm-systems/pull/10739) changes initialization and pooled-signal lifetimes, and its file list/patches do not contain this helper correction. The fetched current source still contains both bad returns. No matching merged fix was found. This is a bounded deduplication result, not a guarantee nobody has reported it elsewhere. Existing loader, idle-polling, allocator-host-access, and compiled-dropout findings are separate and were excluded.

## Reproduction and patch

Extract `dxg-queue-reference-reproducer.zip` to a disposable Linux directory with Python 3 and g++, then run:

```bash
python3 -I run_queue_reference_audit.py
```

Expected summary: `upstream_failures=3`, `candidate_failures=0`. Per-case expected/actual values are in `dxg-queue-reference-results.json`. The ZIP retains the exact upstream source snapshots and their MIT notices, a status-definition provenance record, the harness, results, and candidate patch. It contains no binaries. The harness validates source Git blob hashes before extraction and compilation.

`dxg-queue-reference-bool.patch` applies cleanly to the pinned source. The applied file matched the tested candidate byte-for-byte with LF line endings preserved. Only these two failure returns change:

```diff
-    return HSAKMT_STATUS_ERROR;
+    return false;
```

Suggested upstream regression acceptance: absent allocation returns false without changing references; registered acquire/release remains balanced; an absent ring allocation is rejected before either compute or SDMA queue construction. The current runnable reduction exercises the compute creation path; real SDMA creation and the full upstream build are untested.

## Environment and limits

CPU test toolchain: Python 3.14.4, g++ 15.2.0, WSL kernel `6.18.33.2-microsoft-standard-WSL2`. Read-only preflight found one GPU owner and no matching kernel stop messages, so hardware probes were not launched. GPU-driver and runtime versions were not reinitialized or inferred from this source snapshot. The installed 10.0 wheel's exact source identity has not been established.

The source-level failure requires a non-null address absent from the thunk allocation map. The harness intentionally uses a generated unregistered stack buffer to reach that branch; it does not show how often legitimate applications reach it. Real allocator races, queue execution, device faults, kernel-log deltas during GPU work, and application impact were not tested. Do not induce an actual invalid queue or alter production libraries to expand this evidence while the GPU is occupied.

No GitHub issue, comment, pull request, or external message was published. The local report and candidate patch are ready for review.
