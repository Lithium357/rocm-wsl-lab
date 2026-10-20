# 0005 — dxg adapter capability queries emit `-22` and `-2` ioctl failures

**Status:** Observed
**Affected layer:** WSL dxgkrnl capability/query interface
**Potential audience:** Microsoft WSL graphics team, with ROCm visibility
**First observed:** 2026-10-19

## Environment

| Field | Value |
| --- | --- |
| GPU | AMD Radeon RX 7800 XT, 16 GB |
| Windows | 10.0.26200.9711 |
| WSL / kernel | 2.7.11.0 / 6.18.33.2-microsoft-standard-WSL2 |
| PyTorch / ROCm | 2.13.0+rocm10.0.0 |

## Observed behavior

The WSL kernel log records repeated dxg capability and adapter-query failures:

```text
misc dxg: dxgk: dxgkio_is_feature_enabled: Ioctl failed: -22
misc dxg: dxgk: dxgkio_query_adapter_info: Ioctl failed: -22
misc dxg: dxgk: dxgkio_query_adapter_info: Ioctl failed: -2
```

The same WSL session successfully exposes the GPU to the long-running ROCm
training process, which remains active.

## Minimal reproduction

Not yet isolated. The messages appear near GPU-client initialization events in
the kernel log, but no single client has been identified.

## Control result

Not yet collected. The planned control is a fresh WSL session with one minimal
ROCm/PyTorch device query, then a second session without the query.

## Impact

No visible training failure or throughput regression has been tied to these
messages. Their current impact is diagnostic ambiguity: normal GPU use is
accompanied by ioctl failures that look fatal without context.

## Mitigation

None. Keep the raw surrounding kernel lines when a future ROCm failure occurs
so this background noise is not misattributed.

## Assessment

Observed: these errors occur while the GPU remains usable. Inference: the
queries may target unsupported optional features or a missing adapter-info
path. This is not yet a demonstrated correctness or performance bug.
