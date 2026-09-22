"""Protocol checks use inert thread-pool doubles and optional tiny CPU tensors."""
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "suite/_lib"))
from autoresearch_suite import kernel_threads
from autoresearch_suite.runtime import CandidateError


class Pool:
    def __init__(self, intra=128, inter=128, *, inter_started=False):
        self.intra, self.inter = intra, inter
        self.inter_started = inter_started
        self.calls = []

    def get_num_threads(self): return self.intra
    def get_num_interop_threads(self): return self.inter

    def set_num_threads(self, value):
        self.calls.append(("intra", value))
        self.intra = value

    def set_num_interop_threads(self, value):
        if self.inter_started: raise RuntimeError("The pool was already started")
        self.calls.append(("inter", value))
        self.inter = value
        self.inter_started = True


def test_host_wide_or_environment_thread_counts_cannot_expand_canonical_allocation(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "256")
    monkeypatch.setenv("MKL_NUM_THREADS", "64")
    pool = Pool()
    assert kernel_threads.configure(pool) is pool
    assert kernel_threads.details(pool) == {
        "thread_policy": "arena.kernel-cpu.single-thread/1", "threads": 1, "interop_threads": 1}


def test_repeated_configuration_does_not_repeat_torch_one_shot_interop_setter():
    pool = Pool()
    kernel_threads.configure(pool)
    kernel_threads.configure(pool)
    assert pool.calls == [("intra", 1), ("inter", 1)]
    already_configured = Pool(1, 1, inter_started=True)
    kernel_threads.configure(already_configured)
    assert already_configured.calls == []


def test_unreconfigurable_pool_is_an_explicit_evaluator_error():
    pool = Pool(inter_started=True)
    with pytest.raises(CandidateError, match="Cannot establish.*fresh process"):
        kernel_threads.configure(pool)
    with pytest.raises(CandidateError, match="requires one"):
        kernel_threads.details(pool)


def test_failed_or_changed_thread_setting_cannot_claim_the_policy():
    pool = Pool()
    pool.set_num_threads = lambda value: None
    with pytest.raises(CandidateError, match="requires one"):
        kernel_threads.configure(pool)
    pool = Pool(1, 1)
    pool.intra = 2
    with pytest.raises(CandidateError, match="requires one"):
        kernel_threads.require_policy(pool)


@pytest.mark.parametrize("metric", ["speedup", "tflops"])
def test_tiny_cpu_fixture_preserves_correctness_and_score_formula(monkeypatch, metric):
    torch = pytest.importorskip("torch")
    from autoresearch_suite import kernel_cpu
    kernel_cpu._torch()  # Initialize pools before deterministic timing probes.
    kernel_cpu._torch()
    clock = iter([0, 2, 10, 11, 20, 20.5, 30, 30.25])
    monkeypatch.setattr(kernel_cpu, "time", SimpleNamespace(perf_counter=lambda: next(clock)))
    candidate = SimpleNamespace(mm=lambda a, b: a @ b)
    # A unit fixture, not a reduced version of any admitted task.
    ops = [{"name": "mm", "op": "matmul", "params": {"m": 4, "k": 3, "n": 8}}]
    value, details = kernel_cpu.kernel_score(candidate, ops, repeats=2, score=metric)
    expected = 4.0 if metric == "speedup" else 2 * 4 * 3 * 8 / 0.25 / 1e12
    assert math.isclose(value, expected)
    assert details["metric"] == metric and details["kernels"][0]["max_abs_error"] == 0
    assert details["thread_policy"] == kernel_threads.POLICY
    assert details["threads"] == details["interop_threads"] == 1
    assert details["kernels"][0]["reference_seconds"] == 1
    assert details["kernels"][0]["candidate_seconds"] == 0.25


def test_incorrect_candidate_still_fails_correctness():
    torch = pytest.importorskip("torch")
    from autoresearch_suite import kernel_cpu
    candidate = SimpleNamespace(mm=lambda a, b: torch.zeros((4, 8)))
    with pytest.raises(CandidateError, match="exceeds tolerance"):
        kernel_cpu.kernel_score(candidate, [{"name": "mm", "op": "matmul", "params": {"m": 4, "k": 3, "n": 8}}])


@pytest.mark.parametrize("change_on_call", [1, 2])
def test_warmup_or_timed_call_cannot_silently_change_thread_policy(monkeypatch, change_on_call):
    pytest.importorskip("torch")
    from autoresearch_suite import kernel_cpu
    pool, calls = Pool(1, 1), []
    monkeypatch.setattr(kernel_cpu, "torch", pool)
    def candidate():
        calls.append(None)
        if len(calls) == change_on_call: pool.intra = 8
    with pytest.raises(CandidateError, match="requires one"):
        kernel_cpu._time(candidate, 2)
