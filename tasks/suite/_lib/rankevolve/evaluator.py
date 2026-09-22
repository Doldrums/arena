"""Run a candidate subprocess, then independently validate and grade its rankings.

The child receives public corpus/query paths only. The parent imports no
candidate code and parses qrels only after the child exits. Both share a UID
and container: this is not an adversarial file-secrecy or anti-tamper guarantee.
"""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from .contract import decode, digest, records, verified_bundle
from .ranking import grade_rankings


def evaluate(program_path, task_dir):
    here = Path(task_dir)
    lock = decode((here / "dataset-lock.json").read_bytes())
    dataset = lock["dataset"]
    started = time.monotonic()
    base, manifest = verified_bundle(dataset, lock.get("manifest_sha256"))
    # Input identity is verified before execution. Qrels are not loaded into
    # parent memory until the candidate child has terminated.
    with tempfile.TemporaryDirectory(prefix="arena-rankevolve-") as temporary:
        work = Path(temporary)
        output = work / "rankings.jsonl"
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work), "TMPDIR": str(work),
               "PYTHONPATH": str(here.parent / "_lib"), "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPYCACHEPREFIX": str(work / "pycache"), "BM25_QUERY_WORKERS": "1",
               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        command = [sys.executable, "-m", "rankevolve.candidate", "--candidate", str(Path(program_path).resolve()),
                   "--data", str(base / "public"), "--output", str(output),
                   "--documents", str(manifest["documents"]), "--queries", str(manifest["queries"])]
        process = subprocess.Popen(command, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            process.wait(timeout=lock["candidate_timeout_seconds"])
        finally:
            # Clean the child's process group even if it exited with descendants.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        if process.returncode != 0:
            raise ValueError("Candidate subprocess failed or returned an invalid ranking")
        if output.is_symlink() or output.stat().st_size > manifest["queries"] * 32768:
            raise ValueError("Ranking output exceeds its bounded artifact contract")
        output_sha = digest(output)
        # Revalidate read-only prepared inputs before trusting the independent
        # grader's view; no candidate-supplied metric or dataset ID is accepted.
        verified_bundle(dataset, lock["manifest_sha256"])
        corpus_ids = [row["id"] for row in records(base / "public/corpus.jsonl")]
        query_ids = [row["id"] for row in records(base / "public/queries.jsonl")]
        qrels = {}
        for row in records(base / "private/qrels.jsonl"):
            if (set(row) != {"id", "relevance"} or row["id"] in qrels
                    or type(row["relevance"]) is not dict
                    or any(type(value) is not int for value in row["relevance"].values())):
                raise ValueError("Invalid prepared relevance judgments")
            qrels[row["id"]] = row["relevance"]
        metrics = grade_rankings(records(output), corpus_ids, query_ids, qrels)
        if digest(output) != output_sha:
            raise ValueError("Candidate rankings changed while being graded")
    return {**metrics, "combined_score": metrics["score"], "direction": "maximize", "valid": True,
            "dataset": dataset, "documents": manifest["documents"], "tokenizer_api": manifest["tokenizer"],
            "data_manifest_sha256": lock["manifest_sha256"], "rankings_sha256": output_sha,
            "search_protocol": "exploratory_search_on_test", "metric_semantics": "positive-qrel binary nDCG; not graded BEIR nDCG",
            "candidate_boundary": "separate_process_same_uid_and_container; no adversarial secrecy guarantee",
            "wall_seconds": time.monotonic() - started}
