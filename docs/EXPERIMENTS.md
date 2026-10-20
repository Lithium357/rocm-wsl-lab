# Experiment registry

Run these only when no production workload owns the GPU.

| ID | Probe | Variable | Control | Status | Safety gate |
| --- | --- | --- | --- | --- | --- |
| WSL-001 | Bridge wiring audit | None: inspect `/dev/dxg`, DXCore, ROCDXG, and library paths | Fresh WSL session | Planned | Read-only |
| WSL-002 | Stable framework control | Default attention path | Repeated same command | Planned | Short synthetic run |
| WSL-003 | Experimental attention | One documented experimental attention toggle | WSL-002 | Planned | Stop at first dxg warning |
| WSL-004 | Allocation boundary | One activation/memory setting | WSL-002 | Planned | Expect a clean framework error; stop on bridge failure |
| WSL-005 | Mounted-storage read reliability | Read-only scan from mounted Windows storage | Identical ext4 scan | Planned | No training data or writes |
| WSL-006 | GPU-PV uptime soak | Fixed synthetic control at fresh, 24h, and 72h WSL uptime | Fresh control | Planned | No GPU reset or concurrent workload |
| WSL-007 | WSL release baseline | One stable WSL/kernel update | Pre-update WSL-002 | Planned | Requires a durable checkpoint and intentional shutdown |
| WSL-008 | AMD-supported framework baseline | Clean AMD-published WSL PyTorch/ROCm pairing | Existing environment | Planned | Separate disposable environment |

Do not mark an experiment complete without attaching a sanitized result note.
