# ROCm–WSL findings

Published evidence from RX 7800 XT / gfx1101 investigations and isolated CPU-only source tests. Original run dates and environments remain in each report. A source fixture is not a hardware reproduction, and a matching symptom is not proof of a shared cause.

| Finding | Evidence | Current interpretation |
|---|---|---|
| [Queue-buffer lookup converts error 1 to Boolean success](dxg-queue-reference-report.md) | Actual upstream helpers and queue-create function; 14 CPU fixture cases; two-line candidate passes all seven scenarios | Additional unresolved source-level defect. Installed GPU impact untested. [Reproducer](dxg-queue-reference-reproducer.zip), [patch](dxg-queue-reference-bool.patch), [results](dxg-queue-reference-results.json) |
| [Expandable-segment allocation / host-access boundary](hip-vmm-access-report-20261027.md) | Passing GPU-only descriptor versus failing GPU+host descriptor, two processes each; standalone 2 MiB HIP reduction | Locally reproduced integration boundary. Whether host access is supported on this WSL path remains unsettled; no new driver defect claim. Disable expandable segments as the tested workaround. [Earlier framework reduction](rocm-unresolved-report.md) |
| [Checkpointed dropout with compiled eager backend](rocm-correctness-report-20261027.md) | Two complete CPU/GPU matrices; passing uncompiled and aot_eager controls | Known generic PyTorch issue [#199251](https://github.com/pytorch/pytorch/issues/199251), not attributed to ROCm/WSL |
| [Versioned-only ROCDXG loader](rocdxg-loader-audit.md) | Pinned constructor, private ELF fixtures, comparison with upstream proposed fix | Existing [#12495](https://github.com/ROCm/rocm-systems/issues/12495); open unmerged [PR #13576](https://github.com/ROCm/rocm-systems/pull/13576) has a fuller fix. **The historical local versioned-first patch is incomplete: do not apply it.** |
| [Failed DXCore open leaves stale stored descriptor](dxg-open-cleanup-audit.md) | Actual upstream open function with fake descriptor table; 12 CPU cases | Existing open unmerged [PR #10738](https://github.com/ROCm/rocm-systems/pull/10738) passes the isolated cleanup contract. Installed-runtime reproduction untested |

## Known signatures and excluded fixed work

- [Idle CPU polling](rocm-test-report.md) reproduced locally, but [upstream PR #7898](https://github.com/ROCm/rocm-systems/pull/7898) is merged. Archived evidence; do not rediscover it.
- [Field-spanning synchronization warning](rocm-unresolved-report.md) was observed once and stopped GPU testing. It matches known [WSL #40580](https://github.com/microsoft/WSL/issues/40580); it is not a new hang or corruption finding.
- Imported-handle CPU-access [PR #11380](https://github.com/ROCm/rocm-systems/pull/11380) and VA-pool [PR #10458](https://github.com/ROCm/rocm-systems/pull/10458) are merged; neither is treated as an unresolved discovery here.

## Supporting audits and negative controls

[Package/ELF manifest](rocdxg-package-resolution-audit.md), [runtime-directory fixtures](rocdxg-runtime-dir-audit.md), [empty-agent CLI contract](rocdxg-empty-agent-contract-audit.md), and [native visibility trace](rocdxg-native-availability-audit.md) are supporting investigations, not additional hardware bugs. The artificial prefix-name case is not an installed defect. Sparse determinism and small graph-lifecycle controls passed within the scope described in the [correctness report](rocm-correctness-report-20261027.md).

The [HIP pool probe status](hip-pool-test-status-20261027.md) is preparation only; it was not executed on an occupied GPU. Older reports' statements that nothing was published describe the time of those runs. These sanitized snapshots are now public in this repository; no third-party upstream issue or comment was posted as part of this publication.

## Running the probes

Read [the repository protocol](../docs/REPRODUCTION_PROTOCOL.md) and [data policy](../docs/DATA_POLICY.md) first. GPU probes require a healthy idle GPU, generated inputs, readable kernel logs, and per-process limits. Never reset or alter production work to bypass a stop condition. CPU fixture bundles use inert dependencies and do not load AMD runtime libraries. Keep raw runs outside Git and publish only reviewed summaries.
