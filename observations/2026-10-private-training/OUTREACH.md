# Vendor reporting and hardware-access checklist

Last reviewed: **2026-10-19**. This is a factual plan for building credibility
with AMD or Intel. It is **not** a promise of hardware, an endorsement, or a
request to publish the private training project's private material.

## Non-negotiable privacy boundary

the private training project contains private training work. Never use its dataset, weights, roleplay
records, private dashboard source, complete logs, local paths, account names,
or chat captures in a public issue, project, benchmark, or social post.

If a public reproduction becomes worthwhile, create a separate tiny repository
containing only a synthetic tensor workload, a redacted environment table, an
exact command, expected/actual output, and the smallest relevant log delta.
This bug ledger can link to that reproduction, but it is not itself a public
repro package.

## AMD: the practical route

AMD's AI Developer Program is free, offers a $100 Developer Cloud credit,
private technical community access, training, and a monthly prize draw. The
current rules specify **two winners per month** in 2026, with an RX 9070 XT
and an AMD AI laptop as the listed prizes. It is an automatic monthly drawing
for eligible program members, not a discretionary hardware-loan program and
not a path to a guaranteed 7900 XTX.

Current official requirements and opportunities:

1. The account holder must join the AI Developer Program. Eligibility for the
   2026 draw is age 18+ and legal residence in the US or Canada; the program
   rules are authoritative if they change.
2. Complete the profile, then take the ROCm certification and relevant AI
   Academy courses. AMD currently assigns points for the profile, courses,
   certification, community help, events, hackathons, and being a featured
   member.
3. Make useful public contributions based on a **sanitized** reproduction:
   answer community questions when qualified, submit an issue only after
   reproducing it, and share a concise benchmark or workaround.
4. Use the program's project-submission path only with a separate,
   deliberately public project. A privacy-safe ROCm/WSL reproduction suite is
   a better candidate than the the private training project repository.

AMD's own ROCm documentation directs Windows users to ROCm GitHub Issues. Do
not post a speculative complaint: a maintainer needs a minimal reproducer,
hardware/runtime version table, exact expected vs. observed behaviour, full
redacted error, one-variable control, and a workaround if known.

Useful official pages, checked on the date above:

- [AMD AI Developer Program](https://developer.amd.com/ai-developer-program/)
- [2026 AMD AI Developer Program Sweepstakes Rules](https://www.amd.com/content/dam/amd/en/documents/developer/ai-developer-program/ai-developer-program-sweepstakes-terms-conditions.pdf)
- [ROCm bug-report channel](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/feedback.html)
- [AMD events and contests](https://developer.amd.com/events/)

## Intel: worthwhile, but a longer shot for physical hardware

There is no current Intel Arc device in this setup, so an Intel GPU bug report
would be invented rather than earned. The credible starting point is instead a
small separate project that demonstrates an OpenVINO deployment or benchmark.
Intel's current OpenVINO Software Innovator application explicitly asks for an
AI project using OpenVINO on GitHub (or another platform), then reviews the
application and schedules a discovery call. Published OpenVINO demos and
technical community contributions earn program credit.

The listed benefits focus on expert access, amplification, events, and
community recognition. They do **not** promise a physical Intel GPU. Treat an
Intel card as a possible relationship outcome after a genuine Intel-targeted
project exists, not as an immediate ask.

- [Intel Software Innovator for OpenVINO](https://www.intel.com/content/www/us/en/developer/community/edge-innovator-program.html)

## Current the private training project evidence: do not overclaim

| Finding | Current status | Next evidence needed before an external report |
| --- | --- | --- |
| Experimental AOTriton triggered a dxg synchronization warning | Candidate external bug | Repeat only with the production trainer stopped; preserve default-SDPA control and exact `dmesg` delta. |
| Disabling activation checkpointing produced a dxg allocation path error | Candidate external bug / expected capacity boundary | Establish whether a normal PyTorch OOM should be surfaced instead; retain minimal script and control. |
| Packed cache on mounted Windows storage returned `Errno 5` | Mitigated WSL/filesystem issue | Repeat a checksum scan and compare against WSL ext4 before reporting. |
| Hyper-V VMBus channel allocation warnings | Observed WSL pressure signal | Reproduce under controlled guest-memory/page-cache pressure and prove whether it affects service reliability. |
| dxg adapter-query ioctl warnings | Observed | Isolate the exact user-space query in a fresh WSL session before assigning impact. |
| Hyper-V VMSwitch Event 285 warning stream | Observed WSL networking telemetry | Pair the warning with a network, session, or service failure before adding evidence to an existing Microsoft issue. |

The detailed observations and controls live in this directory. Their status is
deliberately conservative: a warning line is not proof that AMD, Microsoft,
or PyTorch caused a defect.

## Gate before any public report

- [ ] Existing upstream issues searched; do not duplicate one.
- [ ] A redacted minimal reproducer works independently of the private training project.
- [ ] One normal control and one affected run are recorded.
- [ ] Version table, start/end timestamps, command, and raw redacted error are
      included.
- [ ] Reproduction has no sensitive data, model weights, screenshots, paths,
      or private application source.
- [ ] Expected behaviour, actual behaviour, impact, and workaround are stated
      separately.
- [ ] The report names the affected layer only as a hypothesis unless an
      upstream maintainer confirms it.
