# BF16 default versus experimental attention: seed 357

Observed 2026-10-28 UTC. Classification: **bounded observation**, not sustained-training
validation or an upstream-confirmed fix. This probe uses generated tensors only.

## Environment

- AMD Radeon RX 7800 XT; reported total VRAM 17,138,180,096 bytes.
- Windows 10.0.26200.9711; AMD driver 32.0.32015.7029, driver date 2026-10-18 UTC.
- WSL 2.7.11.0; kernel 6.18.33.2-microsoft-standard-WSL2.
- ROCDXG package `rocdxg-roct` 1.2.2.
- Python 3.14.4; PyTorch 2.13.0+rocm10.0.0; reported HIP 7.15.26333.

The driver differs from the October 21 hardware profile (32.0.31041.1004). This is not a
matched reproduction of the earlier long-running training observations and does not establish
that a driver change fixed them.

## Workload and commands

Identical generated BF16 query, key and value tensors, each shape `[2,8,128,64]`; CPU input
generator seed 357; causal default SDPA; dropout zero; one forward/backward step on
`mean(output.float() ** 2)`. No pretrained model, data, prompts or adapters are involved.

After activating the intended environment, from the repository root:

```bash
timeout 60s env -u TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL python probes/pytorch_bf16_attention.py --output artifacts/bf16-control-357
timeout 60s env TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 python probes/pytorch_bf16_attention.py --output artifacts/bf16-experimental-357
```

The environment flag is the sole changed workload variable. No CK-preference flag was enabled.
No recognizable production trainer was running. Experimental settings are subprocess-local.

## Corrected raw-timestamp capture pair

| Observation | Default control | Experimental flag = 1 |
| --- | ---: | ---: |
| Started UTC | 22:51:38.492885 | 22:51:54.126569 |
| Forward/backward | completed, finite outputs/gradients | completed, finite outputs/gradients |
| Flash eligibility API | false | true |
| Efficient-attention eligibility API | false | true |
| Peak PyTorch allocated bytes | 166,200,320 | 3,680,256 |
| Loss | 0.07834029197692871 | 0.07834162563085556 |
| New raw-timestamp kernel lines | 0 | 0 |
| Stop-condition kernel lines | 0 | 0 |
| Whole process measurement wall seconds | 2.364437918004114 | 2.3174292359908577 |

These are cold, single-step observations. No throughput/speedup, backend-dispatch identity, numerical
equivalence, long-context feasibility or sustained-stability claim follows from them. Kernel
dispatch was not profiled; API eligibility alone does not identify the executed kernel.

Input SHA-256 hashes matched between conditions:

```text
3e9b4d4671fd6540f4e84f84f95e3616a46bce0921725219e428da27c7c07c6d
a314aca5bdda50e002c55c64683d22037ac6dab20a1d8bc89e75ba93d2570142
68a55748bdf2ed116d81a82491a4b1e4ec2a2c8d320b419f2a481a3129a78b90
```

Descriptive numerical differences, without a post-hoc pass/fail tolerance:

- Output maximum absolute difference: 0.0078125; RMS difference: 0.0005250598187558353.
- Query/key/value gradient maximum absolute differences: each 4.76837158203125e-07.
- Gradient RMS differences: 1.263324644895647e-08, 1.2642238367277514e-08,
  9.003379375371878e-09 respectively.

## Initial pair: invalid kernel-delta instrumentation retained

An earlier identical compute pair also completed with finite tensors. Its capture used
`dmesg --time-format iso` and compared entire strings before/after. Wall-clock conversion
shifted old timestamps by microseconds, causing 2,186 historical WSL broken-pipe lines to be
miscounted as new in the experimental condition. Those lines predated the probe. This was a
capture defect, not evidence of 2,186 new GPU errors.

The original raw artifacts remain preserved outside Git. No kernel-stability conclusion is
drawn from that pair. The capture was changed to raw monotonic kernel timestamps and both
conditions were repeated. The table above uses only the corrected pair. The published probe
retains before, after and delta logs for auditing future captures.

## Scope

No GPU reset, WSL shutdown, runtime installation or driver change was performed. No new kernel
messages were observed in the corrected pair. No full model or 75,000-token workload has been
tested. Preserve the earlier negative observations: this short result does not invalidate them.
