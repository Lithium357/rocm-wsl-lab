"""WSL runner: gate GPU ownership, monitor kernel errors, stop on first failure."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

PATTERN = re.compile(r"wait_for_completion failed|failed to destroy allocations|create_existing_sysmem:.*failed|dxgkio_create_allocation:.*failed|GPU reset|GPU fault|I/O error|field-spanning write|kernel panic", re.I)

def kernel():
    r = subprocess.run(["dmesg", "--color=never"], capture_output=True, text=True)
    if r.returncode: raise RuntimeError("Cannot read kernel log; no GPU tests allowed")
    return r.stdout.splitlines()

def owners():
    result = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit(): continue
        try:
            for fd in (proc/"fd").iterdir():
                try:
                    target = os.readlink(fd)
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue
                if target == "/dev/dxg":
                    result.append({"pid": int(proc.name), "comm": (proc/"comm").read_text().strip()})
                    break
        except (FileNotFoundError, PermissionError, ProcessLookupError): pass
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--focus", choices=["initial", "followup", "cleanup", "unresolved", "minimal_control", "minimal_changed", "concurrency", "sparse", "dropout", "graphs", "hip_device", "hip_host", "hip_pool"], default="initial")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    events = out/"events.jsonl"
    def log(**kw):
        kw["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with events.open("a") as f: f.write(json.dumps(kw)+"\n")
        print(json.dumps(kw), flush=True)
    old = kernel()
    bad = [s for s in old if PATTERN.search(s)]
    if bad:
        log(status="blocked", reason="existing kernel instability", errors=bad[-8:])
        return 2
    active = owners()
    if active:
        log(status="blocked", reason="GPU already owned", owners=active)
        return 2
    tests = [["smoke"], ["smoke"], ["idle"], ["idle"]]
    for dtype in ["float32", "bfloat16"]:
        for dim in [256, 320, 384, 512]:
            for backend in ["math", "default", "efficient"]:
                tests.append(["attention", "--dim", str(dim), "--dtype", dtype, "--backend", backend])
    tests += [["copies"], ["copies"]]
    if args.focus == "followup":
        tests = [["idle"], ["training", "--dtype", "float32"], ["training", "--dtype", "bfloat16"]]
        for dim in [256, 384, 512]:
            for backend in ["math", "default"]:
                tests.append(["attention", "--length", "1024", "--dim", str(dim), "--dtype", "bfloat16", "--backend", backend])
    if args.focus == "cleanup":
        tests = [["idle", "--release"]]
    if args.focus == "unresolved":
        tests = [["allocator", "false"], ["allocator", "true"],
                 ["threaded_copies", "--threads", "1"], ["threaded_copies", "--threads", "2"],
                 ["stream_order", "--streams", "1"], ["stream_order", "--streams", "8"]]
    if args.focus == "minimal_control":
        tests = [["minimal_allocator", "false"]]
    if args.focus == "minimal_changed":
        tests = [["minimal_allocator", "true"]]
    if args.focus == "concurrency":
        tests = [["threaded_copies", "--threads", "1"], ["threaded_copies", "--threads", "2"],
                 ["stream_order", "--streams", "1"], ["stream_order", "--streams", "8"]]
    if args.focus in ["sparse", "dropout"]:
        tests = [[args.focus]]
    if args.focus == "graphs":
        tests = [["graphs", "--sync", "false"], ["graphs", "--sync", "true"]]
    if args.focus in ["hip_device", "hip_host"]:
        tests = [["public_hip_vmm", "host" if args.focus == "hip_host" else "device"]]
    if args.focus == "hip_pool":
        tests = [["public_hip_pool", "classic"], ["public_hip_pool", "async"]]
    for n, test in enumerate(tests):
        if owners():
            log(status="blocked", reason="GPU ownership changed", test=test)
            return 2
        previous = kernel()
        stop_messages = [line for line in previous if PATTERN.search(line)]
        if stop_messages:
            log(status="blocked", reason="kernel stop condition appeared between cases", errors=stop_messages[-8:])
            return 2
        stdout = out/f"{n:02d}.stdout.txt"
        stderr = out/f"{n:02d}.stderr.txt"
        unresolved = args.focus in ["unresolved", "minimal_control", "minimal_changed", "concurrency"]
        script = "rocm_unresolved_probe.py" if unresolved else "rocm_probe.py"
        if args.focus in ["sparse", "dropout", "graphs"]:
            script = "rocm_correctness_probe.py"
        environment = os.environ.copy()
        child_args = list(test)
        if unresolved or args.focus in ["sparse", "dropout", "graphs"]:
            for key in ["PYTORCH_CUDA_ALLOC_CONF", "PYTORCH_HIP_ALLOC_CONF", "PYTORCH_ALLOC_CONF"]:
                environment.pop(key, None)
            if test[0] in ["allocator", "minimal_allocator"]:
                environment["PYTORCH_ALLOC_CONF"] = "expandable_segments:"+test[1].title()
                child_args = [test[0]]
        cmd = [sys.executable, str(Path(__file__).with_name(script)), *child_args]
        if args.focus in ["hip_device", "hip_host"]:
            cmd = [str(Path(__file__).parent.parent/"work/hip-vmm-build/hip_vmm_access_probe"), test[1]]
        if args.focus == "hip_pool":
            cmd = [str(Path(__file__).parent.parent/"work/hip-vmm-build/hip_pool_lifecycle_probe"), test[1]]
        log(status="started", index=n, test=test)
        start = time.monotonic()
        reason = None
        delta = []
        foreign_owners = []
        with stdout.open("w") as so, stderr.open("w") as se:
            child = subprocess.Popen(cmd, stdout=so, stderr=se, env=environment)
            while child.poll() is None:
                foreign_owners = [owner for owner in owners() if owner["pid"] != child.pid]
                if foreign_owners:
                    reason = "another GPU owner appeared during the probe"
                current = kernel()
                if len(current) < len(previous) or current[:len(previous)] != previous:
                    reason = "kernel log changed or wrapped; evidence continuity lost"
                else:
                    delta = [s for s in current[len(previous):] if PATTERN.search(s)]
                    if delta: reason = "new kernel instability"
                if time.monotonic()-start > 60: reason = "60 second timeout"
                if reason:
                    child.terminate()
                    try: child.wait(3)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        try: child.wait(3)
                        except subprocess.TimeoutExpired: pass
                    break
                time.sleep(0.25)
        current = kernel()
        if current[:len(previous)] != previous:
            reason = reason or "kernel log continuity lost"
        else:
            delta = [s for s in current[len(previous):] if PATTERN.search(s)]
            if delta: reason = reason or "new kernel instability"
        log(status="stopped" if reason else "completed", index=n, test=test,
            returncode=child.poll(), wall_s=time.monotonic()-start, reason=reason, kernel_errors=delta,
            foreign_gpu_owners=foreign_owners)
        if reason or child.returncode != 0: return 1
    log(status="suite_complete", tests=len(tests))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
