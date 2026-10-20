# 0006 — Recurrent WSL Hyper-V firewall Event 285 timing warnings

**Status:** Observed
**Affected layer:** Windows Hyper-V VMSwitch / WSL firewall telemetry
**Potential audience:** Microsoft WSL networking team
**First observed:** 2026-10-18

## Environment

| Field | Value |
| --- | --- |
| Windows host version reported by WSL | 10.0.26200.9711 |
| WSL / kernel | 2.7.11.0 / 6.18.33.2-microsoft-standard-WSL2 |
| WSL configuration file | No user `.wslconfig` was present at observation time |
| Active workload | Long Qwen3-4B LoRA CPT under a persistent user systemd service |

## Observed behavior

The Windows `Microsoft-Windows-Hyper-V-VmSwitch-Operational` channel recorded
**907** Event ID 285 warnings for the `WSL (Hyper-V firewall)` switch from
2026-10-18 01:12:07 through 2026-10-19 19:11:14 local time. Every sampled
entry had the same internally inconsistent timing text:

```text
V-Switch operation OID_GEN_STATISTICS (131334) took too long to complete.
Operation Type: NDIS PNP.
Execution time 0 ms. Queued time 0 ms. Expected execution time less than 0 ms.
SwitchName: WSL (Hyper-V firewall).
```

The count is high enough to be useful diagnostic evidence. It is not proof of
packet loss, a GPU error, or a WSL VM restart.

## Control result

During the observation:

- WSL had been up for more than five days.
- The CPT systemd service was active with `NRestarts=0`.
- A normal WSL-to-Windows interop command (`cmd.exe /c ver`) completed.
- No GPU reset, trainer exit, or user-visible networking failure was observed.

The warning therefore has no demonstrated runtime impact on this machine yet.

## Related upstream issue

[microsoft/WSL#40363](https://github.com/microsoft/WSL/issues/40363) is open
and contains the same Event 285 message on the same `WSL (Hyper-V firewall)`
switch. A later user report in that issue specifically notes that the
zero-millisecond / `less than 0 ms` form can continue during healthy uptime,
so a bare Event 285 count is not enough to diagnose a VM or network failure.

This observation should be contributed to that existing issue only if it can
be paired with a timestamped service interruption, WSL VM restart, failed
interop, DNS/routing failure, packet loss, or a reproducing configuration.

## Mitigation

No firewall, networking, registry, or WSL configuration was changed. Disabling
the Hyper-V firewall to suppress a warning would alter the host's security
posture and is not justified without a demonstrated failure and controlled
before/after evidence.

## Assessment

Observed: Windows emits a persistent, internally contradictory timing warning
for the WSL firewall virtual switch. Inference: this may be a telemetry
threshold/reporting defect or a symptom of a separate networking issue. The
current system is healthy, so this is a Microsoft WSL-networking lead only,
not an AMD/ROCm report and not a duplicate issue filing.
