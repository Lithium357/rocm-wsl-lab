# 0001 — Experimental AOTriton attention triggers dxg synchronization failures

**Status:** Candidate external bug
**Affected layer:** Experimental ROCm attention path interacting with WSL GPU virtualization
**Potential audience:** AMD ROCm and Microsoft WSL graphics teams
**First observed:** 2026-10-12

## Environment

| Field | Value |
| --- | --- |
| GPU | AMD Radeon RX 7800 XT, 16 GB |
| Windows | 10.0.26200.9711 |
| WSL / kernel | 2.7.11.0 / 6.18.33.2-microsoft-standard-WSL2 |
| PyTorch / ROCm | 2.13.0+rocm10.0.0 |
| HIP runtime | 7.15.26333 |
| Workload geometry | Qwen3-4B LoRA CPT, BF16, context 512, microbatch 1, accumulation 16, activation checkpointing |

## Minimal reproduction

Run the otherwise stable workload with only `TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1` added.

## Observed behavior

Steps 1 and 2 completed at roughly 508 and 716 tokens/second. WSL then emitted:

```text
memcpy: detected field-spanning write ... dxgvmbus.c:3095
WARNING: ... dxgvmb_send_wait_sync_object_gpu
dxgk: dxgkio_wait_sync_object_cpu: wait_completion_interruptible: -512
dxgk: dxgkio_wait_sync_object_cpu: Ioctl failed: -512
```

The benchmark was stopped rather than allowed to continue after the bridge warnings.

## Control result

Default SDPA with identical geometry completed 250 steps at a 14.367 second median step time and 570.20 tokens/second without a new dxgkrnl warning.

## Impact

The experimental path is not suitable for unattended CPT on this WSL/RDNA3 setup. The two successful steps are not a performance result.

## Mitigation

Use default SDPA. Do not enable the experimental AOTriton variable for the production run.

## Supportedness context

AMD's current [Radeon limitations and recommended
settings](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/limitations/limitationsrad.html)
state that AO Triton is disabled by default on RX 7000-series Radeon products
for the documented PyTorch 2.9 configuration and must be manually enabled.
That documentation does not cover this exact PyTorch/ROCm version or the dxg
failure above, but it confirms that this is an explicitly experimental path on
the affected GPU family. Reproduce on a current supported software set before
presenting it as a new AMD issue.

The current WSL matrix lists the RX 7800 XT, but its named production framework
pair is PyTorch 2.9.1 / ROCm 7.2.1. The observed PyTorch 2.13 / ROCm 10 build
is not a listed production combination, which further makes a reference-stack
reproduction mandatory before escalation.

## Upstream WSL correlation

Microsoft's WSL tracker has a report for the exact field-spanning-write warning
at `dxgvmbus.c:3095` in `dxgvmb_send_wait_sync_object_gpu`, under a sustained
PyTorch training workload with many GPU synchronization operations. Microsoft
directed a duplicate report for the same signature to that issue. Those
reports use NVIDIA hardware and different framework builds, so they do **not**
establish an AMD-specific failure or prove the same root cause here. They do,
however, make the WSL GPU-PV synchronization layer a concrete comparison point
for a future AMD reference-stack reproduction.

Source: [Microsoft WSL issue 41017](https://github.com/microsoft/WSL/issues/41017)
and its [duplicate-linking discussion](https://github.com/microsoft/WSL/issues/41060).

## Assessment

Observed: the experimental toggle and dxg synchronization warnings coincide; the default control completes normally. Inference: this may be a WSL bridge bug, ROCm interaction, or unsupported experimental path. Vendor ownership is not confirmed.
