# Reproduction protocol

## Before a run

1. Use a synthetic workload or public fixture only.
2. Record the Windows, WSL, kernel, GPU-driver, ROCDXG, framework, HIP, and
   Python versions. Do not record serial numbers, account names, or local paths.
3. Establish a fixed baseline using default, documented settings.
4. Change exactly one variable for the affected run.
5. Choose a safe output directory outside the repository for raw logs.

## Required evidence

Each result must include:

- the complete command, with secrets and personal paths removed;
- workload shape and deterministic seed, when applicable;
- baseline and affected outcome;
- wall time or throughput, plus error text if any;
- a short, timestamped kernel-log delta rather than a full `dmesg` dump;
- a stated confidence level: observed, reproduced, or upstream-confirmed.

## Stop conditions

Stop immediately on a GPU reset, a dxg synchronization failure, host or guest
instability, a filesystem I/O error, or an unsafe thermal condition. Preserve
the evidence; do not automatically retry an unstable probe.

Never run a stress test beside production training. A WSL update, driver
change, GPU reset, or `wsl --shutdown` requires the production job to be
intentionally stopped first.

## Attribution rules

An error message from a layer is not proof that the layer caused it. Attribute
only what the control establishes:

| Evidence | Allowed conclusion |
| --- | --- |
| One failed run | Observation only |
| Same failure after one changed variable, with passing control | Candidate external issue |
| Same failure on an upstream-supported version set | Stronger report candidate |
| Maintainer diagnosis or a verified upstream fix | Upstream-confirmed |
