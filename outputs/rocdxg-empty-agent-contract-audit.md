# Empty-agent CLI contract audit

2026-10-28 UTC. The unmodified upstream `rocprofv3-avail.py` CLI returns successful, silent completion when its Python inventory backend reports no GPU agents. This is a conditional CLI behavior reproduced with an inert backend, **not an installed profiler or WSL failure**. An empty list can be legitimate; no specification requiring a nonzero exit was established, so no defect or fix is claimed.

| Synthetic inventory / selector | Effective exit | stdout | stderr |
|---|---|---|---|
| Empty inventory | 0 | Empty | Empty |
| CPU-only inventory | 0 | Empty | Empty |
| One generated GPU | 0 | Includes the generated GPU marker | Empty |
| Same GPU, explicitly unmatched device 99 | 0 | Empty | Empty |

The GPU-present row is the passing output control. Only inventory contents or the device selector changes. Four fresh Python processes ran with five-second deadlines. Source Git blob `bcfb251c5daad1b171f667abad7276e37dd0a9d1` is verified before execution. The harness calls the real parser, `main`, `process_list`, `list_basic_agent`, and formatting functions; only `rocprofv3.avail` is supplied as an inert Python module. `main()` returns `None`, which the script's actual `sys.exit(ec)` convention maps to exit zero. Python version: 3.14.4.

Source inspection of the real Python backend (`avail.py`, blob `90448b526e2fc376d9ecf95ad15e5d9e5f35c216`) shows `get_agent_info_map()` iterating the native handle list without an explicit empty-list error. The native library's initialization and diagnostics were not executed. They may report a loader failure independently; these fixtures cannot establish whether installed users see silent failure.

Current integration coverage already has GPU-output assertions: `rocprofv3-avail-test-info` and `rocprofv3-avail-test-list` use `PASS_REGULAR_EXPRESSION` matching a GPU line. The two `pmc-check` execute tests in the inspected CMake source lack that output assertion. Existing open, unmerged [PR #9211](https://github.com/ROCm/rocm-systems/pull/9211), checked at head `3e8fd89762a3557447658f9685603d20c379c1f8`, already adds CLI coverage and `pmc-check` output assertions. Do not duplicate those changes. The test files inspected were `tests/rocprofv3-avail/CMakeLists.txt` (blob `dd185bb31915d7458e9a99b579386eb0d4a69ac5`) and `validate.py` (blob `13216a13d5dfe5e79acf3a429d924adf600058ca`).

The loader repair remains tracked separately by [PR #13576](https://github.com/ROCm/rocm-systems/pull/13576). A successful CLI exit alone must not be used as the success criterion for future WSL GPU discovery tests: require an expected synthetic GPU or an explicit supported skip reason. This is a proposed test acceptance rule, not a claim that every empty inventory is erroneous.

Reproduction: extract `rocdxg-empty-agent-fixtures.zip` into a disposable directory and run:

```bash
python3 -I audit_empty_agents.py
```

Expected output is the four-row result above; the harness asserts that pattern. All native-runtime imports are replaced before the CLI is loaded. No AMD runtime/profiler was loaded, no GPU accessed, and no production process attached. Kernel logs and GPU telemetry were not collected because this is a Python-only contract test. Evidence is in `rocdxg-empty-agent-results.json`; raw fixture sources remain under work.

Next: trace the native availability library's zero-agent path and WSL detection/visibility gates in pinned source, using actual functions and injected inert inputs where practical. Distinguish loader diagnostics, unsupported hardware filtering, and a legitimate zero-device host before proposing any error-policy change.
