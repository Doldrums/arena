#!/usr/bin/env python3
"""Pin material-science data without fabricating missing benchmark examples.

--edbo fetches the compact, complete released BMS experiment table.
--validate-bundle CXX PATH validates an externally curated canonical bundle.
--geom SOURCE_PICKLE MANIFEST prepares one or more *trusted* official GEOM
pickles listed in a JSON manifest; loading pickle is opt-in and requires the
manifest SHA-256 to agree. No pickle is loaded during candidate evaluation.

All other source conversion recipes are documented in MATERIALS_EXPANSION.md.
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import data_root

import argparse
import csv
import gzip
import hashlib
import json
import pickle
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = data_root() / "materials-expansion"
sys.path.insert(0, str(ROOT / "suite/_lib"))
from autoresearch_suite import science_materials_expansion as metrics

EDBO_COMMIT = "db06b8dd592056df03ae604da030b080acd32658"
EDBO_URL = f"https://raw.githubusercontent.com/doyle-lab-ucla/edboplus/{EDBO_COMMIT}/examples/publication/BMS_yield_cost/data/experiments_yield_and_cost.csv"


def fetch_edbo():
    destination = DATA / "C01"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "experiments_yield_and_cost.csv"
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != metrics.EDBO_SHA256:
        with urllib.request.urlopen(EDBO_URL, timeout=90) as response:
            raw = response.read()
        if hashlib.sha256(raw).hexdigest() != metrics.EDBO_SHA256:
            raise ValueError("EDBO source differs from reviewed SHA-256")
        path.write_bytes(raw)
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1728:
        raise ValueError("EDBO full campaign is not 1,728 experiments")
    manifest = {"proposal_id": "C01", "source_url": EDBO_URL, "commit": EDBO_COMMIT,
                "sha256": metrics.EDBO_SHA256, "rows": len(rows), "license": "Source repository MIT; source experiment attribution retained",
                "adaptation": "Full single BMS campaign, categorical conditions, no DFT descriptor transformation, query-budget hypervolume AUC. Three permutations are robustness replicates, not held-out reaction campaigns."}
    (destination / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def prepare_geom(source_directory, manifest_path):
    """Extract explicit-H coordinates from source GEOM molecules, with hashes."""
    from rdkit import Chem
    source_directory = Path(source_directory)
    manifest = json.loads(Path(manifest_path).read_text())
    if not manifest.get("license") or not manifest.get("source_url"):
        raise ValueError("GEOM manifest must retain source license and URL")
    cases = {"training": [], "evaluation": []}
    for item in manifest["files"]:
        path = source_directory / item["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"Source GEOM hash mismatch: {path}")
        # Caller explicitly opts into trusted source pickle conversion. The
        # benchmark never deserializes untrusted candidate pickle objects.
        data = pickle.loads(raw)
        conformers = data["conformers"]
        smiles = item["smiles"]
        graph = Chem.AddHs(Chem.MolFromSmiles(smiles))
        coords = []
        for conf in conformers:
            mol = conf["rd_mol"]
            matches = mol.GetSubstructMatches(graph, useChirality=True, uniquify=False)
            if not matches:
                raise ValueError(f"GEOM graph/stereochemistry mismatch: {path}")
            order = matches[0]
            coords.append(mol.GetConformer().GetPositions()[list(order)].tolist())
        cases[item["split"]].append({"group_id": item["scaffold_group"], "smiles": smiles, "reference_coordinates": coords, "source_sha256": item["sha256"]})
    bundle = {"schema": "sciel-materials-C02-v1", "provenance": {"source_url": manifest["source_url"], "sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(), "license": manifest["license"]}, "data_kind": "computed_CREST_xTB", **cases}
    destination = DATA / "C02" / "dataset.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(bundle) + "\n")
    metrics.load_bundle("C02", {"data_path": str(destination)})
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "molecules": {k: len(v) for k, v in cases.items()}}


def fetch_matbench():
    """Real WBM initial geometries + released MP2020 DFT-hull outcomes.

    The bounded zero-shot pilot intentionally supplies no fitted training model.
    Select 512 unique-prototype records by a label-independent ID hash, then
    partition into four 128-candidate screening pools. No relaxed structure or
    computed outcome is included in the candidate's geometry records.
    """
    directory = DATA / "C03"
    raw_directory = directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)
    files = [
        ("53161835", "initial.jsonl.gz", "98d545172c1ea9060f03f40cace6f8173a4ac06f1ee875ccd963765211519b58"),
        ("64706751", "summary.csv.gz", "adbdd8b24086d4888195d8894c77f6d5fb29ce33bbb5d7d3898b4d79e964dc54"),
    ]
    receipts = []
    for file_id, name, digest in files:
        path = raw_directory / name
        url = "https://ndownloader.figshare.com/files/" + file_id
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Matbench official source SHA-256 changed: " + name)
        receipts.append({"source_url": url, "sha256": digest, "bytes": path.stat().st_size})
    with gzip.open(raw_directory / "summary.csv.gz", "rt") as f:
        rows = {row["material_id"]: row for row in csv.DictReader(f) if row["unique_prototype"].lower() == "true"}
    selected = sorted(rows, key=lambda s: hashlib.sha256(("sciel-C03-v1:" + s).encode()).hexdigest())[:512]
    structures = {}
    with gzip.open(raw_directory / "initial.jsonl.gz", "rt") as f:
        for line in f:
            item = json.loads(line)
            if item["material_id"] in selected:
                structures[item["material_id"]] = item["initial_structure"]
    if len(structures) != 512:
        raise ValueError("WBM geometry/DFT reference identifiers did not join")
    cases = []
    for i in range(4):
        group = selected[i*128:(i+1)*128]
        cases.append({"group_id": "wbm_unique_prototypes_pool_" + str(i), "source_material_ids": group,
                      "unrelaxed_structures": [structures[mid] for mid in group],
                      "dft_energy_above_hull": [float(rows[mid]["e_above_hull_mp2020_corrected_ppd_mp"]) for mid in group]})
    provenance = {"source_url": "https://figshare.com/articles/dataset/22715158", "sha256": hashlib.sha256(json.dumps(receipts, sort_keys=True).encode()).hexdigest(), "license": "CC BY 4.0", "source_files": receipts,
                  "selection": "512 source unique-prototype WBM rows with lowest SHA256(sciel-C03-v1:+material_id), no label-based selection; four consecutive pools of128", "reference": "released MP2020-corrected formation-energy distance to Materials Project reference hull"}
    bundle = {"schema": "sciel-materials-C03-v1", "provenance": provenance, "training": [], "evaluation": cases, "data_kind": "DFT_reference", "adaptation": "512-crystal zero-shot ranking pilot, not full Matbench Discovery leaderboard or ML training protocol"}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps(bundle) + "\n")
    return {"proposal_id": "C03", "crystals": 512, "pools": 4, "path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "source_files": receipts}


def fetch_adsorbml():
    """Use author-filtered valid DFT targets and adsorption-site metadata."""
    import numpy as np
    directory = DATA / "C04"
    raw_directory = directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)
    path = raw_directory / "mappings.tar.gz"
    url = "https://dl.fbaipublicfiles.com/opencatalystproject/data/adsorbml/oc20_dense_mappings.tar.gz"
    digest = "8526f0a6441910790bed2369d0447c024420b902f804617853cad73725fda658"
    if not path.exists():
        with urllib.request.urlopen(url, timeout=90) as response, path.open("wb") as f:
            shutil.copyfileobj(response, f)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("AdsorbML source archive hash changed")
    expected = {"oc20dense_mapping.pkl": "4ff64a90cb89cc43a54fc627675e96637835f048fff0e53acc25a2d8185c7abe", "oc20dense_targets.pkl": "3bb538d841dbaeba27ac7e5b2703001a64a4b6ef5854d9993f028ff8236c3062"}
    data = {}
    with tarfile.open(path) as archive:
        for name, sha in expected.items():
            raw = archive.extractfile(name).read()
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError("AdsorbML individual source member hash changed")
            data[name] = pickle.loads(raw)  # Explicitly trusted, pinned author artifact.
    mapping = {(v["system_id"], v["config_id"]): v for v in data["oc20dense_mapping.pkl"].values()}
    targets = data["oc20dense_targets.pkl"]
    systems = sorted([s for s, outcomes in targets.items() if len(outcomes) >= 20], key=lambda s: hashlib.sha256(("sciel-C04-v1:" + s).encode()).hexdigest())[:32]
    cases = []
    for system in systems:
        outcomes = sorted(targets[system], key=lambda row: hashlib.sha256((system + ":" + row[0]).encode()).hexdigest())
        info = mapping[(system, outcomes[0][0])]
        configurations = []
        for config, energy in outcomes:
            md = mapping[(system, config)]
            configurations.append({"adsorption_site_angstrom": np.asarray(md["adsorption_site"]).tolist(), "placement": "heuristic" if config.startswith("heur") else "random"})
        cases.append({"group_id": system, "surface": {k: str(info[k]) if k == "mpid" else np.asarray(info[k]).tolist() for k in ("mpid", "miller_idx", "shift", "top")}, "adsorbate": {"formula": info["adsorbate"]}, "configurations": configurations, "dft_energy_ev": [float(row[1]) for row in outcomes], "physically_valid": [True] * len(outcomes)})
    provenance = {"source_url": url, "sha256": digest, "license": "OC20 data CC BY 4.0; AdsorbML source MIT", "member_sha256": expected,
                  "archive_note": "Downloaded archive MD5 differs from old README tar checksum, but every included pickle matches the individual README MD5. Current archive and individual contents are SHA256-pinned.",
                  "validity": "Only authors' converged, anomaly-filtered target configurations. No unvalidated placement is evaluated; atomic relaxation trajectories are not redistributed.", "selection": "32 systems by source-ID hash, all valid configurations within each. Configurations reordered by hash, never source energy order."}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps({"schema": "sciel-materials-C04-v1", "provenance": provenance, "training": [], "evaluation": cases, "adaptation": "Finite-pool DFT query replay with released adsorption-site metadata; no atomic geometry relaxation or leaderboard reproduction"}) + "\n")
    return {"proposal_id": "C04", "systems": len(cases), "configurations": sum(len(c["configurations"]) for c in cases), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def fetch_arcmof():
    directory = DATA / "C05"
    raw_directory = directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)
    files = [("overall_process.csv", "af7a747b5febffe3f949b8e7cde0a787ddfcff59fdcd33cadddeae608355a25f"), ("geometric_properties.csv", "3fd6994d0c8060e61b4e19693dbeaaad7c3b7a80ff1e9e054a76718fad43daaf")]
    receipts = []
    for name, sha in files:
        path = raw_directory / name
        url = "https://zenodo.org/api/records/6908728/files/" + name + "/content"
        if not path.exists():
            with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as f:
                shutil.copyfileobj(response, f)
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("ARC-MOF source hash mismatch: " + name)
        receipts.append({"source_url": url, "sha256": sha, "bytes": path.stat().st_size})
    with (raw_directory / "geometric_properties.csv").open() as f:
        geometry = {r["filename"].removesuffix(".cif"): r for r in csv.DictReader(f) if r["ARC-MOF"] == "True"}
    with (raw_directory / "overall_process.csv").open() as f:
        outcomes = {r["filename"].removesuffix("_repeat"): r for r in csv.DictReader(f) if r["process"] == "post-combustion-vsa" and r["filename"].removesuffix("_repeat") in geometry}
    names = sorted(outcomes, key=lambda s: hashlib.sha256(("sciel-C05-v1:" + s).encode()).hexdigest())[:512]
    if len(names) != 512:
        raise ValueError("Insufficient matched ARC-MOF source rows")
    fields = ["UC_volume", "Density", "ASA", "vASA", "gASA", "AVA", "AVAf", "AVAg", "Di", "Df", "Dif"]
    cases = []
    for i in range(4):
        group = names[i*128:(i+1)*128]
        cases.append({"group_id": "ARC-MOF-post-combustion-pool-" + str(i), "source_structure_ids": group,
                      "descriptors": [{key: float(geometry[name][key]) for key in fields} for name in group],
                      "operating_conditions": {"source_process": "post-combustion-vsa", "minimum_selectivity": 10, "reference": "ARC-MOF released post-combustion VSA process definition"},
                      "working_capacity_mol_kg": [float(outcomes[name]["mmol/g_working_capacity"]) for name in group],
                      "selectivity": [float(outcomes[name]["selectivity"]) for name in group], "minimum_selectivity": 10})
    provenance = {"source_url": "https://zenodo.org/records/6908728", "sha256": hashlib.sha256(json.dumps(receipts, sort_keys=True).encode()).hexdigest(), "source_files": receipts, "license": "CC BY 4.0", "selection": "512 ARC-MOF=True structures by label-independent ID hash; released geometric descriptors only; target-derived process columns are private", "join": "Remove .cif from geometry identifiers and _repeat supercell suffix from process identifiers; geometry remains original unit-cell descriptors", "units": "source mmol/g numerically equals mol/kg"}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps({"schema": "sciel-materials-C05-v1", "provenance": provenance, "training": [], "evaluation": cases, "adaptation": "Post-combustion VSA finite-pool pilot, 20 queries per128-material pool. Selectivity>=10 is a local design constraint. No cross-topology transfer claim."}) + "\n")
    return {"proposal_id": "C05", "materials": 512, "pools": 4, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def fetch_spice():
    """Curate a ligand-group-held-out quantum-label pilot using HTTP ranges.

    Full-file verification is not claimed: downloaded ranges and the resulting
    normalized bundle are SHA256-pinned. Source dataset version, size, advertised
    MD5 and native units are retained. No simulated substitute is generated.
    """
    import h5py
    import numpy as np
    from materials_http_range import HTTPRangeReader
    directory = DATA / "C10"
    url = "https://zenodo.org/api/records/10975225/files/SPICE-2.0.1.hdf5/content"
    reader = HTTPRangeReader(url, 37479271148, directory / "ranges")
    groups = {}
    cases = {"training": [], "evaluation": []}
    source_groups = []
    bohr_angstrom, hartree_ev = .529177210903, 27.211386245988
    try:
        with h5py.File(reader, "r") as source:
            def select(name):
                text = name.decode()
                ligand = text.split(" ")[0]
                if ligand not in groups and len(groups) == 4:
                    return True
                groups.setdefault(ligand, [])
                if len(groups[ligand]) < 8:
                    groups[ligand].append(text)
                return None
            source.id.links.iterate(select)
            if len(groups) != 4:
                raise ValueError("SPICE source organization changed")
            for group_index, (ligand, names) in enumerate(groups.items()):
                accepted = 0
                for name in names:
                    g = source[name]
                    if g["conformations"].shape[0] < 2:
                        continue
                    for key, unit in [("conformations", "bohr"), ("dft_total_energy", "hartree"), ("dft_total_gradient", "hartree/bohr")]:
                        if g[key].attrs["units"] != unit:
                            raise ValueError("Unexpected SPICE physical units: " + key)
                    z = g["atomic_numbers"][:].astype(int).tolist()
                    coordinates = g["conformations"][:2] * bohr_angstrom
                    energy = g["dft_total_energy"][:2] * hartree_ev
                    forces = -g["dft_total_gradient"][:2] * hartree_ev / bohr_angstrom
                    split = "training" if group_index < 2 else "evaluation"
                    source_groups.append({"source_group": name, "split_group": ligand, "split": split, "frames": [0, 1], "subset": [s.decode() for s in g["subset"][:]], "smiles": g["smiles"][0].decode()})
                    for frame in range(2):
                        cases[split].append({"group_id": name, "split_group_id": ligand, "atomic_numbers": z, "coordinates_angstrom": coordinates[frame].tolist(), "energy_ev": float(energy[frame]), "forces_ev_angstrom": forces[frame].tolist(), "source_frame": frame})
                    accepted += 1
                    if accepted == 4:
                        break
                if accepted < 2:
                    raise ValueError("Source ligand group lacks enough independently labeled complexes")
    finally:
        ranges = reader.save_receipt()
    provenance = {"source_url": url, "sha256": hashlib.sha256(json.dumps(ranges, sort_keys=True).encode()).hexdigest(), "license": "CC0-1.0", "advertised_full_file_md5": "bfba2224b6540e1390a579569b475510", "full_file_checksum_verified": False, "range_receipt": ranges, "source_groups": source_groups,
                  "unit_conversion": {"bohr_to_angstrom": bohr_angstrom, "hartree_to_ev": hartree_ev, "force": "negative_gradient * hartree_to_ev / bohr_to_angstrom"}, "selection": "First four lexicographic ligand groups, up to four distinct amino-acid complexes per ligand, two conformers each; entire ligand groups held out, no same-ligand train/test split"}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps({"schema": "sciel-materials-C10-v1", "provenance": provenance, **cases, "adaptation": "Bounded SPICE interaction-complex acquisition pilot; eight-label budget, ligand-group holdouts. Not full SPICE training or pretrained-model benchmarking."}) + "\n")
    metrics.load_bundle("C10", {"data_path": str(destination)})
    return {"proposal_id": "C10", "training_geometries": len(cases["training"]), "evaluation_geometries": len(cases["evaluation"]), "ligand_groups": list(groups), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "source_range_bytes": sum(x["end"]-x["start"]+1 for x in ranges["blocks"].values())}


def fetch_battery():
    import numpy as np
    from scipy.io import loadmat
    directory = DATA / "C12"
    raw_directory = directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/Battery-Intelligence-Lab/Hallemans-2025-JES/3308a34396b8b56cd614291dd151c3405577c068/Data/LGM50LT/"
    sources = {"OCP_LGM50LT.mat": "9fd8293724ae5da5ad101a142875e8b6ed2c68c0f916bd6d80c13652b33d1233", "impedanceLGM50LT_Hybrid_4h_3mVrms.mat": "5f06cf0b495eeb2d5704b41a6e3c93b8e480e977b71809d5b8f5e39c643ad8c5", "DrivecycleMeasurement_80to20.mat": "981e5b045556a226ad7c08ed1401004f980d7983cafa45592f291833bfd9e0d0"}
    for name, sha in sources.items():
        path = raw_directory / name
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(base + name, timeout=90).read())
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Battery source hash differs: " + name)
    impedance = loadmat(raw_directory / "impedanceLGM50LT_Hybrid_4h_3mVrms.mat")
    drive = loadmat(raw_directory / "DrivecycleMeasurement_80to20.mat")
    names_bounds = [
        ("Series resistance [Ohm]", [.0125, .016]),
        ("Positive particle diffusion time scale [s]", [500., 10000.]),
        ("Negative particle diffusion time scale [s]", [500., 10000.]),
        ("Cation transference number", [.2, .7]),
        ("Positive electrode electrolyte diffusion time scale [s]", [100., 1000.]),
        ("Negative electrode electrolyte diffusion time scale [s]", [100., 1000.]),
        ("Separator electrolyte diffusion time scale [s]", [100., 1000.]),
        ("Positive electrode charge transfer time scale [s]", [10., 5000.]),
        ("Negative electrode charge transfer time scale [s]", [10., 5000.]),
        ("Positive electrode capacitance [F]", [1e-6, 2.]),
        ("Negative electrode capacitance [F]", [1e-6, 2.]),
        ("Positive electrode relative porosity", [.5, 1.7]),
        ("Negative electrode relative porosity", [.5, 1.7]),
        ("Reference electrolyte capacity [A.s]", [500., 2000.]),
        ("Minimum positive stoichiometry", [.1897, .1899]),
        ("Maximum positive stoichiometry", [.982, .984]),
        ("Minimum negative stoichiometry", [.0014, .0015]),
        ("Maximum negative stoichiometry", [.8862, .8864]),
    ]
    train, evaluation = [], []
    frequencies = impedance["f"].ravel()[::4]
    for j, soc in enumerate(impedance["SOC"].ravel() / 100):
        # Match the source exclusion of10%/90%; hold out whole40%/70% states.
        if j in (0, 8):
            continue
        z = impedance["Z"][::4, j]
        item = {"group_id": f"SOC_{soc:.1f}", "protocol": {"kind": "impedance", "soc": float(soc), "frequency_hz": frequencies.tolist()}, "real_ohm": z.real.tolist(), "imag_ohm": z.imag.tolist(), "normalization_ohm": .01}
        (evaluation if j in (3, 6) else train).append(item)
    # First60 seconds of the separate measured drive cycle, preserving the
    # original0.15s current trace. This entire modality is held out from fitting.
    keep = drive["t"].ravel() <= 60
    evaluation.append({"group_id": "independent_drive_protocol_80_percent", "protocol": {"kind": "voltage", "soc": .8, "time_s": drive["t"].ravel()[keep].tolist(), "current_a": (-drive["i"].ravel()[keep]).tolist()}, "voltage_v": drive["v"].ravel()[keep].tolist(), "normalization_v": .1})
    adapter = ROOT / "suite/_lib/autoresearch_suite/materials_battery_forward.py"
    provenance = {"source_url": "https://github.com/Battery-Intelligence-Lab/Hallemans-2025-JES/tree/3308a34396b8b56cd614291dd151c3405577c068", "sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(), "source_files": sources, "license": "BSD-3-Clause author repository", "adaptation": "Seventeen source frequencies per SOC;40%/70% whole SOCs and first60s of measured drive cycle held out. All18 grouped parameters retained and physical mesh matches author100/20/100 spatial and100 radial discretization. Positive capacitance lower bound1e-6 replaces zero to ensure regular model solves."}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps({"schema": "sciel-materials-C12-v1", "provenance": provenance, "training": train, "evaluation": evaluation, "parameter_bounds": dict(names_bounds), "model": {"kind": "pybop.GroupedSPMe", "adapter_path": "../../../autoresearch_suite/materials_battery_forward.py", "adapter_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest()}}) + "\n")
    return {"proposal_id": "C12", "training_socs": len(train), "heldout_socs": 2, "voltage_points": int(keep.sum()), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def fetch_nasicon():
    """Use released dynamic LCE inputs; derive an exact finite-event reference."""
    import itertools
    import numpy as np
    from autoresearch_suite.materials_nasicon import exact_moments
    commit = "7761fdd2c0506763816d5b0b42226b224f60dc70"
    base = f"https://raw.githubusercontent.com/caneparesearch/kMCpy/{commit}/"
    inputs = {
        "model": ("tests/files/input/model.json", "ca38b42250633918068e4d6ff11c7c1af998a19de6896b42239cb1de8f9ef6e6"),
        "events": ("tests/files/input/events.json", "d1d51a462e3693b6336e614d2e50147b1421cdbbe22d85e7e9f43c99d7bc5b2b"),
        "initial_state": ("example/files/input/initial_state.json", "ff0571cff0eaa816635fe6cfaa5f1d4ce2a5991571fe0590ad49691a8a8787ae"),
        "prim": ("tests/files/gather_mc_data/prim.json", "a1206dbd07f542526b20cc4fa31710fe6237ddff2575a28ccca29bbf609bf6ec"),
        "fitting_results": ("example/files/input/fitting_results.json", "e284258dd1ec1b44e667b480beed6a5312423d15643a050c6e18e7cf4faff497"),
        "fitting_results_site": ("example/files/input/fitting_results_site.json", "e284258dd1ec1b44e667b480beed6a5312423d15643a050c6e18e7cf4faff497"),
    }
    directory = DATA / "C11"; rawdir = directory / "raw"; rawdir.mkdir(parents=True, exist_ok=True)
    loaded, receipts = {}, []
    for name, (source_path, sha256) in inputs.items():
        path = rawdir / (name + ".json")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
            with urllib.request.urlopen(base + source_path, timeout=90) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != sha256:
                raise ValueError(f"NASICON source changed: {source_path}")
            path.write_bytes(content)
        loaded[name] = json.loads(path.read_text())
        receipts.append({"url": base + source_path, "sha256": sha256, "bytes": path.stat().st_size})
    source_model, events = loaded["model"], loaded["events"]
    # The released composite model embeds the example's fit. Verify rather than
    # silently pretending that the two author fit files contain different fits.
    for name, fit in (("kra", "fitting_results"), ("site", "fitting_results_site")):
        for parameter in ("keci", "empty_cluster"):
            if source_model[name]["parameters"][parameter] != loaded[fit]["0"][parameter]:
                raise ValueError("Composite LCE does not match author example fit")
    primitive = np.array(loaded["prim"]["lattice_vectors"])
    cell = primitive.copy(); cell[0] *= 2
    coordinates = np.array([(np.array(site["coordinate"]) + [replica, 0, 0]) @ primitive
                            for site in loaded["prim"]["basis"][:8] for replica in range(2)])
    images = np.array(list(itertools.product(range(-1, 2), repeat=3)))
    edges = []
    for event in events["events"]:
        a, b = event["mobile_ion_indices"]
        candidates = coordinates[b] - coordinates[a] + images @ cell
        nearest = int(np.argmin(np.linalg.norm(candidates, axis=1)))
        displacement = candidates[nearest]
        if abs(np.linalg.norm(displacement) - 3.47782) > 1e-5:
            raise ValueError("Source active-site order disagrees with NASICON hop distance")
        edges.extend([{"from": a, "to": b, "displacement_angstrom": displacement.tolist(), "periodic_image": images[nearest].tolist()},
                      {"from": b, "to": a, "displacement_angstrom": (-displacement).tolist(), "periodic_image": (-images[nearest]).tolist()}])
    active = [loaded["initial_state"]["occupation"][i] for i in events["index_metadata"]["active_to_original"]]
    model = {"mobile_count": 16, "vacancy_count": sum(active[:16]), "framework_states": active[16:],
             "attempt_hz": 5e12, "events": events["events"], "edges": edges,
             "state_encoding": {"mobile": {"Na": 0, "vacancy": 1}, "framework": {"Si": 0, "P": 1}}}
    for name in ("kra", "site"):
        model[name] = {"parameters": source_model[name]["parameters"], "lce": {key: source_model[name]["lce"][key] for key in
                        ("cluster_site_indices", "correlation_basis_indices", "site_basis_values")}}
    event_count = 1000
    reference = exact_moments(model, active, 298., [1, event_count, event_count * 2])
    adaptation = "Pinned author NASICON example fit and active-site event graph in a2x1x1 cell; Na=0/vacancy=1; fixed pure-Si framework, two vacancies,14 ions. Exact finite-event tagged-ion MSD divided by6 times expected residence duration.1000-event and2000-event values expose finite-horizon dependence. The author ships identical KRA/site fitted coefficients; they are retained explicitly. This benchmarks that declared illustrative source model, not a newly validated material fit, bulk limit or asymptotic conductivity."
    provenance = {"source_url": f"https://github.com/caneparesearch/kMCpy/tree/{commit}",
                  "sha256": hashlib.sha256(json.dumps(receipts, sort_keys=True).encode()).hexdigest(), "source_files": receipts,
                  "license": "kMCpy MIT repository; crystallographic numerical facts retained from source prim.json. Restricted ICSD CIF is not bundled.",
                  "adaptation": adaptation}
    case = {"group_id": "NASICON_2x1x1_298K_two_vacancies", "lattice": {"cell_angstrom": cell.tolist(), "positions_angstrom": coordinates.tolist(), "species_encoding": model["state_encoding"]},
            "occupancies": active, "nasicon_lce": model, "temperature_k": 298., "volume_angstrom3": float(abs(np.linalg.det(cell))),
            "reference_event_count": event_count, "exact_reference": reference}
    destination = directory / "dataset.json"
    destination.write_text(json.dumps({"schema": "sciel-materials-C11-v1", "provenance": provenance, "training": [], "evaluation": [case]}) + "\n")
    return {"proposal_id": "C11", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "mobile_sites": 16,
            "vacancies": 2, "undirected_events": 24, "reference": reference}


def validate_bundle(code, path):
    bundle = metrics.load_bundle(code, {"data_path": path})
    # Domain-specific mandatory keys, not a generic regression table accepted
    # in place of a promised scientific benchmark.
    fields = {
        "C02": ["smiles", "reference_coordinates"],
        "C03": ["unrelaxed_structures", "dft_energy_above_hull"],
        "C04": ["surface", "adsorbate", "configurations", "dft_energy_ev", "physically_valid"],
        "C05": ["descriptors", "operating_conditions", "working_capacity_mol_kg", "selectivity", "minimum_selectivity"],
        "C07": ["h_spectrum", "c_spectrum", "target_smiles", "metadata"],
        "C08": ["two_theta", "intensity", "wavelength_angstrom", "candidate_library", "phase_ids", "annotation_complete"],
        "C10": ["atomic_numbers", "coordinates_angstrom", "energy_ev", "forces_ev_angstrom"],
        "C11": ["lattice", "occupancies", "edges", "site_energy_ev", "temperature_k", "volume_angstrom3", "reference_diffusivity_m2_s", "reference_diffusivity_std_m2_s", "reference_converged"],
        "C12": ["protocol"],
    }
    if code not in fields:
        raise ValueError("C01 uses its exact CSV; C06/C09 are specified model simulations")
    for case in bundle["evaluation"]:
        required = ["lattice", "occupancies", "nasicon_lce", "temperature_k", "reference_event_count", "exact_reference"] if code == "C11" and "nasicon_lce" in case else fields[code]
        missing = set(required) - case.keys()
        if missing:
            raise ValueError(f"{code} missing required source fields: {sorted(missing)}")
    return {"proposal_id": code, "training_cases": len(bundle.get("training", [])), "evaluation_cases": len(bundle["evaluation"]), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(), "validation": "schema_and_group_split_only; scientific seed execution still required"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--edbo", action="store_true")
    group.add_argument("--matbench", action="store_true")
    group.add_argument("--adsorbml", action="store_true")
    group.add_argument("--arcmof", action="store_true")
    group.add_argument("--spice", action="store_true")
    group.add_argument("--battery", action="store_true")
    group.add_argument("--nasicon", action="store_true")
    group.add_argument("--validate-bundle", nargs=2, metavar=("CXX", "PATH"))
    group.add_argument("--geom", nargs=2, metavar=("TRUSTED_SOURCE_DIRECTORY", "MANIFEST"))
    args = parser.parse_args()
    result = fetch_edbo() if args.edbo else fetch_matbench() if args.matbench else fetch_adsorbml() if args.adsorbml else fetch_arcmof() if args.arcmof else fetch_spice() if args.spice else fetch_battery() if args.battery else fetch_nasicon() if args.nasicon else validate_bundle(*args.validate_bundle) if args.validate_bundle else prepare_geom(*args.geom)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
