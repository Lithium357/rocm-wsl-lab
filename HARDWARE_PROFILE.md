# Reproduction hardware profile

This is the sanitized host profile for the initial ROCm-on-WSL experiments.
It is a reproducibility aid, not a performance claim or a recommended
configuration. It excludes serial numbers, account details, personal paths,
network identifiers, and private workload data.

Captured: 2026-10-21

| Area | Configuration |
|---|---|
| Host OS | Windows 11 Home, x64, build 26200 |
| Board | ASRock B550 PG Velocita |
| CPU | AMD Ryzen 5 5600 (6 cores / 12 threads) |
| Host memory | 32 GB installed |
| GPU | AMD Radeon RX 7800 XT, 16 GB dedicated VRAM |
| Windows driver | 32.0.31041.1004 |
| Storage | 1 TB SATA SSD and 2 TB NVMe SSD |
| WSL | WSL 2.7.11.0; Linux 6.18.33.2-microsoft-standard-WSL2 |
| WSL allocation observed | 12 vCPUs, 15 GiB RAM, 4 GiB swap |
| ML environment | Python 3.14; PyTorch 2.13.0+rocm10.0.0; Transformers 4.57.6; PEFT 0.20.0 |

## Telemetry caveat

The generic Windows WMI `AdapterRAM` field reports 4 GiB for this RX 7800 XT
under the current WDDM stack. That value is not used by this lab. The 16 GB
figure is from Windows dedicated-GPU-memory telemetry. `rocm-smi` and `amd-smi`
are not exposed inside this particular WSL image, which is itself relevant
when comparing telemetry behavior across setups.

## Reproduction expectations

Use this profile to compare broad platform differences, not to claim that a
failure is universal. Report your own Windows build, WSL/kernel version,
driver version, GPU, framework build, and workload command alongside any
result.
