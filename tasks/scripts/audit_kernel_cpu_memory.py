#!/usr/bin/env python3
"""Static tensor-allocation floors for CPU kernel seeds; never import PyTorch.

This is a resource-planning audit, not a measured peak RSS or a readiness proof.
It retains every declared shape and does not execute candidate/evaluator code.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


POLICY = "arena.kernel-cpu.single-thread/1"
FAMILIES = {"kernel_cpu", "kernel_cpu_attention"}


def tensor(shape: tuple[int, ...], dtype: str = "float32") -> dict:
    return {"shape": list(shape), "dtype": dtype,
            "bytes": math.prod(shape) * {"float32": 4, "int64": 8}[dtype]}


def tensors(op: str, p: dict) -> tuple[list[dict], dict]:
    """Exact argument/output tensor shapes of the bundled seed generators."""
    extra = []
    if op == "attention":
        b, h, kv, n, d = (p[k] for k in ("batch", "heads_q", "heads_kv", "seq", "dim"))
        shapes, output = [(b, h, n, d), (b, kv, n, d), (b, kv, n, d)], (b, h, n, d)
    elif op == "decode_attention":
        b, h, d, n = (p[k] for k in ("batch", "heads", "dim", "kv_len"))
        shapes, output = [(b, h, 1, d), (b, h, n, d), (b, h, n, d)], (b, h, 1, d)
    elif op == "paged_attention":
        b, h, d, page, n = (p[k] for k in ("batch", "heads", "dim", "page", "kv_len"))
        shapes = [(b, h, d), (b * (n // page), page, h, d), (b * (n // page), page, h, d)]
        extra, output = [tensor((b, n // page), "int64"), tensor((b,), "int64")], (b, h, d)
    elif op in {"matmul", "gemm_split_k", "transpose_matmul", "gemm_bias_relu", "matmul_layer_norm", "lora", "swiglu"}:
        m, k, n = p["m"], p["k"], p["n"]
        shapes, output = [(k, m) if op == "transpose_matmul" else (m, k), (k, n)], (m, n)
        if op == "gemm_bias_relu": shapes += [(n,)]
        elif op == "matmul_layer_norm": shapes += [(n,), (n,)]
        elif op == "lora": shapes += [(k, p["r"]), (p["r"], n)]
        elif op == "swiglu": shapes += [(k, n)]
    elif op in {"bmm", "bmm_softmax"}:
        b, m, k, n = (p[key] for key in ("b", "m", "k", "n"))
        shapes, output = [(b, m, k), (b, k, n)], (b, m, n)
    elif op in {"vec_matmul", "persistent_vec_matmul"}:
        m, n, v = p["m"], p["n"], p.get("vectors", 1)
        shapes, output = [(m, n), (n, v)], (m, v)
    elif op in {"softmax", "relu", "silu", "swish", "layer_norm", "rmsnorm", "adamw"}:
        m, n = p["m"], p["n"]
        shapes, output = [(m, n)], (m, n)
        if op in {"layer_norm", "rmsnorm"}: shapes += [(n,), (n,)]
        elif op == "adamw": shapes, output = [(m, n)] * 4, (3, m, n)
    elif op in {"conv2d", "conv_bn_relu"}:
        b, ci, co, n = p.get("b", 8), p["cin"], p["cout"], p["hw"]
        shapes, output = [(b, ci, n, n), (co, ci, 3, 3)], (b, co, n, n)
        if op == "conv_bn_relu": shapes += [(co,)] * 4
    elif op in {"mlp_block", "transformer_block"}:
        t, d, f = p["tokens"], p["d"], p["ff"]
        shapes, output = [(t, d), (d, f), (f,), (f, d), (d,)], (t, d)
        if op == "transformer_block":
            shapes = [(1, t, d), (d, 3 * d), (d, d), (d,), (d,), *shapes[1:]]
            output = (1, t, d)
    elif op == "fused_moe":
        t, d, e, f = (p[k] for k in ("tokens", "d", "experts", "ff"))
        shapes, output = [(t, d), (d, e), (e, d, f), (e, f, d)], (t, d)
    elif op == "grouped_gemm_weight_gradient":
        t, k, n, g = (p[key] for key in ("tokens", "k", "n", "groups"))
        shapes, output = [(t, k), (t, n)], (g, k, n)
        extra = [tensor((g,), "int64")]
    elif op == "rope":
        b, h, n, d = p.get("b", 1), p["heads"], p["seq"], p["dim"]
        shapes, output = [(b, h, n, d), (n, d // 2), (n, d // 2)], (b, h, n, d)
    elif op == "mamba_scan":
        n, c, s = p["seq"], p["channels"], p["state"]
        shapes, output = [(n, c), (n, c), (c, s), (n, s), (n, s), (c,)], (n, c)
    elif op == "trimul":
        n, c, h = p["n"], p["c"], p["hidden"]
        shapes = [(1, n, n, c), (1, n, n), (c,), (c,), *([(c, h)] * 4), (h,), (h,), (c, c), (h, c)]
        output = (1, n, n, c)
    elif op in {"add_rmsnorm_matmul", "rmsnorm_matmul", "matmul_add_rmsnorm"}:
        m, k, n = p["m"], p["k"], p["n"]
        shapes, output = [(m, k), (k,), (k, n)], (m, n)
        if op == "add_rmsnorm_matmul": shapes.insert(1, (m, k))
        elif op == "matmul_add_rmsnorm": shapes = [(m, k), (k, n), (m, n), (n,)]
    else:
        raise ValueError(f"Unreviewed operator: {op}")
    return [tensor(shape) for shape in shapes] + extra, tensor(output)


def operator_audit(entry: dict) -> dict:
    inputs, output = tensors(entry["op"], entry["params"])
    resident = sum(item["bytes"] for item in inputs)
    # _check holds ref and out while (out - ref).abs() makes two full tensors.
    correctness = resident + 4 * output["bytes"]
    # _randn constructs a fresh tensor and its scaled result simultaneously.
    prior, generation = 0, resident
    for item in inputs:
        generation = max(generation, prior + item["bytes"] * (2 if item["dtype"] == "float32" else 1))
        prior += item["bytes"]
    result = {**entry, "inputs": inputs, "output": output, "resident_input_bytes": resident,
              "input_generation_floor_bytes": generation, "correctness_floor_bytes": correctness,
              "allocation_floor_bytes": max(generation, correctness)}
    if entry["op"] == "attention":
        p = entry["params"]
        result["dense_attention_weights_bytes"] = 4 * p["batch"] * p["heads_q"] * p["seq"] ** 2
    return result


def audit(root: Path) -> dict:
    rows = []
    for path in sorted((root / "suite").glob("*/problem.json")):
        problem = json.loads(path.read_text())
        if problem.get("family") not in FAMILIES: continue
        evaluator = (path.parent / "evaluator.py").read_bytes()
        tree = ast.parse(evaluator)
        parameters = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "P" for target in node.targets))
        if parameters != problem["parameters"]: raise ValueError(f"Evaluator parameters differ: {path.parent.name}")
        call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == "kernel_score")
        metric = next(ast.literal_eval(item.value) for item in call.keywords if item.arg == "score")
        operators = [operator_audit(entry) for entry in parameters["ops"]]
        floor = max(entry["allocation_floor_bytes"] for entry in operators)
        rows.append({"task_id": path.parent.name, "family": problem["family"], "protocol": problem["protocol"],
                     "timing_protocol": POLICY, "metric": metric, "seed": parameters.get("seed", 0),
                     "repeats": parameters.get("repeats", 3), "timeout_seconds": problem["timeout"],
                     "evaluator_sha256": hashlib.sha256(evaluator).hexdigest(),
                     "seed_sha256": hashlib.sha256((path.parent / "initial_program.py").read_bytes()).hexdigest(),
                     "allocation_floor_bytes": floor, "exceeds_2gib": floor >= 2 * 1024 ** 3,
                     "readiness": "requires_measured_seed_preflight", "operators": operators})
    return {"schema": "arena.kernel-cpu-resource-audit/1", "task_count": len(rows),
            "timing_protocol": POLICY, "analysis": "static_allocation_lower_bounds_only", "model_calls": 0,
            "metrics": dict(Counter(row["metric"] for row in rows)),
            "exceed_2gib_count": sum(row["exceeds_2gib"] for row in rows),
            "limitations": ["Not measured peak RSS: excludes Python/PyTorch, allocator retention, library workspaces and other temporaries.",
                            "Operator-loop liveness can retain earlier tensors; the maximum is a lower bound, not a safe memory limit.",
                            "Dense attention weights are a shape-derived warning, not a claim that the fused reference materializes them.",
                            "No task shapes, score formulas, tolerances, seeds, repeats or evaluator timeouts were reduced.",
                            "A task below 2 GiB here is not proven to fit 2 GiB or its timeout; every seed still needs measured preflight."],
            "tasks": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = audit(args.root)
    raw = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if args.output: args.output.write_text(raw)
    else: print(raw, end="")


if __name__ == "__main__":
    main()
