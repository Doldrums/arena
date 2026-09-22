"""Static memory bounds are not readiness claims; all original shapes remain."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kernel_memory_audit", ROOT / "scripts/audit_kernel_cpu_memory.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
REPORT = json.loads((ROOT / "validation/kernel-cpu-resource-audit.json").read_text())
ROWS = {row["task_id"]: row for row in REPORT["tasks"]}
GIB = 1024 ** 3


def test_static_audit_is_current_and_does_not_claim_executed_readiness():
    assert audit_module.audit(ROOT) == REPORT
    assert REPORT["task_count"] == 51
    assert REPORT["metrics"] == {"speedup": 27, "tflops": 24}
    assert REPORT["exceed_2gib_count"] == 19
    assert REPORT["model_calls"] == 0
    assert all(row["readiness"] == "requires_measured_seed_preflight" for row in ROWS.values())


def test_decode_input_generation_and_bmm_correctness_exceed_two_gib():
    decode = ROWS["agentic-optimization-decode-attention-kernel-optimization"]["operators"][0]
    assert decode["resident_input_bytes"] == 2 * GIB + 512 * 1024
    assert decode["input_generation_floor_bytes"] == 3 * GIB + 512 * 1024
    for ident in ("accelopt-bmm-b16-m4096-k64-n4096-0", "accelopt-bmm-softmax-b16-k64-m4096-n4096-0"):
        row = ROWS[ident]["operators"][0]
        assert row["output"]["bytes"] == GIB
        assert row["correctness_floor_bytes"] == 4 * GIB + 32 * 1024 ** 2


def test_avo_batch_varies_with_sequence_to_preserve_exact_total_token_count():
    batches = set()
    for ident, row in ROWS.items():
        if not ident.startswith("avo-"): continue
        op = row["operators"][0]
        p = op["params"]
        assert p["batch"] * p["seq"] == 32768
        batches.add(p["batch"])
        expected = 1.75 if p["heads_q"] == 16 else 2.625 if p["heads_kv"] == 4 else 2.75
        assert row["allocation_floor_bytes"] == expected * GIB
    assert batches == {1, 2, 4, 8}


def test_all_51_metadata_records_disclose_the_timing_revision():
    catalog = {row["id"]: row for row in json.loads((ROOT / "catalog/tasks.json").read_text())}
    index = {row["id"]: row for row in json.loads((ROOT / "suite/index.json").read_text())["tasks"]}
    for ident, row in ROWS.items():
        directory = ROOT / "suite" / ident
        task = json.loads((directory / "task.json").read_text())
        problem = json.loads((directory / "problem.json").read_text())
        policy = problem["timing_protocol"]
        assert task == catalog[ident]
        assert policy == task["execution"]["suite"]["timing_protocol"] == index[ident]["timing_protocol"]
        assert policy["id"] == REPORT["timing_protocol"]
        assert policy["intra_op_threads"] == policy["inter_op_threads"] == 1
        assert policy["historical_timings_comparable"] is False
        assert policy["validation_status"] == "requires_seed_preflight"
        assert task["execution"]["suite"]["protocol"] == problem["protocol"] == "recreated"
        assert set(task["execution"]["suite"]["env"].values()) == {"1"}
        assert REPORT["timing_protocol"] in (directory / "README.txt").read_text()
        assert any("Historical host-wide-thread timings" in note for note in problem["notes"])
        assert row["seed_sha256"] == hashlib.sha256((directory / "initial_program.py").read_bytes()).hexdigest()
        assert row["evaluator_sha256"] == hashlib.sha256((directory / "evaluator.py").read_bytes()).hexdigest()


def test_static_input_shapes_match_all_real_generators_without_tensor_allocation():
    torch = pytest.importorskip("torch")
    sys.path.insert(0, str(ROOT / "suite/_lib"))
    from autoresearch_suite import kernel_cpu
    # Meta tensors execute shape propagation, not the large numerical kernels.
    for row in ROWS.values():
        for op in row["operators"]:
            with torch.device("meta"):
                inputs = kernel_cpu.OPS[op["op"]][0](row["seed"], op["params"])
            actual = [value for value in inputs if isinstance(value, torch.Tensor)]
            assert [list(value.shape) for value in actual] == [item["shape"] for item in op["inputs"]]
            assert [str(value.dtype).removeprefix("torch.") for value in actual] == [item["dtype"] for item in op["inputs"]]
