# ROCm / WSL test results — 2026-10-26

**Finding:** A tiny GPU operation causes an otherwise sleeping Python process to consume approximately two CPU cores. Reproduced in four independent processes. Releasing the tensor and clearing the GPU cache does not resolve it. This resembles a known upstream ROCm polling issue; the exact local runtime function responsible was not established by a stack trace.

## Environment and isolation

Live GPU enumeration confirmed AMD Radeon RX 7800 XT, gfx1101, 17,138,180,096 reported device-memory bytes. PyTorch `2.13.0+rocm10.0.0`, HIP `7.15.26333`, Python `3.14.4`, kernel `6.18.33.2-microsoft-standard-WSL2`. Loaded library basenames include `libamdhip64.so.7`, `libhsa-runtime64.so.1`, and `librocdxg.so.1.2.2`.

The unexpected trainer was verified inactive and disabled before testing. The guest had no visible `/dev/dxg` owners and no matching instability messages at the initial gate. The earlier allocation failures were absent from this session; no recovery action was performed by this test suite.

Shell checks found these relevant toggles unset: `TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL`, `HSA_ENABLE_SDMA`, `HSA_ENABLE_INTERRUPT`, `HSA_ENABLE_DXG_DETECTION`, `GPU_MAX_HW_QUEUES`, `HIP_VISIBLE_DEVICES`, `ROCR_VISIBLE_DEVICES`, and `OMP_NUM_THREADS`. The probe itself sets the PyTorch CPU thread count to two.

All inputs were generated tensors, seed 357. Each case ran in its own process with a 60-second limit and kernel-log monitoring. The suite would stop on an incorrect result, unexpected exception, timeout, log discontinuity, or a matching GPU synchronization/reset/allocation/I/O failure. None occurred. Final inspection found no GPU-owning processes; the trainer remained inactive.

## Reproduced issue: idle CPU consumption

The test imports torch, sets its CPU thread count to two, measures process CPU time over five seconds of sleep, creates a 4,096-element GPU tensor, performs `add_(1)`, synchronizes, then measures another five-second sleep. CPU percentages use aggregate user plus system process CPU time divided by wall time; 200% means two fully occupied CPU cores, not 200% of total machine capacity.

| Independent run | Before GPU work | After completion, during sleep |
|---|---:|---:|
| 1 | 0.0027% | 199.9885% |
| 2 | 0.0009% | 199.9715% |
| 3 | 0.0018% | 199.9875% |
| 4 | 0.0017% | 199.9748% |

Thread accounting in runs 3 and 4 found two threads at approximately 100% each. Their Linux names were both `python`, so names alone do not identify their runtime functions.

In run 4, deleting the tensor, running Python garbage collection, calling `torch.cuda.empty_cache()`, and synchronizing still left **200.1201% CPU** during the next five-second sleep.

Expected: after the synchronized operation, a sleeping process uses negligible CPU. Actual: roughly two cores remain busy until the process exits. The pre-GPU interval is the unaffected control; GPU initialization plus the tiny operation is the changed condition. The test does not isolate initialization from the operation itself. Four fresh-process repetitions establish the local symptom, not the exact upstream cause.

### Fix and mitigation status

[ROCm PR #7898](https://github.com/ROCm/rocm-systems/pull/7898), merged August 18, 2026, addresses busy polling in the async-event loop with a bounded sleep/backoff. Its reported WSL symptoms closely match this result. Merge commit: `46558b7af4dc79b8b8014619c1afdb82db079a9f`.

- **Immediate mitigation:** use an on-demand GPU worker process and let it exit when idle work is finished. Every probe exited, and subsequent ownership checks were clear. This removes the offending process rather than repairing the runtime.
- **Not effective here:** deleting GPU tensors and clearing the cache.
- **Runtime fix candidate:** validate a complete compatible ROCm/PyTorch stack containing the upstream change in a separate environment, using this same before/after test. Inclusion of the patch in the currently installed binaries, the correct replacement package version, and a fixed local result have not been verified. No libraries or packages were replaced.

[ROCm issue #13006](https://github.com/ROCm/rocm-systems/issues/13006) reports a separate memory-placement/performance tradeoff with newer WSL runtimes on different hardware. It supports testing an entire candidate stack rather than assuming that an isolated library swap is a safe fix. That issue was not reproduced here.

## Other results

| Probe | Coverage | Result |
|---|---|---|
| Basic GPU arithmetic | Two fresh-process runs; 4,096 elements, exact CPU comparison | Both passed |
| SDPA numerical correctness | Head dimensions 256/320/384/512; FP32 and BF16; shape `[1,4,128,D]`; forced MATH and default dispatch | All 16 passed |
| Forced efficient SDPA | Same eight shape/dtype combinations | All eight rejected as unavailable; not counted as successful computations |
| Longer-sequence SDPA | BF16, `[1,4,1024,D]`, D=256/384/512; MATH and default | All six passed |
| Host/GPU round-trip copies | Two runs, 100 iterations each, 1 MiB each direction, exact element checks | Both passed |
| Synthetic backward/checkpointing | FP32 and BF16; two 64-wide matrix layers with GELU; eager and non-reentrant checkpointed variants; 16 backward iterations per variant | All gradients within tolerance |

Attention references used CPU FP64 operations on the same precision-rounded inputs. Maximum measured relative L2 error was **7.04e-7 for FP32** and **0.001669 for BF16**. Limits were 1e-4 and 0.02 respectively. Gradient relative L2 error peaked at **2.52e-7 for FP32** and **0.004188 for BF16**, below 1e-4 and 0.03 limits. Checkpointed and eager gradients matched their respective CPU reference to the same reported errors. These are small correctness probes, not optimizer convergence or real-model training validation.

[PyTorch #200999](https://github.com/pytorch/pytorch/issues/200999) motivated the attention checks. Its reported gfx1100 silent-corruption symptom was not reproduced on this gfx1101 stack for these shapes. Eight forced efficient cases were unavailable, so they cannot establish correctness of that backend. No claim is made about untested masks, FLASH-only dispatch, other shapes, or other versions.

Total: **40 case processes** — 28 passed computation checks, eight explicitly unsupported, four reproduced the idle CPU symptom. No new matching kernel instability appeared during any case.

## Reproduction

Place `rocm_probe.py` and `run_rocm_probes.py` together. Inside WSL, use the existing ROCm Python environment; substitute its interpreter for `$ROCM_PYTHON`. Run from the scripts' directory:

```bash
"$ROCM_PYTHON" run_rocm_probes.py --out ./results/initial
"$ROCM_PYTHON" run_rocm_probes.py --focus followup --out ./results/followup
"$ROCM_PYTHON" run_rocm_probes.py --focus cleanup --out ./results/cleanup
```

The runner requires readable kernel logs and refuses to start if existing instability or another visible GPU owner is found. It does not stop other jobs, reboot WSL, reset the GPU, download models, or install packages. Keep result directories distinct to avoid mixing runs. The exported `rocm-results.json` contains measured case outputs, exact case arguments, timestamps, durations, exit statuses, and filtered kernel-error deltas.

## Limits and next experiments

No VRAM exhaustion, experimental AOTriton toggle, concurrent-copy stress, multi-day uptime soak, mounted-storage fixture comparison, or thermal burn-in was run. The repository records a known unstable experimental attention configuration, so it was not retried. These bounded probes do not certify sustained stability or absence of defects. This run reproduced a known class of reliability/performance issue; it did not establish a novel upstream defect. No upstream issue or comment was published.
