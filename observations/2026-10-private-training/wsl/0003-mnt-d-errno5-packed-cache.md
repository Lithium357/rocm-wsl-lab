# 0003 — `/mnt/d` packed-cache read returned `Errno 5` during long CPT

**Status:** Mitigated
**Affected layer:** WSL Windows-mounted filesystem
**Potential audience:** Microsoft WSL filesystem team
**First observed:** 2026-10-14

## Environment

| Field | Value |
| --- | --- |
| GPU | AMD Radeon RX 7800 XT, 16 GB |
| WSL / kernel | 2.7.11.0 / 6.18.33.2-microsoft-standard-WSL2 |
| Workload geometry | Stable Qwen3-4B LoRA CPT control geometry |
| Affected input | 29 GB packed `uint32` token cache read from `/mnt/d` |

## Minimal reproduction

Not yet reduced. The event occurred in a long-running training job while sequentially reading packed blocks from the Windows-mounted volume.

## Observed behavior

After a complete step-2000 checkpoint, the data iterator raised:

```text
OSError: [Errno 5] Input/output error
PackedBlocks.__iter__ -> handle.read(context_length * 4)
```

There was no HIP/PyTorch exception, dxgkrnl warning, explicit OOM, or thermal event at the time.

## Control result

The identical cache copied to WSL ext4 continued training after verifying file size and manifest SHA-256. Sustained throughput was approximately 565 tokens/second.

## Impact

The active job exited after its last durable checkpoint. No completed checkpoint data was lost, but the mounted-volume cache was unsuitable for sustained active reads.

## Mitigation

Keep active read-heavy packed caches on WSL ext4. Windows-mounted storage remains acceptable for archival data and checkpoints.

## Assessment

Observed: the error occurred on `/mnt/d`, and the ext4 copy ran normally. Inference: this is a WSL filesystem/mount reliability issue, not evidence of an AMD GPU defect.
