# 0002 — Larger activation footprint fails through opaque WSL allocation path

**Status:** Candidate external bug
**Affected layer:** WSL GPU virtualization allocation/error reporting
**Potential audience:** Microsoft WSL graphics team, with AMD ROCm visibility
**First observed:** 2026-10-12

## Environment

| Field | Value |
| --- | --- |
| GPU | AMD Radeon RX 7800 XT, 16 GB |
| Windows | 10.0.26200.9711 |
| WSL / kernel | 2.7.11.0 / 6.18.33.2-microsoft-standard-WSL2 |
| PyTorch / ROCm | 2.13.0+rocm10.0.0 |
| HIP runtime | 7.15.26333 |
| Workload geometry | Qwen3-4B LoRA CPT, BF16, context 512, microbatch 1, accumulation 16, activation checkpointing disabled |

## Minimal reproduction

Use the stable geometry above but disable activation checkpointing.

## Observed behavior

Model setup failed before a usable first training step. WSL kernel output included:

```text
dxgk: create_existing_sysmem: get_user_pages_fast failed: 2534
dxgk: dxgvmb_send_sync_msg: wait_for_completion failed: fffffe00
dxgk: create_local_allocations: failed to destroy allocations: fffffe00
dxgk: dxgkio_create_allocation: Ioctl failed: -12
```

PyTorch did not emit an actionable out-of-memory exception.

## Control result

The same workload with activation checkpointing enabled trains stably at roughly 565–570 tokens/second.

## Impact

The failure is hard to diagnose and provides no actionable allocation/VRAM explanation to the user.

## Mitigation

Keep activation checkpointing enabled and use the stable microbatch-one geometry.

## Assessment

Observed: changing activation checkpointing changes the result, and the failing path reports dxg allocation errors. Inference: likely resource exhaustion or allocation failure in the WSL graphics bridge; it is not a confirmed VRAM OOM.
