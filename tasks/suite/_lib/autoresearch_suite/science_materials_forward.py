"""Forward-model checks for mechanisms, potentials, kinetic Monte Carlo and batteries."""
from __future__ import annotations

from .science_materials_expansion import (
    DATA,
    Path,
    copy,
    hashlib,
    importlib,
    indices,
    load_bundle,
    math,
    np,
    numeric,
    require,
    time,
)

def mechanism_trajectory(gas, condition, times, species):
    import cantera as ct
    gas.TP = condition["temperature"], condition["pressure_atm"] * ct.one_atm
    gas.set_equivalence_ratio(condition["phi"], "H2", "O2:1,AR:3.76")
    reactor = ct.IdealGasConstPressureReactor(gas, clone=True)
    solver = ct.ReactorNet([reactor])
    solver.rtol, solver.atol = 1e-9, 1e-15
    rows = []
    for t in times:
        solver.advance(float(t))
        rows.append([reactor.T] + [reactor.phase[s].X[0] for s in species])
    return np.array(rows)


def reduce_cantera(selection, full, required_species):
    import cantera as ct
    require(isinstance(selection, dict), "reduced mechanism must specify species and reaction_indices")
    names = selection.get("species")
    require(isinstance(names, list) and len(names) == len(set(names)), "species must be a unique list")
    require(set(required_species) <= set(names) <= set(full.species_names), "missing required or unknown species")
    picked = indices(selection.get("reaction_indices"), full.n_reactions)
    reactions = [full.reaction(int(i)) for i in picked]
    for reaction in reactions:
        require(set(reaction.reactants) | set(reaction.products) <= set(names), "reaction references removed species")
    # Species thermo and reaction rates come only from the independently loaded
    # full mechanism. Cantera checks balance and rate/thermo compatibility.
    return ct.Solution(thermo="ideal-gas", kinetics="gas", species=[full.species(s) for s in names], reactions=reactions)


def mechanism_score(fn, p):
    import cantera as ct
    require(ct.__version__.startswith("3.2."), "requires_setup: Cantera 3.2.x is required for the pinned h2o2 mechanism protocol")
    full = ct.Solution("h2o2.yaml")
    training = [{"temperature": 1000., "pressure_atm": 1., "phi": 1.}, {"temperature": 1200., "pressure_atm": 5., "phi": .7}]
    required = ["H2", "O2", "H2O", "OH", "AR"]
    public = {"yaml": full.write_yaml(), "species": full.species_names, "reaction_equations": full.reaction_equations(), "required_species": required, "mechanism": "Cantera_3.2_h2o2"}
    reduced = reduce_cantera(fn(copy.deepcopy(public), copy.deepcopy(training), p.get("tolerance", .05)), full, required)
    holdout = p.get("conditions", [{"temperature": 950., "pressure_atm": 1., "phi": .7}, {"temperature": 1100., "pressure_atm": 2., "phi": 1.3}, {"temperature": 1300., "pressure_atm": 5., "phi": 1.}])
    times = np.geomspace(1e-7, .03, 90)
    errors = []
    for condition in holdout:
        target = mechanism_trajectory(full, condition, times, required[:-1])
        pred = mechanism_trajectory(reduced, condition, times, required[:-1])
        scale = np.maximum(np.max(target, axis=0) - np.min(target, axis=0), [100., 1e-3, 1e-3, 1e-3, 1e-5])
        error = float(np.max(np.abs(pred - target) / scale))
        # Sampled ignition delay is independently estimated from max dT/dt.
        ref_ignition = float(times[np.argmax(np.diff(target[:, 0]) / np.diff(times)) + 1])
        got_ignition = float(times[np.argmax(np.diff(pred[:, 0]) / np.diff(times)) + 1])
        if np.ptp(target[:, 0]) > 100:
            error = max(error, abs(got_ignition - ref_ignition) / ref_ignition)
        require(error <= p.get("tolerance", .05), f"reduced mechanism worst scientific error {error:.4g} exceeds tolerance")
        errors.append(error)
    return 1 - .5 * (reduced.n_species / full.n_species + reduced.n_reactions / full.n_reactions), {"species": reduced.n_species, "reactions": reduced.n_reactions, "full_species": full.n_species, "full_reactions": full.n_reactions, "worst_errors": errors, "model_validation": "reference_mechanism_agreement_not_experimental_truth"}


def checked_potential(potential, z, coordinates, derivative_tolerance=.005):
    r = numeric(coordinates)
    energy, forces = potential(list(z), r.copy())
    energy = float(numeric(energy, ()))
    # A candidate may reuse its output buffer on subsequent potential calls.
    # Preserve this evaluation before finite differences and rotated queries.
    forces = numeric(forces, r.shape, "forces").copy()
    require(np.linalg.norm(forces.sum(axis=0)) < derivative_tolerance, "net force violates translation symmetry")
    require(np.linalg.norm(np.cross(r - r.mean(axis=0), forces).sum(axis=0)) < derivative_tolerance, "net torque violates rotation symmetry")
    h = 1e-4
    for i, j in [(0, 0), (len(r) - 1, 1), (len(r) // 2, 2)]:
        plus, minus = r.copy(), r.copy(); plus[i, j] += h; minus[i, j] -= h
        derivative = -(float(potential(list(z), plus)[0]) - float(potential(list(z), minus)[0])) / (2 * h)
        require(abs(derivative - forces[i, j]) <= derivative_tolerance, "forces are not the negative energy gradient")
    rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    e2, f2 = potential(list(z), r @ rotation.T + [2.3, -1.2, .7])
    require(abs(float(e2) - energy) < derivative_tolerance, "energy lacks rigid-motion invariance")
    require(np.max(np.abs(numeric(f2, r.shape) - forces @ rotation.T)) < derivative_tolerance, "forces lack rotational equivariance")
    return energy, forces


def potential_score(module, p):
    d = load_bundle("C10", p)
    training = d["training"]
    require(training, "SPICE task requires a source-derived acquisition pool")
    pool = [{"atomic_numbers": c["atomic_numbers"], "coordinates_angstrom": c["coordinates_angstrom"], "group_id": c["group_id"]} for c in training]
    observations, used = [], set()
    for _ in range(min(p.get("budget", 32), len(pool))):
        i = int(indices(module.acquire(copy.deepcopy(pool), copy.deepcopy(observations), 1), len(pool), 1)[0])
        require(i not in used, "quantum label queried twice")
        used.add(i)
        observations.append({"index": i, **copy.deepcopy(training[i])})
    model = module.fit(copy.deepcopy(observations))
    require(callable(getattr(model, "potential", None)), "fit must return an object with potential(atomic_numbers, coordinates)")
    force_errors, energy_groups = [], {}
    for c in d["evaluation"]:
        energy, forces = checked_potential(model.potential, c["atomic_numbers"], c["coordinates_angstrom"])
        truth = numeric(c["forces_ev_angstrom"], forces.shape)
        force_errors.extend((forces - truth).ravel().tolist())
        energy_groups.setdefault(c["group_id"], []).append((energy, float(c["energy_ev"])))
        # Evaluator-controlled short velocity-Verlet stress test in eV, Angstrom,
        # fs. This catches instability; it is not a quantum-accuracy reference.
        from rdkit import Chem
        masses = np.array([Chem.GetPeriodicTable().GetAtomicWeight(int(z)) for z in c["atomic_numbers"]])[:, None] * 103.6426965
        r = numeric(c["coordinates_angstrom"]).copy(); v = np.zeros_like(r); dt = .1
        for _ in range(5):
            r += v * dt + .5 * forces / masses * dt ** 2
            _, new_forces = checked_potential(model.potential, c["atomic_numbers"], r)
            v += .5 * (forces + new_forces) / masses * dt
            forces = new_forces
            require(np.max(np.abs(r)) < 1e4 and np.max(np.abs(v)) < 100, "potential has catastrophic short-trajectory instability")
    relative_errors = []
    for rows in energy_groups.values():
        a = np.array(rows)
        if len(a) > 1:
            relative_errors.extend(((a[:, 0] - a[:, 0].mean()) - (a[:, 1] - a[:, 1].mean())).tolist())
    require(relative_errors, "SPICE evaluation needs multiple conformers per held-out molecule to score relative energies")
    force_rmse = float(np.sqrt(np.mean(np.square(force_errors))))
    energy_rmse = float(np.sqrt(np.mean(np.square(relative_errors))))
    return force_rmse + energy_rmse, {"force_rmse_ev_angstrom": force_rmse, "relative_energy_rmse_ev": energy_rmse, "label_queries": len(used), "scalarization": "force_RMSE/(1_eV/Angstrom)+relative_energy_RMSE/(1_eV)"}


def kmc_rates(case, occupied):
    kb_ev = 8.617333262145e-5
    available, rates = [], []
    for i, edge in enumerate(case["edges"]):
        if occupied[edge["from"]] and not occupied[edge["to"]]:
            require(edge["barrier_ev"] >= 0 and edge["attempt_hz"] > 0, "invalid physical migration barrier")
            available.append(i)
            rates.append(edge["attempt_hz"] * math.exp(-edge["barrier_ev"] / (kb_ev * case["temperature_k"])))
    return available, np.array(rates)


def kmc_seed(lattice, occupancies, barrier_model, temperature, budget):
    if barrier_model.get("kind") == "nasicon_lce":
        from .materials_nasicon import nasicon_seed
        return nasicon_seed(lattice, occupancies, barrier_model, temperature, budget)
    case = {"edges": barrier_model["edges"], "temperature_k": temperature}
    rng = np.random.default_rng(budget["seed"])
    occupied = np.array(occupancies, bool)
    result = []
    for _ in range(budget["events"]):
        available, rates = kmc_rates(case, occupied)
        require(len(rates) > 0, "absorbing occupation state")
        dt = float(rng.exponential(1 / rates.sum()))
        edge_index = int(rng.choice(available, p=rates / rates.sum()))
        edge = case["edges"][edge_index]
        occupied[edge["from"]] = False; occupied[edge["to"]] = True
        result.append([dt, edge_index])
    return result


def kmc_score(fn, p):
    from scipy.stats import kstest
    d = load_bundle("C11", p)
    if all("nasicon_lce" in case for case in d["evaluation"]):
        from .materials_nasicon import nasicon_score
        outputs = [nasicon_score(fn, case, p) for case in d["evaluation"]]
        return float(np.mean([value[0] for value in outputs])), {"transport": [value[1] for value in outputs], "metric": "candidate_seconds_times_squared_relative_standard_error"}
    scores, diagnostics = [], []
    for c in d["evaluation"]:
        require(c.get("reference_converged") is True and c.get("reference_diffusivity_std_m2_s", 0) > 0, "requires_setup: independently converged transport references with uncertainty are required")
        require(c["temperature_k"] > 0 and c["volume_angstrom3"] > 0, "invalid lattice thermodynamics")
        edge_map = {(e["from"], e["to"]): e for e in c["edges"]}
        site_energy = numeric(c["site_energy_ev"])
        for e in c["edges"]:
            rev = edge_map.get((e["to"], e["from"]))
            require(rev is not None and abs((e["barrier_ev"] - rev["barrier_ev"]) - (site_energy[e["to"]] - site_energy[e["from"]])) < 1e-8 and e["attempt_hz"] == rev["attempt_hz"], "barrier model violates detailed balance")
        estimates, waiting, categorical = [], [], []
        started = time.perf_counter()
        for seed in p.get("seeds", list(range(130, 162))):
            events_count = p.get("events", 500)
            budget = {"events": events_count, "seed": seed}
            events = numeric(fn(copy.deepcopy(c["lattice"]), list(c["occupancies"]), {"edges": copy.deepcopy(c["edges"]), "site_energy_ev": site_energy.tolist()}, c["temperature_k"], budget), (events_count, 2), "kMC event history")
            occupied = np.array(c["occupancies"], bool)
            labels = np.full(len(occupied), -1, dtype=int); labels[occupied] = np.arange(occupied.sum())
            displacement = np.zeros((occupied.sum(), 3)); duration = 0.0
            rng = np.random.default_rng(seed + 99000)
            for dt, edge_index in events:
                require(dt > 0 and edge_index == int(edge_index), "invalid kMC waiting time or edge identifier")
                available, rates = kmc_rates(c, occupied)
                require(int(edge_index) in available, "kMC move violates exclusion or graph adjacency")
                j = available.index(int(edge_index)); probability = rates / rates.sum()
                categorical.append(float(probability[:j].sum() + rng.random() * probability[j]))
                waiting.append(float(dt * rates.sum()))
                edge = c["edges"][int(edge_index)]
                label = labels[edge["from"]]
                displacement[label] += numeric(edge["displacement_angstrom"], (3,))
                labels[edge["to"]] = label; labels[edge["from"]] = -1
                occupied[edge["from"]] = False; occupied[edge["to"]] = True
                duration += dt
            estimates.append(float(np.mean(np.sum(displacement ** 2, axis=1)) * 1e-20 / (2 * c.get("dimension", 3) * duration)))
        elapsed = time.perf_counter() - started
        require(kstest(waiting, "expon").pvalue > 1e-5, "waiting-time law disagrees with exponential kinetics")
        require(kstest(categorical, "uniform").pvalue > 1e-5, "event probabilities disagree with physical transition rates")
        mean = float(np.mean(estimates)); se = float(np.std(estimates, ddof=1) / np.sqrt(len(estimates)))
        reference = c["reference_diffusivity_m2_s"]
        require(abs(mean - reference) <= 4 * math.hypot(se, c["reference_diffusivity_std_m2_s"]), "diffusivity inconsistent with independent reference uncertainty")
        conductivity = int(np.sum(c["occupancies"])) * (c.get("charge_number", 1) * 1.602176634e-19) ** 2 * mean / (c["volume_angstrom3"] * 1e-30 * 1.380649e-23 * c["temperature_k"])
        scores.append(elapsed * (se / reference) ** 2)
        diagnostics.append({"diffusivity_m2_s": mean, "standard_error_m2_s": se, "nernst_einstein_conductivity_s_m": conductivity, "conductivity_correlation_assumption": "uncorrelated_tracer_Nernst_Einstein"})
    return float(np.mean(scores)), {"transport": diagnostics, "metric": "elapsed_seconds_times_squared_relative_standard_error"}


def battery_score(fn, p):
    d = load_bundle("C12", p)
    # The model adapter is evaluator-owned, versioned source code, never supplied
    # by the candidate. The original paper uses PyBOP's GroupedSPMe, not an RC fit.
    spec = d.get("model", {})
    require(spec.get("kind") == "pybop.GroupedSPMe", "requires_setup: the paper's GroupedSPMe model is required")
    adapter = Path(p.get("data_path", DATA / "C12" / "dataset.json")).parent / spec.get("adapter_path", "forward_model.py")
    require(adapter.is_file() and hashlib.sha256(adapter.read_bytes()).hexdigest() == spec.get("adapter_sha256"), "requires_setup: pinned evaluator-owned GroupedSPMe adapter is missing or changed")
    module_spec = importlib.util.spec_from_file_location("trusted_battery_forward", adapter)
    model = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(model)
    calls = [0]
    def forward(parameters, protocol):
        calls[0] += 1
        require(calls[0] <= p.get("budget", 100), "battery fitting exceeded forward-solve budget")
        return model.forward(copy.deepcopy(parameters), copy.deepcopy(protocol))
    bounds = d["parameter_bounds"]
    answer = fn(copy.deepcopy(d["training"]), forward, copy.deepcopy(bounds), p.get("budget", 100))
    require(isinstance(answer, dict) and set(answer) == set(bounds), "return exactly the grouped physical parameter dictionary")
    for name, value in answer.items():
        require(math.isfinite(float(value)) and bounds[name][0] <= value <= bounds[name][1], f"parameter outside physical bounds: {name}")
    impedance, voltage = [], []
    for c in d["evaluation"]:
        prediction = model.forward(copy.deepcopy(answer), copy.deepcopy(c["protocol"]))
        if c["protocol"]["kind"] == "impedance":
            pred = numeric(prediction, (len(c["real_ohm"]), 2), "complex impedance [real,imag]")
            target = np.c_[c["real_ohm"], c["imag_ohm"]]
            impedance.append(float(np.sqrt(np.mean((pred - target) ** 2)) / c["normalization_ohm"]))
        else:
            pred = numeric(prediction, (len(c["voltage_v"]),), "voltage")
            voltage.append(float(np.sqrt(np.mean((pred - c["voltage_v"]) ** 2)) / c["normalization_v"]))
    require(impedance and voltage, "battery evaluation requires both held-out SOC impedance and time-domain protocols")
    return .5 * (float(np.mean(impedance)) + float(np.mean(voltage))), {"impedance_normalized_rmse": impedance, "voltage_normalized_rmse": voltage, "candidate_forward_calls": calls[0], "identifiability_claim": False}
