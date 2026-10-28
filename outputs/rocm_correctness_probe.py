"""Bounded synthetic checks for open PyTorch/ROCm correctness reports."""
import argparse
import gc
import hashlib
import json
import time
import warnings

p = argparse.ArgumentParser()
p.add_argument("mode", choices=["sparse", "dropout", "graphs"])
p.add_argument("--sync", choices=["false", "true"], default="false")
a = p.parse_args()

import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
torch.set_num_threads(2)
torch.manual_seed(357)
started = time.monotonic()
prop = torch.cuda.get_device_properties(0)
record = dict(mode=a.mode, seed=357, torch=torch.__version__, hip=torch.version.hip,
              gpu=prop.name, arch=prop.gcnArchName)

def emit(**kw):
    record.update(kw)
    record["elapsed_s"] = time.monotonic()-started
    print(json.dumps(record), flush=True)

def digest(tensor):
    return hashlib.sha256(tensor.detach().cpu().numpy().tobytes()).hexdigest()

if a.mode == "sparse":
    torch.use_deterministic_algorithms(True)
    g = torch.Generator().manual_seed(357)
    n, width = 10000, 64
    rows = torch.cat([torch.randint(n, (200000,), generator=g), torch.zeros(50000, dtype=torch.int64)])
    cols = torch.randint(n, (len(rows),), generator=g)
    matrix = torch.sparse_coo_tensor(torch.stack([rows, cols]), torch.rand(len(rows), generator=g), (n,n)).coalesce()
    dense = torch.randn(n, width, generator=g)
    reference = torch.sparse.mm(matrix.double(), dense.double())
    outcomes = []
    for device in ["cpu", "cuda"]:
        for layout in ["coo", "csr"]:
            sparse = matrix if layout == "coo" else matrix.to_sparse_csr()
            sparse, x = sparse.to(device), dense.to(device)
            outputs = set()
            first = None
            max_delta = 0.0
            captured = []
            try:
                with warnings.catch_warnings(record=True) as captured:
                    for _ in range(20):
                        result = torch.sparse.mm(sparse, x).cpu()
                        outputs.add(digest(result))
                        if first is None: first = result
                        max_delta = max(max_delta, (result-first).abs().max().item())
                rel = ((first.double()-reference).norm()/reference.norm()).item()
                outcomes.append(dict(device=device, layout=layout, status="computed", runs=20,
                                     distinct_outputs=len(outputs), maximum_repeat_delta=max_delta,
                                     relative_l2_vs_cpu_fp64=rel, warning_categories=sorted({w.category.__name__ for w in captured})))
            except RuntimeError as error:
                if "deterministic" not in str(error).lower(): raise
                outcomes.append(dict(device=device, layout=layout, status="determinism_rejected",
                                     error=str(error).splitlines()[0]))
    issue = any(o.get("distinct_outputs",1)>1 or o.get("relative_l2_vs_cpu_fp64",0)>0.0001 for o in outcomes)
    emit(status="candidate" if issue else "pass", deterministic_algorithms=True,
         requested_nnz=250000, coalesced_nnz=matrix._nnz(), shape=[n,n], dense_width=width, outcomes=outcomes)
    if issue: raise SystemExit(10)
elif a.mode == "dropout":
    def block(x): return F.dropout(x*1.0, p=0.3, training=True)
    def checked(x): return checkpoint(block, x, use_reentrant=False, preserve_rng_state=True)
    outcomes = []
    for device in ["cpu", "cuda"]:
        for backend in ["plain", "checkpoint", "aot_eager", "eager"]:
            fn = block if backend == "plain" else checked
            if backend in ["aot_eager", "eager"]:
                torch._dynamo.reset()
                fn = torch.compile(checked, backend=backend)
            for seed in [0,1,2]:
                torch.manual_seed(seed)
                x = (torch.rand(64,256)+0.5).to(device).requires_grad_()
                try:
                    y = fn(x)
                    y.sum().backward()
                except RuntimeError as error:
                    if "not supported" in str(error).lower() and "python" in str(error).lower():
                        outcomes.append(dict(device=device, backend=backend, seed=seed, status="unsupported_python"))
                        break
                    raise
                mismatch = ((y != 0) != (x.grad != 0)).float().mean().item()
                outcomes.append(dict(device=device, backend=backend, seed=seed, status="computed",
                                     forward_backward_mask_mismatch=mismatch))
    issue = any(o.get("forward_backward_mask_mismatch",0) != 0 for o in outcomes)
    emit(status="candidate" if issue else "pass", shape=[64,256], dropout_p=0.3,
         preserve_rng_state=True, outcomes=outcomes)
    if issue: raise SystemExit(10)
elif a.mode == "graphs":
    count = 4
    inputs = [torch.randn(512,device="cuda") for _ in range(count)]
    refs = [(x.sin()*2+1).cpu() for x in inputs]
    side = torch.cuda.Stream()
    side.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(side):
        for x in inputs:
            for _ in range(3): y=x.sin()*2+1
    torch.cuda.current_stream().wait_stream(side)
    torch.cuda.synchronize()
    graphs, static = [], []
    for x in inputs:
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph): y=x.sin()*2+1
        graphs.append(graph)
        static.append(y)
    outputs = []
    for i in range(200):
        slot=i%count
        graphs[slot].replay()
        outputs.append(static[slot].clone())
    if a.sync == "true": torch.cuda.synchronize()
    stacked = torch.stack(outputs).cpu()
    for i,y in enumerate(stacked):
        torch.testing.assert_close(y,refs[i%count],rtol=0,atol=0)
    for graph in graphs: graph.reset()
    del outputs,static,graphs,graph,y
    gc.collect()
    # Exercise allocator and execution after teardown; normal interpreter exit remains part of the test.
    z=torch.ones(4096,device="cuda")+1
    torch.cuda.synchronize()
    if not torch.equal(z.cpu(),torch.full((4096,),2.0)): raise RuntimeError("post-graph mismatch")
    emit(status="pass", graphs=count, replays=200, explicit_sync_before_stack=a.sync=="true")
