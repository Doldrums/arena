#!/usr/bin/env python3
"""Stage bounded official LHCO R&D events and pinned FastJet physics features.

This intentionally does not use signal truth to select training observations.
Source truth is used only for held-out scoring and a disjoint no-signal control.
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path, receipt_path
import concurrent.futures
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import numpy as np

from materials_http_range import HTTPRangeReader
from prepare_physics_expansion import DATA, ROOT, save_pack

URL = 'https://zenodo.org/api/records/2629073/files/events_anomalydetection.h5/content'
SIZE = 2775712410
SOURCE_MD5 = 'a06c71ae36cbd4de6699a490c06b94b7'
FEATURES = ['lighter_jet_mass_GeV', 'heavier_minus_lighter_mass_GeV',
            'lighter_girth', 'heavier_girth', 'lighter_pt_dispersion', 'heavier_pt_dispersion',
            'lighter_constituents', 'heavier_constituents']


def jet_features(row):
    import fastjet as fj
    if row.shape != (2101,) or not np.isfinite(row).all() or row[-1] not in (0, 1):
        raise ValueError('Invalid source LHCO event')
    particles = row[:-1].reshape(700, 3)
    particles = particles[particles[:, 0] > 0]
    if len(particles) < 2:
        return None
    pt, eta, phi = particles.T
    jets = [fj.PseudoJet(float(px), float(py), float(pz), float(energy)) for px, py, pz, energy in
            zip(pt*np.cos(phi), pt*np.sin(phi), pt*np.sinh(eta), pt*np.cosh(eta))]
    sequence = fj.ClusterSequence(jets, fj.JetDefinition(fj.antikt_algorithm, 1.0))
    clustered = fj.sorted_by_pt(sequence.inclusive_jets())
    if len(clustered) < 2 or clustered[0].pt() < 1300 or any(abs(jet.eta()) >= 2.5 for jet in clustered[:2]):
        return None
    first, second = clustered[:2]
    mass = float((first+second).m())
    lighter, heavier = sorted((first, second), key=lambda jet: jet.m())
    derived = []
    for jet in (lighter, heavier):
        constituents = jet.constituents()
        scalar_pt = sum(p.pt() for p in constituents)
        # Delta_R uses FastJet rapidity/azimuth geometry, consistent with anti-kT.
        girth = sum(p.pt()*jet.delta_R(p) for p in constituents) / scalar_pt
        dispersion = math.sqrt(sum(p.pt()**2 for p in constituents)) / scalar_pt
        derived.append((girth, dispersion, len(constituents)))
    return [lighter.m(), heavier.m()-lighter.m(), derived[0][0], derived[1][0],
            derived[0][1], derived[1][1], derived[0][2], derived[1][2]], mass, int(row[-1])


def prefetch_span(reader, start, end):
    """Read only the reviewed contiguous compressed slice, at most six concurrent requests."""
    blocks = list(range(start//reader.block_size, (end-1)//reader.block_size+1))
    def fetch_block(block):
        client = HTTPRangeReader(reader.url, reader.size, reader.cache, reader.block_size)
        client.seek(block*reader.block_size); client.read(reader.block_size)
        return client.receipts
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for receipt in executor.map(fetch_block, blocks):
            reader.receipts.update(receipt)


def prepare_lhco():
    import h5py
    import hdf5plugin  # registers the source archive's Blosc filter
    import fastjet
    raw = cache_path('physics-source'); raw.mkdir(parents=True, exist_ok=True)
    cache = raw/'lhco-range1mb'
    reader = HTTPRangeReader(URL, SIZE, cache, 1048576)
    features, masses, truth, source_ids = [], [], [], []
    with h5py.File(reader, 'r') as file:
        table = file['df/block0_values']
        if table.shape != (1100000, 2101) or table.chunks != (62, 2101):
            raise ValueError('LHCO source shape/chunking changed')
        # Do not walk HDF5 objects: named dataset access avoids unnecessary scans.
        start = table.id.get_chunk_info_by_coord((0, 0))
        end = table.id.get_chunk_info_by_coord((49999, 0))
        prefetch_span(reader, start.byte_offset, end.byte_offset+end.size)
        for offset in range(0, 50000, 1000):
            for index, row in enumerate(table[offset:offset+1000], offset):
                derived = jet_features(row)
                if derived is None:
                    continue
                feature, mass, target = derived
                features.append(feature); masses.append(mass); truth.append(target); source_ids.append(index)
            if offset % 5000 == 0:
                print('LHCO source rows processed', offset+1000, flush=True)
    receipt = reader.save_receipt()
    x, mass, y, ids = np.array(features), np.array(masses), np.array(truth), np.array(source_ids)
    in_window = (mass >= 2500) & (mass < 4500)
    sideband = ((mass >= 2500) & (mass < 3300)) | ((mass >= 3700) & (mass < 4500))
    train = (ids < 25000) & sideband
    test = (ids >= 25000) & (ids < 45000) & in_window
    null = (ids >= 45000) & in_window & (y == 0)
    if train.sum() < 1000 or np.sum(test & (y == 0)) < 1000 or np.sum(test & (y == 1)) < 100 or null.sum() < 500:
        raise ValueError('Fixed source subset has insufficient control/background/signal statistics')
    arrays = {'control_features': x[train], 'test_features': x[test], 'null_features': x[null],
              'truth': y[test], 'mass': mass[test], 'train_event_ids': ids[train],
              'test_event_ids': ids[test], 'null_event_ids': ids[null], 'train_mass': mass[train], 'null_mass': mass[null]}
    receipt_path = cache/'receipt.json'
    metadata = {'source_kind': 'source_simulation', 'license': 'LHCO official Zenodo2629073 CC-BY-4.0; FastJet GPL2-or-later engine attributed',
        'sources': [{'url': URL, 'source_bytes': SIZE, 'advertised_full_file_md5': SOURCE_MD5,
                     'verification': 'SHA256 of retrieved byte ranges and final source pack; full archive MD5 not claimed verified',
                     'range_receipt': str(receipt_path.relative_to(ROOT)), 'range_receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                     'hdf5_member': 'df/block0_values', 'source_row_interval': [0, 50000]},
                    {'url': 'https://fastjet.readthedocs.io/en/latest/particle.html', 'locator': 'Official anti-kT R=1 E-scheme recombination; massless source constituents'}],
        'features': FEATURES, 'preprocessing_engine': {'fastjet': fastjet.__version__, 'hdf5plugin': importlib.metadata.version('hdf5plugin')},
        'selection': 'Leading anti-kT R1 jet pT>=1300GeV; leading two jets |eta|<2.5. Features use these two jets sorted by increasing mass.',
        'split': {'train_rows': [0, 25000], 'test_rows': [25000, 45000], 'null_rows': [45000, 50000],
                  'training_mass_sidebands_GeV': [[2500, 3300], [3700, 4500]], 'test_and_null_mass_window_GeV': [2500, 4500],
                  'interval_convention': 'lower inclusive, upper exclusive', 'training_truth_filter': False},
        'counts': {'train': int(train.sum()), 'test': int(test.sum()), 'test_signal': int(y[test].sum()), 'null': int(null.sum()),
                   'training_signal_contamination_diagnostic': int(y[train].sum())},
        'adaptation': 'Fixed first50000 of the author-shuffled R&D events, disjoint row blocks; sideband training retains actual source contamination without revealing labels. Dijet mass, event IDs and truth are excluded from candidate features. Null uses disjoint true QCD events. This is Pythia8/Delphes3.4.1 source simulation; no observed-data discovery or cross-generator validation claim.',
        'engine_reuse': 'FastJet3.5.1.5 is reused for source feature preparation; active SCIEL evaluator independently implemented.'}
    return save_pack('P06', arrays, metadata)


if __name__ == '__main__':
    print(json.dumps(prepare_lhco(), indent=2))
