"""Finite, independently checked algorithm tasks from the expansion roadmap.

Inputs are native generated mathematical instances, not purported paper data.
Public development seeds are reproducible; they are not concealed test cases.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from .runtime import CandidateError, require


def integer(x, upper, name="wire"):
    require(isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_)), f"{name} must be an integer")
    require(0 <= int(x) < upper, f"{name} out of range")
    return int(x)


def check_xor(matrix, circuit, depth_limit=16):
    a = np.asarray(matrix)
    require(a.ndim == 2 and np.all((a == 0) | (a == 1)), "matrix must be binary")
    n = a.shape[1]
    require(isinstance(circuit, dict), "return gates and outputs in a dictionary")
    gates, outputs = circuit.get("gates"), circuit.get("outputs")
    require(isinstance(gates, (list, tuple)) and len(gates) <= 4096, "invalid/oversized gate list")
    require(isinstance(outputs, (list, tuple)) and len(outputs) == len(a), "one output wire required per matrix row")
    # Input i represents basis vector 1<<i. Wire n is the fixed zero constant.
    symbolic, depth = [1 << i for i in range(n)] + [0], [0] * (n + 1)
    for pair in gates:
        require(isinstance(pair, (list, tuple)) and len(pair) == 2, "each gate takes two wires")
        u, v = [integer(x, len(symbolic)) for x in pair]
        symbolic.append(symbolic[u] ^ symbolic[v])
        depth.append(1 + max(depth[u], depth[v]))
    require(max(depth) <= depth_limit, "circuit exceeds depth limit")
    for row, output in zip(a, outputs):
        idx = integer(output, len(symbolic))
        expected = sum(int(x) << i for i, x in enumerate(row))
        require(symbolic[idx] == expected, "circuit does not implement the specified linear map")
    return len(gates), {"depth": max(depth), "verified": "exact_symbolic_GF2"}


def xor_cases(seed=731):
    rng = np.random.default_rng(seed)
    return [rng.integers(0, 2, (m, n), dtype=np.int8) for m, n in [(8, 8), (12, 16), (16, 16)]]


def xor_score(synthesize):
    rows = []
    for a in xor_cases():
        count, details = check_xor(a, synthesize(a.copy(), 16), 16)
        reference = int(np.maximum(a.sum(axis=1) - 1, 0).sum())
        rows.append({"gates": count, "naive_gates": reference, **details})
    return float(np.mean([r["gates"] / r["naive_gates"] for r in rows])), {"instances": rows}


def xor_baseline(matrix, depth_limit=16):
    """Balanced independent row trees. Candidate may discover cross-row reuse."""
    n = matrix.shape[1]
    gates, outputs = [], []
    for row in matrix:
        wires = list(map(int, np.flatnonzero(row)))
        if not wires:
            outputs.append(n)
            continue
        while len(wires) > 1:
            nxt = []
            for j in range(0, len(wires), 2):
                if j + 1 == len(wires):
                    nxt.append(wires[j])
                else:
                    gates.append([wires[j], wires[j + 1]])
                    nxt.append(n + len(gates))
            wires = nxt
        outputs.append(wires[0])
    return {"gates": gates, "outputs": outputs}


def prism_graph(m):
    edges = []
    for layer in (0, 1):
        edges.extend((layer * m + i, layer * m + (i + 1) % m) for i in range(m))
    edges.extend((i, i + m) for i in range(m))
    return {"n": 2 * m, "edges": edges}


def check_lift(graph, signs):
    n, edges = graph["n"], graph["edges"]
    a = np.asarray(signs)
    require(a.shape == (len(edges),) and np.all((a == -1) | (a == 1)), "one sign -1/+1 is required per edge")
    signed = np.zeros((n, n))
    adjacency = [set() for _ in range(2 * n)]
    for (u, v), sign in zip(edges, a):
        signed[u, v] = signed[v, u] = int(sign)
        swap = int(sign == -1)
        for side in (0, 1):
            x, y = 2 * u + side, 2 * v + (side ^ swap)
            adjacency[x].add(y)
            adjacency[y].add(x)
    require(all(len(row) == 3 for row in adjacency), "lift must remain 3-regular")
    visited, todo = {0}, [0]
    while todo:
        fresh = adjacency[todo.pop()] - visited
        visited.update(fresh)
        todo.extend(fresh)
    require(len(visited) == 2 * n, "lift is disconnected")
    values = np.linalg.eigvalsh(signed)
    return float(np.max(np.abs(values))), {"vertices": 2 * n, "new_eigenvalues": values.tolist()}


def lift_baseline(graph, budget):
    rng = np.random.default_rng(3)
    best, best_score = None, float("inf")
    for _ in range(budget):
        signs = rng.choice([-1, 1], len(graph["edges"]))
        try:
            score, _ = check_lift(graph, signs)
        except CandidateError:
            continue
        if score < best_score:
            best, best_score = signs, score
    require(best is not None, "no connected lift found")
    return best


def lift_score(sign_edges):
    records = []
    for m in (4, 5, 7, 9):
        g = prism_graph(m)
        score, details = check_lift(g, sign_edges(copy.deepcopy(g), 32))
        records.append({"spectral_radius": score, **details})
    return float(np.mean([r["spectral_radius"] for r in records])), {"instances": records}


def layered_dag(width, layers):
    parents = [[] for _ in range(width)]
    for layer in range(1, layers):
        prev = (layer - 1) * width
        parents.extend([[prev + j, prev + (j + 1) % width] for j in range(width)])
    return {"parents": parents, "outputs": list(range((layers - 1) * width, layers * width))}


def check_pebbles(dag, operations, memory):
    parents = dag["parents"]
    require(isinstance(operations, (list, tuple)) and len(operations) <= 20000, "return a bounded operation list")
    red, blue = set(), {i for i, p in enumerate(parents) if not p}
    transfers, computes, peak = 0, 0, 0
    for operation in operations:
        require(isinstance(operation, (list, tuple)) and len(operation) == 2, "operation is [load/store/compute/delete, vertex]")
        op, v = operation[0], integer(operation[1], len(parents), "vertex")
        if op == "load":
            require(v in blue and v not in red, "load requires a blue-only value")
            red.add(v)
            transfers += 1
        elif op == "store":
            require(v in red, "store requires a red value")
            blue.add(v)
            transfers += 1
        elif op == "compute":
            require(parents[v] and v not in red and set(parents[v]) <= red, "compute dependencies unavailable")
            red.add(v)
            computes += 1
        elif op == "delete":
            require(v in red, "delete requires a red value")
            red.remove(v)
        else:
            raise CandidateError("unknown pebble operation")
        peak = max(peak, len(red))
        require(len(red) <= memory, "fast-memory budget exceeded")
    require(set(dag["outputs"]) <= blue, "all outputs must be stored")
    return transfers, {"compute_operations": computes, "peak_red_pebbles": peak}


def pebble_baseline(dag, memory):
    operations = []
    for v, parents in enumerate(dag["parents"]):
        if not parents:
            continue
        operations.extend(["load", p] for p in parents)
        operations += [["compute", v], ["store", v]]
        operations.extend(["delete", p] for p in parents)
        operations.append(["delete", v])
    return operations


def pebble_score(pebble):
    rows = []
    for width, layers, memory in [(4, 5, 3), (6, 5, 4), (8, 6, 6)]:
        dag = layered_dag(width, layers)
        value, details = check_pebbles(dag, pebble(copy.deepcopy(dag), memory), memory)
        reference, _ = check_pebbles(dag, pebble_baseline(dag, memory), memory)
        rows.append({"transfers": value, "baseline_transfers": reference, **details})
    return float(np.mean([r["transfers"] / r["baseline_transfers"] for r in rows])), {"instances": rows}


def sketch_baseline_update(state, item):
    """Count-Min: four 64-counter uint32 rows (1024 persistent bytes)."""
    counts = np.frombuffer(state, dtype="<u4").copy().reshape(4, 64)
    for row, prime in enumerate((1035493289, 775374203, 1495862053, 2015145641)):
        idx = ((int(item) * prime + 31 * row) % 2147483647) % 64
        counts[row, idx] += 1
    return counts.tobytes()


def sketch_baseline_query(state, item):
    counts = np.frombuffer(state, dtype="<u4").reshape(4, 64)
    return float(min(counts[row, ((int(item) * p + 31 * row) % 2147483647) % 64]
                     for row, p in enumerate((1035493289, 775374203, 1495862053, 2015145641))))


_WORKER = r'''
import contextlib,json,sys
sys.path.insert(0,sys.argv[1])
from autoresearch_suite.runtime import load_program
payload=json.load(sys.stdin)
module=load_program(sys.argv[2])
state=bytes.fromhex(payload['state'])
with contextlib.redirect_stdout(sys.stderr):
 for item in payload['items']:
  state=module.update(state,item)
  if not isinstance(state,bytes) or len(state)>1024:
   raise ValueError('persistent state must be bytes of at most 1024 bytes')
 estimates=[float(module.query(state,item)) for item in payload['queries']]
print(json.dumps({'state':state.hex(),'estimates':estimates},allow_nan=False))
'''


def stream_call(path, state, items, queries):
    # Fresh interpreter per fixed-size chunk; only serialized bytes persist.
    # This enforces the interface for cooperative candidates, not an OS sandbox.
    lib = Path(__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable, "-c", _WORKER, str(lib), str(Path(path).resolve())],
                               input=json.dumps({"state": state.hex(), "items": list(map(int, items)), "queries": list(map(int, queries))}),
                               capture_output=True, text=True, timeout=15)
    require(completed.returncode == 0, "stream worker failed: " + completed.stderr[-800:])
    try:
        answer = json.loads(completed.stdout)
        new_state = bytes.fromhex(answer["state"])
        estimates = np.asarray(answer["estimates"], float)
    except (ValueError, TypeError, KeyError):
        raise CandidateError("invalid streaming worker output") from None
    require(len(new_state) <= 1024, "persistent memory exceeded")
    require(estimates.shape == (len(queries),) and np.all(np.isfinite(estimates)) and np.all(estimates >= 0), "invalid frequency estimates")
    return new_state, estimates


def streaming_score(program_path):
    rng = np.random.default_rng(4729)
    streams = [rng.integers(0, 400, 1024), rng.zipf(1.6, 1024) % 400,
               np.concatenate([rng.integers(0, 20, 512), rng.integers(150, 400, 512)])]
    rows = []
    for stream in streams:
        state = bytes(1024)
        queries = np.arange(400)
        for i in range(0, len(stream), 256):
            state, estimates = stream_call(program_path, state, stream[i:i + 256], queries if i == 768 else [])
        counts = np.bincount(stream, minlength=400)
        error = float(np.mean(np.abs(estimates - counts)) / len(stream))
        heavy = set(np.argsort(counts)[-10:])
        recall = len(heavy & set(np.argsort(estimates)[-10:])) / 10
        rows.append({"normalized_mae": error, "top10_recall": recall, "state_bytes": len(state)})
    return float(np.mean([r["normalized_mae"] for r in rows])), {"instances": rows, "isolation": "fresh interpreter per 256-item chunk; no adversarial OS sandbox"}
