# Controlled external-runtime test matrix

Run these only after a durable training checkpoint and with the production
trainer stopped. Never run a stress probe beside the active CPT job.

| Probe | One changed variable | Control | Evidence to retain | Risk |
| --- | --- | --- | --- | --- |
| Default attention baseline | None | Same short run repeated | step time, token rate, `dmesg` delta | Low |
| WSL bridge wiring audit | No GPU workload; verify `/dev/dxg`, DXCore, ROCDXG package/version, and process library mappings | Same checks after a fresh WSL restart | version table and sanitized mapping summary | Low: read-only inspection only |
| WSL release baseline | Update from the recorded WSL 2.7.11 / kernel 6.18.33.2 to a current stable release, then run the fixed SDPA control | Pre-update fixed SDPA control and wiring audit | WSL/kernel versions, step-time distribution, `dmesg` delta, service/interop status | Medium: requires `wsl --shutdown`; only after a durable checkpoint and intentional production stop. Do not assume an update is a fix. |
| AMD-published reference runtime | Clean isolated environment with the current WSL matrix's production PyTorch/ROCm pair | Current PyTorch 2.13 / ROCm 10 environment | package versions, short baseline, `dmesg` delta | Medium: create only after the production trainer is stopped; do not modify its environment |
| AOTriton experimental attention | `TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1` | Default SDPA | full stderr, `dmesg` dxg delta, supported-version check | Medium: stop on first bridge warning; currently an unsupported-path investigation |
| Activation-memory boundary | Disable activation checkpointing | Enabled checkpointing | PyTorch error plus dxg lines | Medium: expected allocation failure |
| dxg capability-query noise | One minimal ROCm/PyTorch device query | Fresh WSL session without query | timestamped `dmesg` delta | Low |
| Windows-mounted cache reliability | Read-only sequential scan from `/mnt/d` | Same cache on WSL ext4 | checksums, I/O error, `dmesg` | Low |
| WSL VMBus allocation pressure | Controlled WSL memory cap/cache pressure | Default cap with no pressure | `free -h`, `/proc/buddyinfo`, `dmesg`, new-session/interop result | Medium: no production workload; correlate with [WSL#40795](https://github.com/microsoft/WSL/issues/40795), do not duplicate it without impact |
| WSL Hyper-V firewall Event 285 | Observe warning time window with one normal WSL-to-Windows interop request | Stable WSL uptime and active service | Event 285 count/time range, WSL uptime, service restarts, interop result | Low: telemetry correlation only; do not change firewall settings or report without a user-visible network/VM failure |
| GPU-PV uptime soak | Fixed short SDPA control at fresh WSL start, then after 24 and 72 hours of normal host uptime | Fresh-session control, same environment and geometry | step-time distribution, error count since session start, GPU clocks/thermals, WSL uptime | Medium: investigate only after production CPT stops; no GPU resets, no concurrent workload, and do not infer a regression from timing alone |

## Stop conditions

Stop a probe immediately on a GPU reset, dxg bridge synchronization failure,
filesystem I/O error, sustained thermal limit, or host instability. Capture
logs first; do not retry a suspected unstable configuration unattended.
