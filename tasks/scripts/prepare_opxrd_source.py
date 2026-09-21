#!/usr/bin/env python3
"""Curate measured HKUST-A opXRD phase labels; never manufacture scan intensities."""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import data_root, receipt_path
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import numpy as np
from materials_http_range import HTTPRangeReader

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = data_root() / 'materials-expansion/C08'
URL = 'https://zenodo.org/api/records/15298026/files/opxrd.zip/content'
SIZE = 1400997733
PINS = ROOT/'data/science/materials_expansion/opxrd_hkust_a_sources.json'


def nested(value):
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return value
        return nested(decoded)
    if isinstance(value, list):
        return [nested(v) for v in value]
    if isinstance(value, dict):
        return {k: nested(v) for k, v in value.items()}
    return value


def crystal(phase):
    lattice = list(ast.literal_eval(phase['lattice']))
    sites, composition = [], Counter()
    for atom in phase['basis']:
        element = re.match(r'[A-Z][a-z]?', atom['symbol']).group()
        occupancy = float(atom['occupancy'])
        position = np.mod([atom['x'], atom['y'], atom['z']], 1.)
        position[np.isclose(position, 1, atol=1e-9)] = 0.
        sites.append({'element': element, 'occupancy': occupancy, 'fractional_coordinates': position.tolist()})
        composition[element] += occupancy
    # This selected contributor's structures use integer unit-cell compositions.
    if not composition or any(abs(n-round(n)) > 1e-7 or n <= 0 for n in composition.values()):
        raise ValueError('This source subset requires positive integer formula counts')
    divisor = math.gcd(*[round(n) for n in composition.values()])
    formula = ''.join(f'{element}{round(composition[element])/divisor:g}' for element in sorted(composition))
    sites.sort(key=lambda s: (s['element'], *np.round(s['fractional_coordinates'], 8)))
    return {'lattice_parameters_angstrom_degrees': lattice, 'sites': sites, 'reduced_composition': formula}


def same_phase(a, b):
    """Merge identical source bases with tiny refinement differences, notably beta-Sn."""
    if a['reduced_composition'] != b['reduced_composition'] or len(a['sites']) != len(b['sites']):
        return False
    if not np.allclose(a['lattice_parameters_angstrom_degrees'][:3], b['lattice_parameters_angstrom_degrees'][:3], rtol=.001, atol=0):
        return False
    if not np.allclose(a['lattice_parameters_angstrom_degrees'][3:], b['lattice_parameters_angstrom_degrees'][3:], atol=.01, rtol=0):
        return False
    for x, y in zip(a['sites'], b['sites']):
        if x['element'] != y['element'] or abs(x['occupancy']-y['occupancy']) > 1e-8:
            return False
        delta = np.array(x['fractional_coordinates'])-y['fractional_coordinates']
        if np.max(np.abs(delta-np.round(delta))) > 1e-5:
            return False
    return True


def prepare():
    pins = json.loads(PINS.read_text())
    reader = HTTPRangeReader(URL, SIZE, DIRECTORY/'ranges')
    samples, library, receipts = [], [], []
    with zipfile.ZipFile(reader) as archive:
        for source in pins['members']:
            raw = archive.read(source['member'])
            digest = hashlib.sha256(raw).hexdigest()
            if digest != source['sha256']:
                raise ValueError('opXRD member differs from reviewed source hash')
            d = nested(json.loads(raw)); label = d['label']
            if label['is_simulated'] is not False or not label['phases']:
                raise ValueError('Only measured, fully structurally labeled HKUST-A records are accepted')
            phase_ids, compounds = [], []
            for phase in label['phases']:
                structure = crystal(phase)
                match = next((item for item in library if same_phase(item['structure'], structure)), None)
                if match is None:
                    phase_id = 'phase-' + hashlib.sha256(json.dumps(structure, sort_keys=True).encode()).hexdigest()[:12]
                    match = {'id': phase_id, 'structure': structure, 'source_members': []}
                    library.append(match)
                match['source_members'].append(source['member'])
                phase_ids.append(match['id']); compounds.append(structure['reduced_composition'])
            number = int(Path(source['member']).stem.split('_')[1])
            samples.append({'source_scan': source['member'], 'source_index': number, 'compounds': sorted(set(compounds)),
                            'two_theta': d['two_theta_values'], 'intensity': d['intensities'],
                            'wavelength_angstrom': float(label['xray_info']['primary_wavelength']),
                            'secondary_wavelength_angstrom': label['xray_info']['secondary_wavelength'],
                            'phase_ids': list(dict.fromkeys(phase_ids)), 'annotation_complete': None,
                            'annotation_scope': 'source_reported_curated_phase_set',
                            'annotation_evidence': 'opXRD paper section3.2: HKUST-A/XRed phase-identification subset, refined CIF labels, measured single/multiphase samples. All released source phases retained; unreported impurities unknown.'})
            receipts.append({'member': source['member'], 'sha256': digest, 'crc32': archive.getinfo(source['member']).CRC})
    # A connected-component split keeps every shared compound/mixture series together.
    groups = [{i} for i in range(len(samples))]
    changed = True
    while changed:
        changed = False
        for i in range(len(groups)):
            compounds = set().union(*(samples[j]['compounds'] for j in groups[i]))
            found = next((k for k in range(i+1, len(groups)) if compounds & set().union(*(samples[j]['compounds'] for j in groups[k]))), None)
            if found is not None:
                groups[i] |= groups.pop(found); changed = True; break
    heldout_indices = {5, 7, 9, 11, 13, 15, 17, 19}
    training, evaluation = [], []
    public_library = [{'id': item['id'], 'structure': item['structure']} for item in sorted(library, key=lambda x:x['id'])]
    for group in groups:
        compounds = sorted(set().union(*(samples[j]['compounds'] for j in group)))
        group_id = 'compound-component-' + hashlib.sha256('|'.join(compounds).encode()).hexdigest()[:12]
        heldout = any(samples[j]['source_index'] in heldout_indices for j in group)
        for j in sorted(group):
            case = samples[j]
            case.update(group_id=group_id, split_group_id=group_id, candidate_library=public_library)
            (evaluation if heldout else training).append(case)
    provenance = {'source_url': URL, 'sha256': hashlib.sha256(json.dumps(receipts, sort_keys=True).encode()).hexdigest(),
                  'annotation_scope': 'source_reported_curated_phase_set; physical exhaustiveness unknown',
                  'sha256_scope': 'canonical manifest of21 uncompressed source members, not full1.4GB archive SHA256',
                  'source_members': receipts, 'license': 'opXRD Zenodo15298026 CC-BY4.0; Hollarek et al.; HKUST-A contribution Tong-yi Zhang/XRed.',
                  'adaptation': 'Closed-library recovery of all source-reported HKUST-A phase labels. Complete atom/lattice structures do not establish physical phase exhaustiveness; unreported impurities and all phase fractions remain unknown. No generated spectra or mixtures. Compound-connected split within one contributor, not a cross-laboratory study. Supplied references are source crystal structures, never held-out experimental intensities.'}
    bundle = {'schema': 'sciel-materials-C08-v1', 'provenance': provenance, 'training': training, 'evaluation': evaluation}
    path = DIRECTORY/'dataset.json'
    path.write_text(json.dumps(bundle, separators=(',', ':'), allow_nan=False)+'\n')
    reader.save_receipt()
    report = {'proposal_id': 'C08', 'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'training_cases': len(training), 'evaluation_cases': len(evaluation), 'reference_phases': len(public_library),
              'compound_groups': len(groups), 'source_members': receipts, 'annotation_scope': 'source_reported_curated_phase_set'}
    (receipt_path('opxrd-preparation.json')).write_text(json.dumps(report, indent=2)+'\n')
    return {k:v for k,v in report.items() if k != 'source_members'}


if __name__ == '__main__':
    print(json.dumps(prepare(), indent=2))
