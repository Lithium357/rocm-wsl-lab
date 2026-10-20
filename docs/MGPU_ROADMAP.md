# WSL ROCm multi-GPU roadmap

## Bottom line

There is no supported Windows setting that turns current WSL ROCm into a
multi-GPU training platform. `MESA_D3D12_DEFAULT_ADAPTER_NAME` selects one
adapter for Mesa's D3D12 graphics backend; it does not make extra HIP devices
appear. `HIP_VISIBLE_DEVICES` can hide or reorder already-visible HIP devices;
it cannot expose another GPU.

AMD's Radeon mGPU documentation says Microsoft does not currently support mGPU
setup in WSL. An AMD ROCDXG maintainer separately states that ROCDXG does not
support multi-GPU today, while leaving open the possibility of partial support.
That maintainer also notes that GPUs would not share VRAM; system memory is the
only common memory path.

Sources: [AMD mGPU limits](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-6.3.2/docs/install/native_linux/mgpu.html),
[AMD ROCDXG maintainer comment](https://github.com/ROCm/librocdxg/issues/33#issuecomment-2861238576).

## What Windows appears to expose already

This is not automatically a request to make Windows expose more hardware.
Microsoft's DirectML documentation shows WSL processes enumerating multiple
compatible host adapters. Its older WSL graphics tutorial describes selecting
one adapter at a time for the Mesa D3D12 path. Those are different APIs and
neither promises multi-device HIP support.

The current public ROCDXG development source also calls `D3DKMTEnumAdapters3`
and constructs a `WDDMDevice` for each supported adapter. Its topology code
stores multiple WDDM devices. This is promising scaffolding, not evidence that
released ROCDXG/HIP supports mGPU end-to-end.

Sources: [Microsoft DirectML device enumeration](https://learn.microsoft.com/en-us/windows/ai/directml/gpu-faq),
[Microsoft WSL GPU guide](https://github.com/MicrosoftDocs/WSL/blob/main/WSL/tutorials/gpu-compute.md),
[ROCDXG device enumeration](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/dxg/wddm/device.cpp),
[ROCDXG topology](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/dxg/topology.cpp).

## The integration target

```text
Multiple Windows adapters
          │
          ├── GPU-PV / WSL exposes adapter handles
          │
          ├── ROCDXG maps every supported handle to a stable HSA agent
          │
          ├── HIP exposes every agent as a usable device/context
          │
          ├── RCCL transports collectives across devices
          │
          └── PyTorch DDP/FSDP uses those collectives
```

The first viable milestone is **independent multi-device compute**, not pooled
VRAM. Two cards should each allocate and execute kernels. A second milestone
is host-staged collectives. Only after that should DDP and model sharding be
attempted.

## Acceptance ladder

Run only after production training is intentionally stopped, in a disposable
environment, and with two physical AMD GPUs installed.

| Stage | Requirement | Pass condition | If it fails, investigate |
| --- | --- | --- | --- |
| 0. Hardware baseline | Two AMD GPUs, current stable Windows/WSL and an AMD-published ROCm environment | Both adapters visible in Windows | Host driver / physical setup |
| 1. Discovery | `rocminfo` and a tiny HIP program | Two HSA GPU agents and `hipGetDeviceCount() == 2` | ROCDXG adapter discovery / HSA topology |
| 2. Independent contexts | One generated tensor/kernel per device | GPU 0 and GPU 1 complete separately | Device-context lifecycle / memory manager |
| 3. Topology contract | Query peer access and memory on each device | Accurate answers; `false` peer access is acceptable | ROCDXG topology / WDDM mappings |
| 4. Collective baseline | Two-rank all-reduce on generated buffers | Correct result, explicit transport and timing | RCCL transport / host staging |
| 5. Framework DDP | Small synthetic model, one rank per GPU | Stable forward/backward and all-reduce | PyTorch ROCm/RCCL integration |
| 6. Sharding | Small FSDP or tensor-parallel model | Fits and trains without device loss | Framework strategy; expect much lower speed without peer VRAM |

## Patch boundaries

### ROCDXG / ROCr

This is the likely first open-source patch surface. Audit the multi-adapter
enumeration already present in the development branch and make sure each HSA
agent has a stable adapter handle, context, queue, memory accounting, event,
and topology mapping. Add a two-adapter synthetic test; do not claim support
until stages 1–3 pass from a released artifact.

### Microsoft WSL GPU-PV

If DirectML can see both adapters but ROCDXG cannot make two HSA agents, start
with ROCDXG. If the WSL guest itself supplies only one usable adapter handle,
Microsoft owns the missing GPU-PV capability. A vendor report then needs the
stage-1 discovery evidence and a privacy-scrubbed WSL log bundle.

### RCCL and PyTorch

Treat collectives as a separate capability. No peer VRAM means no transparent
VRAM pool. DDP can improve throughput by replicating the model; FSDP/tensor
parallelism can shard a model but needs inter-device transfers and may be
slow through host memory.

## Explicit non-solutions

- Setting `MESA_D3D12_DEFAULT_ADAPTER_NAME` for HIP training.
- Setting `HIP_VISIBLE_DEVICES` before two usable HIP devices exist.
- Pretending two 16 GB cards form one 32 GB allocator.
- Running two independent training jobs and calling that distributed training.
- Changing drivers, WSL, or power settings while a production job is active.

## First contribution target

Create a minimal generated-tensor **two-adapter discovery test** that records:

1. Windows adapter count and sanitized driver version.
2. WSL adapter/ROCDXG discovery result.
3. HSA agent list and HIP device count.
4. Per-device context creation and one tiny kernel result.
5. A control run on each device separately.

That test determines whether the first patch belongs in ROCDXG or requires a
Microsoft GPU-PV escalation. It does not require Lucy data, model weights, or
private application code.
