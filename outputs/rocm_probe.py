"""Synthetic ROCm correctness probes. Run via run_rocm_probes.py in WSL."""
import argparse
import contextlib
import json
import math
import resource
import time
import os
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("mode", choices=["smoke", "attention", "idle", "copies", "training"])
p.add_argument("--dim", type=int, default=256)
p.add_argument("--length", type=int, default=128)
p.add_argument("--dtype", choices=["float32", "bfloat16"], default="float32")
p.add_argument("--backend", choices=["default", "math", "efficient"], default="default")
p.add_argument("--release", action="store_true")
a = p.parse_args()

import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend

torch.set_num_threads(2)
torch.manual_seed(357)
t0 = time.monotonic()
record = dict(mode=a.mode, seed=357, torch=torch.__version__, hip=torch.version.hip)

def emit(**kw):
    prop = torch.cuda.get_device_properties(0)
    record.update(gpu=prop.name, arch=prop.gcnArchName, total_bytes=prop.total_memory)
    record.update(kw)
    record["elapsed_s"] = time.monotonic() - t0
    print(json.dumps(record), flush=True)

if a.mode == "smoke":
    x = torch.arange(4096, dtype=torch.float32, device="cuda")
    y = x * 2 + 1
    torch.cuda.synchronize()
    torch.testing.assert_close(y.cpu(), torch.arange(4096) * 2 + 1, check_dtype=False, rtol=0, atol=0)
    emit(status="pass")
elif a.mode == "attention":
    dtype = getattr(torch, a.dtype)
    shape = (1, 4, a.length, a.dim)
    cpu = [torch.randn(shape).to(dtype) for _ in range(3)]
    q, k, v = [x.double() for x in cpu]
    ref = torch.softmax(q @ k.transpose(-1, -2) / math.sqrt(a.dim), dim=-1) @ v
    tensors = [x.to("cuda") for x in cpu]
    ctx = contextlib.nullcontext() if a.backend == "default" else sdpa_kernel(
        [SDPBackend.MATH if a.backend == "math" else SDPBackend.EFFICIENT_ATTENTION])
    try:
        with ctx:
            out = F.scaled_dot_product_attention(*tensors)
        torch.cuda.synchronize()
    except RuntimeError as e:
        if "No available kernel" in str(e) or "No viable backend" in str(e):
            emit(status="unsupported", backend=a.backend, dtype=a.dtype, shape=shape)
            raise SystemExit(0)
        raise
    actual = out.cpu().double()
    rel = ((actual-ref).norm()/ref.norm()).item()
    max_abs = (actual-ref).abs().max().item()
    tol = 0.02 if dtype == torch.bfloat16 else 0.0001
    good = torch.isfinite(actual).all().item() and rel < tol
    emit(status="pass" if good else "incorrect", backend=a.backend, dtype=a.dtype,
         shape=shape, relative_l2=rel, max_absolute_error=max_abs, relative_l2_limit=tol)
    if not good: raise SystemExit(10)
elif a.mode == "idle":
    def threads():
        snapshot = {}
        for path in Path("/proc/self/task").iterdir():
            try:
                fields = (path/"stat").read_text().rsplit(")", 1)[1].split()
                snapshot[path.name] = ((path/"comm").read_text().strip(), int(fields[11])+int(fields[12]))
            except FileNotFoundError:
                pass
        return snapshot
    def cpu_s():
        r = resource.getrusage(resource.RUSAGE_SELF)
        return r.ru_utime + r.ru_stime
    c0, w0 = cpu_s(), time.monotonic()
    time.sleep(5)
    before = 100*(cpu_s()-c0)/(time.monotonic()-w0)
    x = torch.ones(4096, device="cuda")
    x.add_(1)
    torch.cuda.synchronize()
    thread0 = threads()
    c0, w0 = cpu_s(), time.monotonic()
    time.sleep(5)
    elapsed = time.monotonic()-w0
    after = 100*(cpu_s()-c0)/elapsed
    thread1 = threads()
    hot = [{"name": name, "cpu_percent": 100*(ticks-thread0.get(tid, (name, ticks))[1])/os.sysconf("SC_CLK_TCK")/elapsed}
           for tid, (name, ticks) in thread1.items()]
    libs = sorted({Path(line.split()[-1]).name for line in Path("/proc/self/maps").read_text().splitlines()
                   if any(x in line for x in ["libhsa", "librocdxg", "libamdhip64"])})
    released = None
    if a.release:
        import gc
        del x
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        c0, w0 = cpu_s(), time.monotonic()
        time.sleep(5)
        released = 100*(cpu_s()-c0)/(time.monotonic()-w0)
    emit(status="observed", baseline_cpu_percent=before, post_gpu_cpu_percent=after,
         interval_s=elapsed, high_idle_cpu=after > 50, hot_threads=sorted(hot, key=lambda x: -x["cpu_percent"])[:4], library_basenames=libs,
         after_tensor_release_and_empty_cache_cpu_percent=released)
elif a.mode == "training":
    from torch.utils.checkpoint import checkpoint
    dtype = getattr(torch, a.dtype)
    source = [torch.randn(16, 64).to(dtype), (torch.randn(64, 64)/8).to(dtype), (torch.randn(64, 64)/8).to(dtype)]
    def block(x, w1, w2):
        return F.gelu(x @ w1) @ w2
    cpu = [x.double().requires_grad_() for x in source]
    reference_loss = block(*cpu).square().mean()
    reference_loss.backward()
    outcomes = []
    for checkpointed in [False, True]:
        tensors = [x.to("cuda").requires_grad_() for x in source]
        start = time.monotonic()
        for step in range(16):
            for t in tensors: t.grad = None
            y = checkpoint(block, *tensors, use_reentrant=False) if checkpointed else block(*tensors)
            loss = y.float().square().mean()
            loss.backward()
            torch.cuda.synchronize()
            if not torch.isfinite(loss).item(): raise RuntimeError("nonfinite loss")
        errors = [((t.grad.cpu().double()-r.grad).norm()/r.grad.norm()).item() for t, r in zip(tensors, cpu)]
        outcomes.append(dict(checkpointed=checkpointed, steps=16, wall_s=time.monotonic()-start,
                             loss=loss.item(), gradient_relative_l2=errors))
    limit = 0.03 if dtype == torch.bfloat16 else 0.0001
    good = all(math.isfinite(e) and e < limit for o in outcomes for e in o["gradient_relative_l2"])
    emit(status="pass" if good else "incorrect", dtype=a.dtype, outcomes=outcomes, gradient_relative_l2_limit=limit)
    if not good: raise SystemExit(10)
elif a.mode == "copies":
    x = torch.arange(262144, dtype=torch.float32)
    dest = torch.empty_like(x, device="cuda")
    start = time.monotonic()
    for _ in range(100):
        dest.copy_(x)
        back = dest.cpu()
        if not torch.equal(x, back): raise RuntimeError("copy mismatch")
    torch.cuda.synchronize()
    emit(status="pass", iterations=100, bytes_per_copy=x.numel()*x.element_size(),
         copy_wall_s=time.monotonic()-start)
