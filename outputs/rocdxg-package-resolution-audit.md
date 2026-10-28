# ROCm/WSL installed-package resolution manifest

2026-10-28 UTC. Read-only metadata and ELF inspection identified two distinct ROCDXG installations with the same SONAME. This explains why an unversioned lookup might find a different installation, but **does not establish that the running process loaded both or selected an incompatible library**.

| Property | SDK wheel core | System ROCm directory |
|---|---|---|
| Installed distribution | `rocm-sdk-core 10.0.0` | Library filename `1.2.2`; package-manager provenance not collected |
| Available ROCDXG filenames | `librocdxg.so.1` | `.so` and `.so.1` aliases to `.so.1.2.2` |
| ELF SONAME | `librocdxg.so.1` | `librocdxg.so.1` |
| Five topology KMT exports required by profiler | All present | All present |
| Optional `DxgAbiCheck` export | Absent | Present |

The installed wheel's RECORD lists only `_rocm_sdk_core/lib/librocdxg.so.1`, matching its on-disk layout. SDK HIP declares `libhsa-runtime64.so.1` in DT_NEEDED, and the wheel HSA runtime has `$ORIGIN` in its RPATH. HSA does not declare ROCDXG in DT_NEEDED; upstream loads the thunk dynamically, so that absence is expected. The profiler library also has `$ORIGIN` in RPATH. These tags describe search configuration, not the actual library selected at runtime.

Public package versions read from installed metadata: `rocm`, `rocm-sdk-core`, `rocm-sdk-libraries`, and `rocm-sdk-device-gfx1101` are `10.0.0`; `torch` is `2.13.0+rocm10.0.0`; `rocm-bootstrap` is `0.1.0`. This is an installed-metadata snapshot, not independent verification of a registry wheel's bytes or its source commit. The inspector used Python 3.14.4 and readelf; it did not import any of these packages.

[Current upstream ROCr loader source](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/runtime/hsa-runtime/core/runtime/thunk_loader.cpp) was inspected as Git blob `82cc128d454a55d87428946b5647188fe1712ea2`. Its DXG path tries the configured name, an adjacent-library fallback, then the unversioned fallback and adjacent fallback. The installed version's exact source commit was not established, so this is a source-policy comparison, not proof that this binary uses every current fallback.

[Profiler PR #13576](https://github.com/ROCm/rocm-systems/pull/13576) remains open and unmerged at head `65313194df87e824f2d3a3cd8f13dbcc22f8707a`. It already addresses the versioned-name and adjacent-runtime lookup mismatch. Do not duplicate it, apply the withdrawn local patch, add symlinks, or replace installed libraries on this evidence. The optional handshake difference is consistent with the distinction documented in upstream source; its absence alone is not proof of broken ABI or snapshot ownership.

Evidence: `rocdxg-package-resolution-manifest.json`. `$CORE`, `$VENV`, and `$OPT_ROCM` replace local installation roots. The reusable `rocdxg_package_manifest.py` uses only public package metadata, filenames, and readelf output, with ten-second deadlines per ELF operation:

```bash
python3 -I rocdxg_package_manifest.py "$VENV"
```

It writes `package-resolution-manifest.json` alongside the script. Eleven path entries were inspected, including aliases; these are not eleven independent library builds. No AMD runtime/profiler was loaded, no GPU was accessed, and no process was attached. Kernel/GPU telemetry was not collected for this static audit. Next: audit the CLI's empty-agent/output error contract against current upstream tests. A future idle-GPU validation should record only sanitized library-selection evidence; static export presence cannot validate ABI layouts, snapshot lifetimes, or real profiling.
