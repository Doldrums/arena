"""Source-based chemistry/materials adapters (C01--C12).

There is deliberately no synthetic-data fallback for the released-data tasks.
Canonical bundles retain source hashes and group splits; see the preparation
script and docs/MATERIALS_EXPANSION.md. Evaluation is an API separation, not an
OS security boundary: run untrusted candidates with evaluator files inaccessible.
"""
from __future__ import annotations

from arena_task_paths import data_root

import copy
import csv
import hashlib
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np

from .runtime import CandidateError, require

DATA = data_root() / "materials-expansion"
EDBO_SHA256 = "3bfdeeb6a55ed316efbc95a8158f9476bb851f37eda48330f1d0ae820d6cf0cd"


def numeric(value, shape=None, name="output"):
    try:
        x = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        raise CandidateError(f"{name} must be numeric") from None
    require(np.isfinite(x).all(), f"{name} contains nonfinite values")
    if shape is not None:
        require(x.shape == tuple(shape), f"{name} has shape {x.shape}; expected {shape}")
    return x


def indices(value, n, k=None):
    a = np.asarray(value)
    require(a.ndim == 1 and a.dtype.kind in "iu", "selection must be a one-dimensional integer array")
    require(len(a) > 0 and (k is None or len(a) == k), "wrong selection size")
    require(len(set(a.tolist())) == len(a), "duplicate selections are not allowed")
    require(bool(np.all((a >= 0) & (a < n))), "selection outside candidate pool")
    return a.astype(int)


def load_bundle(code, parameters):
    path = Path(parameters.get("data_path", DATA / code / "dataset.json"))
    require(path.is_file(), f"requires_setup: {code} source bundle missing: {path}. See docs/MATERIALS_EXPANSION.md and scripts/prepare_materials_expansion.py")
    raw = path.read_bytes()
    if parameters.get("data_sha256"):
        require(hashlib.sha256(raw).hexdigest() == parameters["data_sha256"], "source bundle SHA-256 mismatch")
    d = json.loads(raw)
    require(d.get("schema") == f"sciel-materials-{code}-v1", f"wrong {code} bundle schema")
    provenance = d.get("provenance", {})
    require(bool(provenance.get("source_url") and provenance.get("sha256") and provenance.get("license")), "bundle must retain source URL, SHA-256 and dataset license")
    require(d.get("evaluation") and isinstance(d.get("training", []), list), "bundle needs evaluation cases and a training list")
    train = {str(c.get("split_group_id", c["group_id"])) for c in d.get("training", [])}
    test = {str(c.get("split_group_id", c["group_id"])) for c in d["evaluation"]}
    require(not train & test, "training/evaluation group leakage")
    return d


def hypervolume2(points):
    """Exact union of rectangles [0,x] x [0,y], for maximization."""
    p = numeric(points, name="objectives")
    require(p.ndim == 2 and p.shape[1] == 2 and np.all(p >= 0), "expected nonnegative two-objective points")
    order = p[np.argsort(p[:, 0], kind="stable")]
    best = np.maximum.accumulate(order[::-1, 1])[::-1]
    return float(np.dot(np.diff(np.r_[0.0, order[:, 0]]), best))


def edbo_score(suggest, parameters):
    path = Path(parameters.get("data_path", DATA / "C01" / "experiments_yield_and_cost.csv"))
    require(path.is_file(), "requires_setup: run python scripts/prepare_materials_expansion.py --edbo")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == EDBO_SHA256, "EDBO+ source table hash mismatch")
    with path.open() as f:
        rows = list(csv.DictReader(f))
    targets = numeric([[float(r["yield"]), float(r["cost"])] for r in rows])
    require(len(rows) == 1728, "EDBO+ campaign row count differs from pinned release")
    costs = targets[:, 1]
    objectives = np.c_[targets[:, 0] / 100.0, (costs.max() - costs) / (costs.max() - costs.min())]
    optimal = hypervolume2(objectives)
    scores = []
    for seed in parameters.get("seeds", [211, 307, 419]):
        permutation = np.random.default_rng(seed).permutation(len(rows))
        pool = [{k: v for k, v in rows[j].items() if k not in ("yield", "cost", "new_index")} for j in permutation]
        observations, used, trajectory = [], set(), []
        for _ in range(parameters.get("budget", 32)):
            selected = indices(suggest(copy.deepcopy(observations), copy.deepcopy(pool), 1), len(pool), 1)
            i = int(selected[0])
            require(i not in used, "candidate queried a previously observed experiment")
            used.add(i)
            row = int(permutation[i])
            observations.append({"index": i, "yield": float(targets[row, 0]), "cost": float(targets[row, 1])})
            trajectory.append(hypervolume2(objectives[permutation[sorted(used)]]) / optimal)
        scores.append(float(np.mean(trajectory)))
    return float(np.mean(scores)), {"normalized_hypervolume_auc": scores, "experiments": len(rows), "query_budget": parameters.get("budget", 32), "data_kind": "measured_yields_and_released_cost_accounting", "transfer_claim": False}


def conformer_metrics(smiles, prediction, reference, threshold=0.5, maximum=20):
    from rdkit import Chem
    from rdkit.Chem import rdMolAlign
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    require(mol is not None, "invalid source molecule")
    x = numeric(prediction, name="conformers")
    ref = numeric(reference, name="reference conformers")
    require(x.ndim == 3 and x.shape[1:] == (mol.GetNumAtoms(), 3) and 1 <= len(x) <= maximum, "conformers must be K by explicit-H atom count by 3, within budget")
    require(ref.ndim == 3 and ref.shape[1:] == x.shape[1:], "source conformer atom order mismatch")
    pt = Chem.GetPeriodicTable()
    radii = np.array([pt.GetRcovalent(a.GetAtomicNum()) for a in mol.GetAtoms()])
    required_chirality = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
    templates = []
    for coords in x:
        pair = np.linalg.norm(coords[:, None] - coords[None, :], axis=-1)
        iu = np.triu_indices(len(coords), 1)
        require(np.all(pair[iu] > 0.55 * (radii[:, None] + radii[None, :])[iu]), "conformer contains atomic clashes")
        for b in mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            require(pair[i, j] < 1.6 * (radii[i] + radii[j]), "bond connectivity is inconsistent with coordinates")
        trial = Chem.Mol(mol)
        conf = Chem.Conformer(len(coords))
        for i, p in enumerate(coords):
            conf.SetAtomPosition(i, p)
        trial.AddConformer(conf, assignId=True)
        Chem.AssignStereochemistryFrom3D(trial)
        Chem.AssignStereochemistry(trial, cleanIt=True, force=True)
        for i, code in required_chirality.items():
            require(trial.GetAtomWithIdx(i).HasProp("_CIPCode") and trial.GetAtomWithIdx(i).GetProp("_CIPCode") == code, "conformer violates specified stereochemistry")
        templates.append(Chem.RemoveHs(trial))
    errors = []
    for coords in ref:
        target = Chem.Mol(mol)
        conf = Chem.Conformer(len(coords))
        for i, p in enumerate(coords):
            conf.SetAtomPosition(i, p)
        target.AddConformer(conf, assignId=True)
        target = Chem.RemoveHs(target)
        errors.append(min(rdMolAlign.GetBestRMS(Chem.Mol(pred), target) for pred in templates))
    return float(np.mean(np.array(errors) <= threshold)), float(np.mean(errors))


def conformer_score(fn, p):
    d = load_bundle("C02", p)
    values = []
    for c in d["evaluation"]:
        prediction = fn(c["smiles"], c.get("stereochemistry", "explicit_smiles"), p.get("max_conformers", 20))
        values.append(conformer_metrics(c["smiles"], prediction, c["reference_coordinates"], p.get("rmsd_threshold", .5), p.get("max_conformers", 20)))
    return float(np.mean([v[0] for v in values])), {"mean_matching_rmsd_angstrom": float(np.mean([v[1] for v in values])), "molecules": len(values), "reference_kind": "GEOM_CREST_xTB"}


def crystal_score(fn, p):
    d = load_bundle("C03", p)
    scores = []
    for c in d["evaluation"]:
        structures = c["unrelaxed_structures"]
        k = min(p.get("budget", 20), len(structures))
        chosen = indices(fn(copy.deepcopy(structures), k), len(structures), k)
        hull = numeric(c["dft_energy_above_hull"], (len(structures),))
        scores.append(float(np.mean(hull[chosen] <= 0.0)))
    return float(np.mean(scores)), {"stable_precision_at_budget": scores, "reference_kind": "DFT_convex_hull_not_synthesis"}


def adsorption_score(fn, p):
    d = load_bundle("C04", p)
    successes, regrets = [], []
    for c in d["evaluation"]:
        n = len(c["configurations"])
        energies = numeric(c["dft_energy_ev"], (n,))
        valid = np.asarray(c["physically_valid"], bool)
        require(valid.shape == (n,) and valid.any(), "source must identify valid adsorption configurations")
        used, observations = set(), []
        for _ in range(min(p.get("budget", 10), n)):
            choice = fn(copy.deepcopy(c["surface"]), copy.deepcopy(c["adsorbate"]), copy.deepcopy(c["configurations"]), copy.deepcopy(observations))
            i = int(indices([choice], n, 1)[0])
            require(i not in used, "adsorption query repeated")
            used.add(i)
            observations.append({"index": i, "energy_ev": float(energies[i]), "physically_valid": bool(valid[i])})
        found = [i for i in used if valid[i]]
        regret = float(min(energies[found]) - min(energies[valid])) if found else None
        regrets.append(regret)
        successes.append(regret is not None and regret <= 0.1)
    return float(np.mean(successes)), {"regret_ev": regrets, "success_tolerance_ev": 0.1}


def mof_score(fn, p):
    d = load_bundle("C05", p)
    scores = []
    for c in d["evaluation"]:
        capacity = numeric(c["working_capacity_mol_kg"])
        selectivity = numeric(c["selectivity"], capacity.shape)
        feasible = selectivity >= c["minimum_selectivity"]
        require(feasible.any() and capacity[feasible].max() > 0, "source pool lacks a positive feasible capacity")
        observations, used = [], set()
        for _ in range(min(p.get("budget", 20), len(capacity))):
            answer = fn(copy.deepcopy(c["descriptors"]), copy.deepcopy(c["operating_conditions"]), copy.deepcopy(observations), 1)
            i = int(indices(answer, len(capacity), 1)[0])
            require(i not in used, "MOF query repeated")
            used.add(i)
            observations.append({"index": i, "working_capacity_mol_kg": float(capacity[i]), "selectivity": float(selectivity[i])})
        selected = [i for i in used if feasible[i]]
        scores.append(float(max(capacity[selected]) / max(capacity[feasible])) if selected else 0.0)
    return float(np.mean(scores)), {"feasible_capacity_fraction": scores, "data_kind": "computed_adsorption"}


def pfhub_initial(n, phase=0.0):
    x, y = np.meshgrid(np.arange(n) * 200.0 / n, np.arange(n) * 200.0 / n, indexing="ij")
    return .5 + .01 * (np.cos(.105 * x + phase) * np.cos(.11 * y) + (np.cos(.13 * x) * np.cos(.087 * y + phase)) ** 2 + np.cos(.025 * x - .15 * y) * np.cos(.07 * x - .02 * y))


def laplacian(x, dx):
    return (np.roll(x, 1, 0) + np.roll(x, -1, 0) + np.roll(x, 1, 1) + np.roll(x, -1, 1) - 4 * x) / dx ** 2


def free_energy(c, p):
    dx = p["length"] / len(c)
    # Forward differences match the discrete Laplacian variational derivative.
    grad2 = ((np.roll(c, -1, 0) - c) / dx) ** 2 + ((np.roll(c, -1, 1) - c) / dx) ** 2
    return float(np.sum(p["rho"] * (c - p["alpha"]) ** 2 * (p["beta"] - c) ** 2 + .5 * p["kappa"] * grad2) * dx ** 2)


def phase_rhs(t, flat, shape, p):
    c = flat.reshape(shape)
    derivative = 2 * p["rho"] * (c - p["alpha"]) * (c - p["beta"]) * (2 * c - p["alpha"] - p["beta"])
    mu = derivative - p["kappa"] * laplacian(c, p["length"] / len(c))
    return (p["mobility"] * laplacian(mu, p["length"] / len(c))).ravel()


def phase_reference(initial, parameters, times):
    from scipy.integrate import solve_ivp
    sol = solve_ivp(phase_rhs, (0, float(times[-1])), initial.ravel(), args=(initial.shape, parameters), t_eval=times, method="DOP853", rtol=2e-10, atol=2e-12)
    require(sol.success, "independent PFHub reference integration failed")
    return sol.y.T.reshape((len(times),) + initial.shape)


def phase_seed(initial, parameters, times):
    """Second-order CN/Heun IMEX integration; candidate seed, not reference."""
    c = np.array(initial, float, copy=True)
    n = len(c)
    dx = parameters["length"] / n
    eig1 = -4 * np.sin(np.pi * np.fft.fftfreq(n)) ** 2 / dx ** 2
    eig = eig1[:, None] + eig1[None, :]
    t, output = 0.0, []
    for target in times:
        while t < target - 1e-12:
            dt = min(.02, target - t)
            fp = 2 * parameters["rho"] * (c - parameters["alpha"]) * (c - parameters["beta"]) * (2 * c - parameters["alpha"] - parameters["beta"])
            chat = np.fft.fft2(c)
            linear = parameters["mobility"] * parameters["kappa"] * eig ** 2
            nonlinear = parameters["mobility"] * eig * np.fft.fft2(fp)
            predicted = np.fft.ifft2((chat + dt * nonlinear) / (1 + dt * linear)).real
            fp2 = 2 * parameters["rho"] * (predicted - parameters["alpha"]) * (predicted - parameters["beta"]) * (2 * predicted - parameters["alpha"] - parameters["beta"])
            nonlinear2 = parameters["mobility"] * eig * np.fft.fft2(fp2)
            c = np.fft.ifft2(((1 - .5 * dt * linear) * chat + .5 * dt * (nonlinear + nonlinear2)) / (1 + .5 * dt * linear)).real
            t += dt
        output.append(c.copy())
    return np.array(output)


def phase_score(fn, p):
    parameters = {"length": 200.0, "alpha": .3, "beta": .7, "rho": 5.0, "kappa": 2.0, "mobility": 5.0, "boundary": "periodic", "spatial_contract": "second_order_periodic_finite_volume"}
    times = np.array(p.get("times", [1., 5., 20.]))
    elapsed, errors, drifts, energies = [], [], [], []
    for n, phase in p.get("cases", [[48, 0.0], [64, .31]]):
        initial = pfhub_initial(n, phase)
        reference = phase_reference(initial, parameters, times)
        started = time.perf_counter()
        output = numeric(fn(initial.copy(), dict(parameters), times.copy()), reference.shape, "composition fields")
        elapsed.append(time.perf_counter() - started)
        error = float(np.sqrt(np.mean((output - reference) ** 2)))
        drift = float(np.max(np.abs(output.mean(axis=(1, 2)) - initial.mean())))
        energy = np.array([free_energy(initial, parameters)] + [free_energy(c, parameters) for c in output])
        require(error <= p.get("rmse_tolerance", 2e-5), f"phase-field RMSE {error:.3g} exceeds fixed tolerance")
        require(drift < 1e-9, "phase-field mass is not conserved")
        require(np.all(np.diff(energy) <= 1e-7), "phase-field free energy increased")
        errors.append(error); drifts.append(drift); energies.append(energy.tolist())
    return float(sum(elapsed)), {"field_rmse": errors, "mass_drift": drifts, "free_energy": energies, "protocol": "PFHub_1a_equations_fixed_mesh_short_horizon_adaptation", "reference": "independent_DOP853_method_of_lines"}


def canonical_smiles(smiles, formula=None, stereochemistry=False):
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    require(isinstance(smiles, str), "structure must be a SMILES string")
    mol = Chem.MolFromSmiles(smiles)
    require(mol is not None and len(Chem.GetMolFrags(mol)) == 1, "invalid or disconnected molecular graph")
    if formula:
        require(rdMolDescriptors.CalcMolFormula(mol) == formula, "predicted molecular formula differs")
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=stereochemistry)


def nmr_score(fn, p):
    d = load_bundle("C07", p)
    scores, top1 = [], []
    for c in d["evaluation"]:
        k = p.get("top_k", 5)
        metadata = copy.deepcopy(c.get("metadata", {}))
        answer = fn(copy.deepcopy(c["h_spectrum"]), copy.deepcopy(c["c_spectrum"]), metadata, k)
        require(isinstance(answer, (list, tuple)) and 1 <= len(answer) <= k, "return one to K molecular SMILES")
        keys = [canonical_smiles(s, metadata.get("formula"), c.get("resolve_stereochemistry", False)) for s in answer]
        require(len(set(keys)) == len(keys), "duplicate molecular hypotheses")
        target = canonical_smiles(c["target_smiles"], metadata.get("formula"), c.get("resolve_stereochemistry", False))
        scores.append(target in keys); top1.append(keys[0] == target)
    return float(np.mean(scores)), {"top1_exact_graph_recovery": float(np.mean(top1)), "top_k": p.get("top_k", 5), "data_kind": d.get("data_kind", "simulated_NMR")}


def phase_set_f1(predicted, target, allowed):
    require(isinstance(predicted, (list, tuple)) and predicted, "phase prediction must be a nonempty list")
    require(all(isinstance(x, str) for x in predicted), "phase identifiers must be strings")
    require(len(set(predicted)) == len(predicted), "duplicate phase identifiers")
    require(set(predicted) <= set(allowed), "unknown phase identifier")
    require(bool(target), "source scan has no verified phase annotation")
    return 2 * len(set(predicted) & set(target)) / (len(predicted) + len(set(target)))


def xrd_score(fn, p):
    d = load_bundle("C08", p)
    values = []
    for c in d["evaluation"]:
        source_reported = c.get("annotation_scope") == "source_reported_curated_phase_set" and bool(c.get("annotation_evidence"))
        require(c.get("annotation_complete") is True or source_reported, "partially labeled opXRD scans must not be scored as complete phase sets")
        two_theta = numeric(c["two_theta"])
        intensity = numeric(c["intensity"], two_theta.shape)
        require(two_theta.ndim == 1 and len(two_theta) > 2 and np.all(np.diff(two_theta) > 0), "diffraction angles must increase")
        library = c["candidate_library"]
        allowed = [item["id"] for item in library]
        require(len(allowed) == len(set(allowed)) and set(c["phase_ids"]) <= set(allowed), "phase library must contain distinct identifiers and all source labels")
        wavelength = float(c["wavelength_angstrom"])
        require(np.isfinite(wavelength) and wavelength > 0, "positive finite X-ray wavelength required")
        answer = fn(two_theta.copy(), intensity.copy(), wavelength, copy.deepcopy(library))
        phases = answer.get("phases") if isinstance(answer, dict) else answer
        values.append(phase_set_f1(phases, c["phase_ids"], [item["id"] for item in library]))
    return float(np.mean(values)), {"phase_set_f1": values, "quantitative_fraction_claim": False,
                                 "annotation_scope": d.get("provenance", {}).get("annotation_scope", "source-reported curated labels when declared; otherwise explicit complete annotation"),
                                 "unreported_impurities_are_known_absent": False}


from .science_materials_forward import (
    battery_score,
    checked_potential,
    kmc_rates,
    kmc_score,
    kmc_seed,
    mechanism_score,
    mechanism_trajectory,
    potential_score,
    reduce_cantera,
)


def evaluate(module, parameters):
    code = parameters["proposal_id"]
    dispatch = {
        "C01": (edbo_score, "suggest"), "C02": (conformer_score, "conformers"),
        "C03": (crystal_score, "rank_crystals"), "C04": (adsorption_score, "choose_configuration"),
        "C05": (mof_score, "select_mofs"), "C06": (phase_score, "evolve_composition"),
        "C07": (nmr_score, "elucidate"), "C08": (xrd_score, "identify_phases"),
        "C09": (mechanism_score, "reduce_mechanism"), "C11": (kmc_score, "transport"),
        "C12": (battery_score, "infer_parameters"),
    }
    if code == "C10":
        return potential_score(module, parameters)
    score, method = dispatch[code]
    require(callable(getattr(module, method, None)), f"candidate must implement {method}")
    return score(getattr(module, method), parameters)
