# Experiment registry

Run these only when no production workload owns the GPU.

| ID | Probe | Variable | Control | Status | Safety gate |
| --- | --- | --- | --- | --- | --- |
| WSL-001 | Bridge wiring audit | None: run `scripts/capture_environment.sh` | Fresh WSL session | Ready | Read-only snapshot |
| WSL-002 | Stable HIP control | Run `scripts/run_hip_smoke.sh` twice | Same command and environment | Ready | Trainer must be stopped |
| WSL-003 | Experimental attention | One documented experimental attention toggle | WSL-002 | Planned | Stop at first dxg warning |
| WSL-004 | Allocation boundary | One activation/memory setting | WSL-002 | Planned | Expect a clean framework error; stop on bridge failure |
| WSL-005 | Mounted-storage read reliability | Read-only scan from mounted Windows storage | Identical ext4 scan | Planned | No training data or writes |
| WSL-006 | GPU-PV uptime soak | Fixed synthetic control at fresh, 24h, and 72h WSL uptime | Fresh control | Planned | No GPU reset or concurrent workload |
| WSL-007 | WSL release baseline | One stable WSL/kernel update | Pre-update WSL-002 | Planned | Requires a durable checkpoint and intentional shutdown |
| WSL-008 | AMD-supported framework baseline | Clean AMD-published WSL PyTorch/ROCm pairing | Existing environment | Planned | Separate disposable environment |
| MGPU-001 | Two-adapter discovery | Two physical AMD GPUs; inspect WSL → ROCDXG → HSA → HIP enumeration | Each adapter queried independently | Blocked: second GPU required | Production stopped; disposable environment |
| MGPU-002 | Independent two-device compute | One generated kernel/context per HIP device | MGPU-001 | Blocked: MGPU-001 | Stop on first dxg warning |
| MGPU-003 | Host-staged collective | Two-rank generated-buffer all-reduce | MGPU-002 | Blocked: MGPU-002 | No VRAM-pooling claim |

Do not mark an experiment complete without attaching a sanitized result note.
