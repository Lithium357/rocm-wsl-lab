# Correctness hunt — 2026-10-27

## Confirmed locally: compiled eager checkpointing uses inconsistent dropout gradients

**An unresolved PyTorch correctness issue reproduces on the RX 7800 XT and CPU.** With `torch.compile(backend="eager")`, a checkpointed dropout block produces gradients whose zero mask disagrees with its own forward output on roughly 42% of tensor positions, despite explicitly requesting `preserve_rng_state=True`.

This is a framework issue observed in the ROCm/WSL environment. The CPU control also fails, so the evidence does not attribute the problem to ROCm, WSL, or hardware instability. It is an existing public issue, not a claim of a newly discovered defect.

Environment: RX 7800 XT / gfx1101; torch `2.13.0+rocm10.0.0`; HIP `7.15.26333`; Python `3.14.4`; WSL kernel `6.18.33.2-microsoft-standard-WSL2`.

### Passing controls and affected path

Inputs are strictly positive FP32 tensors of shape `[64,256]`. The block applies dropout with probability 0.3. For a sum loss, output and input-gradient zero masks must agree. Each backward is compared with its own forward, so this test does not assume that different backends produce the same random numbers.

| Execution | CPU mismatch | ROCm GPU mismatch |
|---|---:|---:|
| Plain block, no checkpoint or compilation | 0 for all seeds | 0 for all seeds |
| Checkpointed, uncompiled | 0 for all seeds | 0 for all seeds |
| Checkpointed, `compile(backend="aot_eager")` | 0 for all seeds | 0 for all seeds |
| Checkpointed, `compile(backend="eager")`, seed 0 | 41.8030% | 42.7429% |
| Same, seed 1 | 42.9504% | 41.4612% |
| Same, seed 2 | 41.7908% | 41.8762% |

The complete matrix ran in **two independent processes**, with identical percentages in both. Across those processes, all 36 control forward/backward cases passed, and all 12 affected cases failed the mask invariant. No application exception or kernel warning was raised by the faulty operation; the runner's exit code 10 records the probe detecting incorrect gradients.

### Reproduce with the guarded suite

Place `run_rocm_probes.py` and `rocm_correctness_probe.py` together. Inside WSL, substitute the installed ROCm environment's interpreter for `$ROCM_PYTHON` and run from their directory:

```bash
"$ROCM_PYTHON" run_rocm_probes.py --focus dropout --out ./results/dropout-01
```

The probe tests CPU and ROCm, all four execution paths, and seeds 0/1/2. Use a new result directory for a repeat. An exit code of 10 is expected when the correctness issue is detected. The runner refuses an existing kernel stop condition or another visible GPU owner.

The essential invariant is:

```python
def block(x):
    return torch.nn.functional.dropout(x * 1.0, 0.3, training=True)

def checked(x):
    return checkpoint(block, x, use_reentrant=False, preserve_rng_state=True)

fn = torch.compile(checked, backend="eager")
x = (torch.rand(64, 256) + 0.5).to("cuda").requires_grad_()
y = fn(x)
y.sum().backward()
mismatch = ((y != 0) != (x.grad != 0)).float().mean().item()
# Expected 0; observed approximately 0.42 on the installed stack.
```

### Upstream status and fixes

[PyTorch #199251](https://github.com/pytorch/pytorch/issues/199251) remained open when checked. The related [checkpoint fallback PR #160883](https://github.com/pytorch/pytorch/pull/160883) was open and **unmerged**. The public report's original evidence covered CPU; this test adds a locally reproduced ROCm GPU result on a different torch version.

Read-only inspection found an unconditional `kwargs["preserve_rng_state"] = False` in the installed `torch/_higher_order_ops/wrap.py`, including line 358. That is consistent with the reported failure mechanism. This inspection is not a complete root-cause proof or a validated package patch.

**Verified workarounds for this probe:** keep the checkpointed block uncompiled, or use `torch.compile(..., backend="aot_eager")` when investigating compile behavior. Both produced correct masks on CPU and GPU. `aot_eager` is a diagnostic backend; its passing result is not a performance recommendation. Inductor, reentrant checkpointing, selective checkpoint policies, other dtypes, and real-model convergence were not tested. No installed code was modified.

## Sparse deterministic multiplication: not reproduced on this ROCm stack

[PyTorch #202030](https://github.com/pytorch/pytorch/issues/202030) reports sparse-matrix nondeterminism on NVIDIA CUDA. The discussion explicitly leaves hipSPARSE behavior unestablished; CUDA results were not assumed to apply to ROCm.

The local test used a 10,000-by-10,000 generated sparse matrix, 250,000 requested entries (209,704 after coalescing), a heavily populated row, and a dense width of 64. Deterministic algorithms were enabled. Twenty identical forward calls were checked for each device/layout pair:

| Device / sparse layout | Distinct results in 20 calls | Relative L2 error vs CPU FP64 |
|---|---:|---:|
| CPU / COO | 1 | 1.04e-6 |
| CPU / CSR | 1 | 1.04e-6 |
| ROCm / COO | 1 | 8.58e-7 |
| ROCm / CSR | 1 | 5.30e-7 |

All 80 calls completed; no repeat delta was observed. Sparse construction emitted ordinary invariant-check and CSR-beta warnings, not a determinism rejection or a kernel fault. This covers FP32 forward execution for one generated fixture, not all sparse algorithms or backward paths.

Reproduce: `"$ROCM_PYTHON" run_rocm_probes.py --focus sparse --out ./results/sparse-01`.

## Simple multi-graph replay/teardown: both controls passed

The open [ROCm graph issue #193668](https://github.com/pytorch/pytorch/issues/193668) describes intermittent failures in a larger external pipeline. It lacks a self-contained reproducer, and the reporter says simple stock-operation controls can pass. This local check therefore explores graph lifecycle reliability without claiming to reproduce the full pipeline.

Each of two fresh processes captured four small stock-operation graphs, replayed them 200 times with cloned outputs, checked bitwise equality against eager GPU output, reset the graphs, collected Python garbage, and verified another GPU operation after teardown. Both processes exited normally. The sole comparison variable was an explicit GPU synchronization before stacking the cloned outputs: absent in the first process, present in the second. Both passed.

Reproduce: `"$ROCM_PYTHON" run_rocm_probes.py --focus graphs --out ./results/graphs-01`.

This did not include the original pipeline's custom kernels or concurrent prefetching. No conclusion is made about that reported failure on its original hardware.

## Final state and evidence

Five case processes ran: one sparse case, two dropout matrices, and two graph cases. No kernel stop messages appeared. The final read-only inspection found no `/dev/dxg` owners. The production trainer remained stopped at the initial gate. No driver/package update, GPU reset, WSL shutdown, production setting change, or upstream publication was performed. The already-fixed idle CPU issue and previously observed allocator failure were not retested.

`rocm-correctness-results-20261027.json` contains exact measured masks, errors, case arguments, timestamps, return codes, and kernel deltas. Raw logs remain in the task's work directory; the exported results contain no personal paths or private workload data.
