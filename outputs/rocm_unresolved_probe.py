"""Synthetic probes for unresolved allocator, copy, and stream problems."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import json
import os
import time

p = argparse.ArgumentParser()
p.add_argument("mode", choices=["allocator", "minimal_allocator", "threaded_copies", "stream_order"])
p.add_argument("--threads", type=int, default=1)
p.add_argument("--streams", type=int, default=1)
a = p.parse_args()

import torch
torch.set_num_threads(2)
torch.manual_seed(357)
started = time.monotonic()
prop = torch.cuda.get_device_properties(0)
record = dict(mode=a.mode, seed=357, torch=torch.__version__, hip=torch.version.hip,
              gpu=prop.name, arch=prop.gcnArchName,
              allocator_config=os.environ.get("PYTORCH_ALLOC_CONF", "<unset>"))

def emit(**kw):
    record.update(kw)
    record["elapsed_s"] = time.monotonic()-started
    print(json.dumps(record), flush=True)

if a.mode == "minimal_allocator":
    try:
        x = torch.empty(1, device="cuda", dtype=torch.float32)
        x.fill_(357)
        torch.cuda.synchronize()
        if x.cpu().item() != 357: raise RuntimeError("minimal allocation mismatch")
        emit(status="pass", allocation_bytes=4)
    except torch.AcceleratorError as error:
        emit(status="allocation_error", allocation_bytes=4, error_type=type(error).__name__,
             error=str(error).splitlines()[0])
        raise SystemExit(10)
elif a.mode == "allocator":
    mib = 1024**2
    free, total = torch.cuda.mem_get_info()
    # At most 3 GiB live, with at least 6 GiB initially free. No deliberate OOM.
    if free < 6*1024**3:
        emit(status="skipped", reason="less than 6 GiB free", free_bytes=free)
        raise SystemExit(0)
    sizes = [128, 256, 384, 512, 640, 768]
    live = {}
    allocations = 0
    peak_live = 0
    def check_all():
        for tensor, value in live.values():
            low, high = torch.aminmax(tensor)
            if low.item() != value or high.item() != value:
                raise RuntimeError("live allocation data mismatch")
    for cycle in range(36):
        slot = cycle % 5
        live.pop(slot, None)
        if cycle % 3 == 0:
            gc.collect()
            torch.cuda.empty_cache()
        size = sizes[(cycle*5+cycle//5) % len(sizes)]*mib
        current = sum(t.numel() for t, _ in live.values())
        if current+size > 3*1024**3:
            # Keep the same deterministic budget in both allocator variants.
            for key in list(live):
                del live[key]
                current = sum(t.numel() for t, _ in live.values())
                if current+size <= 3*1024**3: break
        tensor = torch.empty(size, device="cuda", dtype=torch.uint8)
        value = cycle+1
        tensor.fill_(value)
        live[slot] = (tensor, value)
        del tensor
        allocations += 1
        torch.cuda.synchronize()
        check_all()
        peak_live = max(peak_live, sum(t.numel() for t, _ in live.values()))
    stats = torch.cuda.memory_stats()
    snapshot = torch.cuda.memory_snapshot()
    segments = [s for s in snapshot if s.get("is_expandable", False)]
    emit(status="pass", allocations=allocations, cycles=36, initial_free_bytes=free,
         peak_live_bytes=peak_live, peak_reserved_bytes=torch.cuda.max_memory_reserved(),
         expandable_segments_in_snapshot=len(segments), allocation_retries=stats.get("num_alloc_retries"),
         oom_count=stats.get("num_ooms"))
elif a.mode == "threaded_copies":
    # Equal total work: one thread x400, or two threads x200; two independent buffers.
    hosts = [torch.arange(262144, dtype=torch.float32)+i for i in range(2)]
    device = [torch.empty_like(x, device="cuda") for x in hosts]
    for x, d in zip(hosts, device): d.copy_(x)
    torch.cuda.synchronize()
    def worker(worker_id):
        stream = torch.cuda.Stream()
        checked = 0
        with torch.cuda.stream(stream):
            for i in range(400//a.threads):
                slot = (i % 2) if a.threads == 1 else worker_id
                device[slot].copy_(hosts[slot], non_blocking=True)
                stream.synchronize()
                actual = device[slot].cpu()
                if not torch.equal(actual, hosts[slot]): raise RuntimeError("threaded copy mismatch")
                checked += 1
        return checked
    if a.threads == 1:
        counts = [worker(0)]
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            counts = list(executor.map(worker, range(2)))
    torch.cuda.synchronize()
    emit(status="pass", threads=a.threads, total_round_trips=sum(counts), bytes_per_copy=1048576)
elif a.mode == "stream_order":
    x = torch.zeros(4096, device="cuda", dtype=torch.int32)
    streams = [torch.cuda.Stream() for _ in range(a.streams)]
    for stream in streams: stream.wait_stream(torch.cuda.current_stream())
    previous = None
    events = []
    # A dependency orders every update, so concurrent writes are never intentional.
    for i in range(2048):
        stream = streams[i % a.streams]
        with torch.cuda.stream(stream):
            if previous is not None: stream.wait_event(previous)
            x.add_(1)
            event = torch.cuda.Event()
            event.record(stream)
            previous = event
            events.append(event)
    torch.cuda.synchronize()
    if not torch.equal(x.cpu(), torch.full((4096,), 2048, dtype=torch.int32)):
        raise RuntimeError("event-ordered stream update mismatch")
    emit(status="pass", streams=a.streams, ordered_updates=2048)
