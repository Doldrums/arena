"""Source-derived LMX SD1.4 prompt evaluation; no published-baseline claim.

The RGB objective follows jal278/lmx b8fec5dd, scripts/stablediffusion.py.
See tasks/licenses/LMX-LICENSE. Candidate Python runs only in a bounded child.
Process separation protects grader imports; a same-UID container is not an
adversarial secrecy boundary. Production GPU admission is a separate policy.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from . import runtime
from .lmx_sd_assets import (CUDA_ALLOCATOR_LIMIT_BYTES, GENERATION, MAXIMUM_SCORE,
                            PROTOCOL, verify_assets, verify_runtime)


def candidate_prompt(program_path, *, timeout=5):
    if sys.platform != "linux":
        raise RuntimeError("LMX bounded candidate execution requires Linux resource limits")
    path = Path(program_path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Candidate must be a regular Python file of at most 1 MiB")
    helper = Path(__file__).with_name("lmx_sd_candidate.py")
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": "/tmp",
                   "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": ""}
    process = subprocess.Popen([sys.executable, "-I", "-u", str(helper), str(path)],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env=environment, cwd="/tmp", start_new_session=True)
    content = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError("Prompt candidate exceeded its 5-second deadline")
                block = os.read(process.stdout.fileno(), 4096)
                if not block:
                    break
                content.extend(block)
                if len(content) > 32768:
                    raise ValueError("Prompt candidate exceeded the output limit")
        code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        if not content:
            raise ValueError("Prompt candidate exited without a result")
        value = json.loads(content)
        if (code or type(value) is not dict or set(value) != {"prompt"} or type(value["prompt"]) is not str
                or len(value["prompt"].encode("utf-8")) > 4096):
            raise ValueError("candidate() must return only a bounded prompt string")
        return value["prompt"]
    finally:
        # A departed group leader can leave descendants; clean the whole group.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        process.stdout.close()


def excess_color(image, channel):
    """Original float32 RGB sum objective, evaluated on the complete image."""
    import numpy as np

    if channel not in {"r", "g", "b"}:
        raise ValueError("Unknown color objective")
    raw = np.asarray(image)
    if raw.shape != (512, 512, 3) or raw.dtype != np.uint8:
        raise ValueError("Pipeline must produce one complete 512x512 RGB uint8 image")
    img = np.asarray(image, dtype=np.float32)
    if channel == "r":
        score = np.sum(img[:, :, 0]) - 0.5 * np.sum(img[:, :, 1]) - 0.5 * np.sum(img[:, :, 2])
    elif channel == "g":
        score = np.sum(img[:, :, 1]) - 0.5 * np.sum(img[:, :, 0]) - 0.5 * np.sum(img[:, :, 2])
    else:
        score = np.sum(img[:, :, 2]) - 0.5 * np.sum(img[:, :, 0]) - 0.5 * np.sum(img[:, :, 1])
    return float(score), hashlib.sha256(raw.tobytes()).hexdigest()


def load_pipeline(root):
    verify_runtime()
    import torch
    from diffusers import StableDiffusionPipeline
    from diffusers.models.attention_processor import AttnProcessor

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("LMX requires exactly one explicitly assigned CUDA device")
    total = torch.cuda.get_device_properties(0).total_memory
    if total < CUDA_ALLOCATOR_LIMIT_BYTES:
        raise ValueError("The prepared LMX protocol requires at least 8 GiB GPU memory")
    torch.cuda.set_per_process_memory_fraction(CUDA_ALLOCATOR_LIMIT_BYTES / total, 0)
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    pipe = StableDiffusionPipeline.from_pretrained(
        str(root), torch_dtype=torch.float16, local_files_only=True,
        use_safetensors=False, low_cpu_mem_usage=False,
    )
    if pipe.safety_checker is None or pipe.scheduler.__class__.__name__ != "PNDMScheduler":
        raise ValueError("Pinned safety checker and PNDM scheduler must remain enabled")
    # Freeze legacy attention rather than inheriting version-dependent SDPA selection.
    pipe.unet.set_attn_processor(AttnProcessor())
    pipe.vae.set_attn_processor(AttnProcessor())
    pipe.set_progress_bar_config(disable=True)
    return pipe.to("cuda")


def evaluate(program_path, channel):
    started = time.monotonic()
    try:
        prompt = candidate_prompt(program_path)
        # Verify assets and initialize all grading/model state after candidate exit.
        root, assets = verify_assets()
        pipe = load_pipeline(root)
        import torch

        torch.cuda.reset_peak_memory_stats()
        torch.manual_seed(99)
        torch.cuda.synchronize()
        with torch.inference_mode():
            generated = pipe(prompt, **GENERATION)
        torch.cuda.synchronize()
        if len(generated.images) != 1:
            raise ValueError("Expected exactly one full image")
        score, image_hash = excess_color(generated.images[0], channel)
        blocked = generated.nsfw_content_detected
        if not isinstance(blocked, list) or len(blocked) != 1:
            raise ValueError("Safety checker evidence is missing")
        return runtime.success(
            score, "maximize", protocol=PROTOCOL, channel=channel,
            normalized_excess=score / MAXIMUM_SCORE, normalization_role="display_only",
            image_sha256=image_hash, safety_checker_enabled=True,
            nsfw_content_detected=bool(blocked[0]), assets=assets,
            generation={**GENERATION, "seed": 99, "dtype": "float16",
                        "attention_processor": "AttnProcessor", "tf32": False},
            device={"name": torch.cuda.get_device_name(0),
                    "uuid": str(torch.cuda.get_device_properties(0).uuid),
                    "reported_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
                    "torch_allocator_limit_bytes": CUDA_ALLOCATOR_LIMIT_BYTES,
                    "memory_limit_scope": "PyTorch allocator; driver/context allocations are outside this limit",
                    "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                    "peak_reserved_bytes": torch.cuda.max_memory_reserved()},
            runtime_packages=verify_runtime(),
            model_usage={"diffusion_images": 1, "llm_calls": 0, "external_api_calls": 0},
            initialization="Arena neutral prompt; not the paper's initial population",
            paper_reproduction=False, elapsed_seconds=time.monotonic() - started,
        )
    except Exception as exc:
        return runtime.failure(f"{type(exc).__name__}: {exc}", "maximize", protocol=PROTOCOL,
                               elapsed_seconds=time.monotonic() - started)
