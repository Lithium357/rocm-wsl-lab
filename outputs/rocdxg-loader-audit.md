# Off-GPU ROCDXG loader investigation

## Follow-up: existing upstream fix and local patch limitation

Checked 2026-10-28 UTC: [PR #13576](https://github.com/ROCm/rocm-systems/pull/13576) is **open and unmerged** at head `65313194df87e824f2d3a3cd8f13dbcc22f8707a`. It already implements a more complete fix, including filename-aware unit tests. Issue #12495's timeline did not link this PR; a repository-wide PR search found it. Future checks must search relevant PRs as well as issue timelines.

**The local versioned-first patch is incomplete and should not be applied.** Its original six-case matrix did not test an already-resident unversioned library competing with a different loadable versioned library, or a versioned library available only beside the HSA runtime. The local patch selects the new library in the first case and misses the second. This is a limitation of our proposed patch, not a newly discovered upstream defect.

A new CPU-only comparison extracted the PR's actual `rocdxg_names`, `open_rocdxg`, and handle constructor and compared them with the local candidate through inert loader maps. The PR passed five policy cases; the local patch failed the two additional cases. Both passed cold versioned lookup, legacy-only lookup, and missing-library rejection. Acquired handles were balanced in all ten runs. No real library was loaded, no AMD runtime/profiler was invoked, and no GPU was accessed.

PR blob pins: `dxg_topology.cpp=e730ea33a068f9610c5ee2b49ddedb67d1ed3dc0`, `dxg_thunk.hpp=2f2042c77d2fc64e0a7adf43d61afba45e9400e1`. The harness verifies these identities. It supplies major-1 constants and an injected runtime-directory callback; it does not test header version detection, real `dl_iterate_phdr` path discovery, KMT ABI, topology, or the full upstream unit executable. The PR author's reported build/GPU results are not local validation.

The existing tests are in `source/lib/rocprofiler-sdk/platform/tests/wsl_dxg_thunk.cpp` and are included in `platform-dispatch-tests` only when `ROCPROFILER_SDK_DXG_TOPOLOGY_SUPPORTED` is true. Baseline `FakeLoader` ignores the requested filename, explaining why it cannot catch this regression. The open PR replaces that with exact-name resident/loadable sets and covers both missing cases, so another duplicate test patch is unnecessary.

Reproduction: from the retained `work/rocdxg-loader-audit` source folder on Linux, run `python3 compare_pr13576.py`. Results are also preserved as `rocdxg-pr13576-policy-results.json` under outputs. Keep the earlier ZIP as historical evidence only; its candidate is superseded by this analysis. Next off-GPU work: audit the PR's real active-runtime path discovery separately using inert ELF fixtures; do not load production runtime libraries.

## Result

The current upstream loader constructor misses a valid versioned-only library in an isolated CPU test. A candidate versioned-first patch resolves both failing cases and preserves legacy lookup, rejection of missing libraries/exports, and balanced loader references.

This advances existing [ROCm issue #12495](https://github.com/ROCm/rocm-systems/issues/12495), which remains open. It is a **source-level regression result**, not a new hardware defect or a completed real-GPU profiler reproduction.

| Private library scenario | Upstream constructor | Candidate constructor |
|---|---|---|
| Versioned library only | Incorrectly unavailable | Available |
| Versioned library already resident, no alias | Incorrectly unavailable | Available; existing reference acquired |
| Versioned library with unversioned alias | Available | Available |
| Legacy unversioned library only | Available | Available |
| No library | Correctly unavailable | Correctly unavailable |
| Library missing the fixture marker export | Correctly unavailable | Correctly unavailable |

All successful opens were balanced by closes in all 12 cases. The candidate passed all six scenarios. The upstream constructor failed the availability expectation in two. The alias scenario acts as the passing control for the filename difference.

## What was tested

The `RocdxgHandle` constructor and `DxgLoaderOps` declaration are extracted from exact, hash-verified upstream files. The constructor is unchanged in the baseline. Tests use the real Linux ELF loader against private harmless libraries. An injected loader wrapper redirects every lookup to those fixtures, preventing resolution of any system AMD library. Symbol readiness is represented by a minimal marker resolver, not the real KMT exports.

No AMD runtime was loaded, no GPU device was opened, and no profiler was attached. The running workload and installed packages were untouched. These tests ran with Python and g++ on the CPU.

Pinned upstream Git blobs:

- `dxg_topology.cpp`: `ad716825a4a4b8c81bbcb926cf83cc7ddd4bbdde`
- `dxg_thunk.hpp`: `dceb8e885c2af624448eb36b245747f780c0ffcf`

The test verifies those blob identities before compiling. Original MIT notices are retained. The patch changes lookup to try `librocdxg.so.1` first, retaining `librocdxg.so` as a fallback. It applied cleanly to a disposable copy of the pinned source, and the applied files matched the candidate used by the test generator.

## Deliverables

- `rocdxg-versioned-first.patch`: candidate patch for review; not installed or submitted.
- `rocdxg-loader-regression.zip`: self-contained source-level test bundle, pinned sources, README, patch, and results. It contains no compiled binaries.
- `rocdxg-loader-results.json`: measured per-scenario availability, loader requests, and reference counts.

To rerun, extract the ZIP on Linux/WSL with Python 3 and g++ installed, then run:

```bash
python3 run_audit.py
```

Expected summary: `upstream_contract_failures=2`, `candidate_contract_failures=0`. Generated builds and fixture libraries stay under the extracted directory.

## Remaining validation

The complete rocprofiler translation unit and its upstream unit suite have not been built. The stand-in resolver does not validate KMT symbol types, ABI compatibility, topology enumeration, or real trace output. A compatible isolated runtime and eventual GPU profiling run are still needed before claiming an installed-stack fix. The hard-coded major-1 soname also needs maintainer review against the project's preferred version-header/build convention.

## Workflow correction

An occupied GPU blocks only GPU tests. The recurring hunt now has an explicit off-GPU lane: pinned-source audits, CPU-only regressions, package/loader checks, and candidate-patch validation. It must advance a concrete item rather than spend repeated wakes only checking ownership or looking for newly updated issues. The existing no-overlap and kernel stop conditions still apply to GPU work.
