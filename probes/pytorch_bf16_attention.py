"""Synthetic single-step attention probe; no model, data, or private prompts.

Run in fresh subprocesses. Change only TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL
between control and affected commands. Keep raw artifacts outside source control.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)


def kernel_log():
    result = subprocess.run(["dmesg", "--time-format", "raw"], capture_output=True, text=True)
    return result.returncode, result.stdout.splitlines(), result.stderr


before_status, before, before_error = kernel_log()
(args.output / "kernel-before.txt").write_text("\n".join(before) + "\n")
started = time.perf_counter()
result = {"started_utc": datetime.now(timezone.utc).isoformat(), "seed": 357,
          "shape": [2, 8, 128, 64], "dtype": "bfloat16", "causal": True, "dropout": 0.0,
          "experimental_flag": os.environ.get("TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL"),
          "kernel_release": platform.release(), "python_version": platform.python_version(),
          "kernel_log_readable": before_status == 0}
try:
    import torch
    from torch.nn import functional as F
    result.update(torch_version=torch.__version__, hip_version=torch.version.hip,
                  gpu_name=torch.cuda.get_device_name(0), total_vram_bytes=torch.cuda.get_device_properties(0).total_memory)
    cpu_generator = torch.Generator().manual_seed(357)
    tensors = [torch.randn((2, 8, 128, 64), generator=cpu_generator).to(torch.bfloat16) for _ in range(3)]
    result["input_sha256"] = [hashlib.sha256(t.view(torch.uint8).numpy().tobytes()).hexdigest() for t in tensors]
    q, k, v = [t.to("cuda").requires_grad_() for t in tensors]
    params = torch.backends.cuda.SDPAParams(q, k, v, None, 0.0, True, False)
    result["flash_eligible"] = torch.backends.cuda.can_use_flash_attention(params, debug=True)
    result["efficient_eligible"] = torch.backends.cuda.can_use_efficient_attention(params, debug=True)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    step_start = time.perf_counter()
    # Same default SDPA call in both runs; the environment flag is the only changed variable.
    output = F.scaled_dot_product_attention(q, k, v, dropout_p=0.0, is_causal=True)
    loss = output.float().square().mean()
    loss.backward()
    torch.cuda.synchronize()
    result["step_seconds"] = time.perf_counter() - step_start
    result["loss"] = float(loss.detach())
    result["finite_output_and_gradients"] = bool(torch.isfinite(output).all() and all(torch.isfinite(t.grad).all() for t in (q, k, v)))
    result["gradient_norms"] = [float(t.grad.float().norm()) for t in (q, k, v)]
    result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
    torch.save({"output": output.detach().cpu(), "gradients": [t.grad.detach().cpu() for t in (q, k, v)]}, args.output / "synthetic-tensors.pt")
    result["status"] = "completed" if result["finite_output_and_gradients"] else "nonfinite"
except BaseException as error:
    result["status"] = "failed"
    result["error_type"] = type(error).__name__
    result["error"] = str(error)
finally:
    after_status, after, after_error = kernel_log()
    (args.output / "kernel-after.txt").write_text("\n".join(after) + "\n")
    delta = [line for line in after if line not in set(before)] if before_status == after_status == 0 else []
    (args.output / "kernel-delta.txt").write_text("\n".join(delta) + "\n")
    danger = [line for line in delta if any(term in line.lower() for term in ("sync object", "sync_object", "gpu reset", "field spanning", "field-spanning", "ioctl failed", "i/o error"))]
    result["new_kernel_lines"] = len(delta)
    result["stop_condition_kernel_lines"] = len(danger)
    result["kernel_log_readable"] = before_status == after_status == 0
    result["wall_seconds"] = time.perf_counter() - started
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))
