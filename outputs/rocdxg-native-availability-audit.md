# Native availability and WSL visibility: source audit

2026-10-28 UTC. The native source path does not justify upgrading the earlier empty-inventory CLI observation into a silent WSL failure claim. Multiple WSL discovery failures have explicit warnings, and partial topology mismatch deliberately lets the profiled application continue. No native profiler library or GPU operation was executed for this audit.

The call chain is `get_number_of_agents()` → `get_agents()` → `get_metadata()` → `metadata(inprocess)` → `rocprofiler_query_available_agents()`. The metadata constructor copies each returned agent into its inventory; the counter initialization method skips CPU agents and iterates available non-CPU agents. An empty successful query can therefore remain empty without a separate list-avail fatal error. This source trace does not establish that the SDK query succeeds silently after a real loader failure.

| Discovery gate or refusal | Source behavior |
|---|---|
| Platform selection | Explicit force-platform setting, then Linux KFD availability, then WSL probe, then Linux fallback |
| No `/dev/dxg` | WSL availability returns false with INFO |
| `/dev/dxg` exists but DXCore load/symbol fails | WSL availability returns false with WARNING |
| Late attach marker | WSL enumeration warns and returns empty; intentional snapshot-lifetime guard |
| DXCore load/symbol or adapter enumeration failure | Enumeration warns and returns its empty result |
| DXCore reports zero adapters | INFO and empty result |
| Thunk provides no GPU nodes | Explicit warning that no GPU agents will be published |
| Non-AMD adapter | INFO and skip |
| Required adapter query fails, unmatched/ambiguous KMT node, unparseable target, incomplete topology | Adapter is discarded with a diagnostic for the checked refusal |
| HSA reports GPUs that profiler cannot match on WSL | ERROR explains profiling is unavailable on those GPUs while the application and matched GPUs continue |

The inspected WSL adapter construction does not contain a blanket `gfx1101` rejection. It parses the target name and requires complete topology. This is **not** proof that RX 7800 XT hardware counters, tracing, or the installed 10.0 build are supported: metric definitions, compiled feature gates, and runtime behavior remain separate.

Pinned Git blobs from [ROCm/rocm-systems](https://github.com/ROCm/rocm-systems):

- `source/lib/rocprofiler-sdk-tool/list-avail/rocprofv3_avail.cpp`: `0f853e2c828eaf25a25a926df206a356c05cc37f`, especially lines 77–135.
- `source/lib/output/metadata.cpp`: `6458dabd0a4a075604913d88b91f5ac95a0f6c8e`, lines 190–279.
- `source/lib/rocprofiler-sdk/platform/wsl/agent.cpp`: `ef91fefd9a8ebfab38ff6c5f02daa9c609c4da00`, lines 192–224, 392–480, and 594–719.
- `source/lib/rocprofiler-sdk/agent.cpp`: `51213b7b3e282411911f62d4a44938346ee22f36`, lines 315–368 and 769–789.

These are current upstream source identities, not a version fingerprint of the installed binary. Exact excerpts and line numbers are retained in `work/rocdxg-loader-audit/native-availability-source-map.json`; no new runtime test is claimed. Kernel delta, GPU owners, and hardware telemetry were not collected because this batch was source-only. No installed library, driver, service, or running workload was changed.

Deduplication: [PR #13576](https://github.com/ROCm/rocm-systems/pull/13576) remains open/unmerged at `65313194df87e824f2d3a3cd8f13dbcc22f8707a`; its loader repair is already tracked. The related snapshot-lifetime [PR #10034](https://github.com/ROCm/rocm-systems/pull/10034) appears merged in the upstream search result and must not be rediscovered; source comments describing a prerequisite alone do not establish an unresolved issue in current source or an installed package.

Next off-GPU candidate: [open PR #10738](https://github.com/ROCm/rocm-systems/pull/10738), checked unmerged at `06d49e43db342c6a73e87e55589e3da4ba201193`, describes a stale stored DXG descriptor after a failed DXCore-loader open. Prepare a CPU-only reduction of the actual open/failure-cleanup function with injected file/loader operations. Never induce a real runtime failure or close any production descriptor. This is an existing proposed fix to validate, not a new defect claim.
