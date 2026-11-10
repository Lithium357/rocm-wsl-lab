# DXG make-resident warning during BF16 training

Observed November 9, 2026 at 20:49:53 Mountain time (November 10 at 03:49:53 UTC) on an AMD Radeon RX 7800 XT under Ubuntu on WSL. The run used PyTorch `2.13.0+rocm10.0.0` with experimental AOTriton enabled, BF16 autocast, and two 64,000-token sequences per optimizer step on a 498,578,016-parameter transformer.

The trainer recorded these newly observed kernel messages at optimizer step 149 of attempt 2:

```text
[41806.345046] misc dxg: dxgk: dxgvmb_send_sync_msg: wait_for_completion failed: fffffe00
[41806.366476] misc dxg: dxgk: dxgvmb_send_make_resident: send_make_resident failed fffffe00
[41806.367223] misc dxg: dxgk: dxgkio_make_resident: Ioctl failed: -512
```

The step had a recorded optimizer observation. The trainer's kernel-warning guard stopped the run without an automatic retry. The manifest reports status `failed`, 149 completed updates, 19,072,000 token exposures, and a step-149 checkpoint. The peak PyTorch allocation reported for that step was 14,030,394,880 bytes. That figure measures PyTorch allocations; total device memory use and other GPU activity were not captured by this observation.

The recorded checkpoint SHA-256 is `648d6d16e790b6a646352b091f1b74225b9d0a521a16d0e0fa893d8bf0befe67`. The checkpoint file was present during follow-up. A fresh integrity or resume check has not been performed.

This is a single incident report from the run manifest, optimizer metrics, and kernel delta. The triggering condition and root cause are undetermined.
