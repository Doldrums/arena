"""Source-data biology protocols; no fabricated fallback benchmark data.

Prepared bundles live outside the candidate package. Small source-derived bundles
can be prepared with scripts/prepare_biology_expansion.py. Fixtures are accepted
by the metric functions for tests, never by the dataset loader as benchmark data.
"""
from __future__ import annotations

from arena_task_paths import cache_path, receipt_path

import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import tempfile
import subprocess
import numpy as np
from scipy import stats
from scipy.ndimage import gaussian_filter
from scipy.spatial.distance import cdist
from .runtime import CandidateError, require

ROOT = Path(__file__).resolve().parents[3]


def array(value, shape=None, nonnegative=False):
    raw = np.asarray(value)
    require(raw.dtype.kind in 'fiu' and not np.iscomplexobj(raw), 'Expected real numeric values')
    out = raw.astype(float)
    require(np.isfinite(out).all(), 'Output contains nonfinite values')
    if shape is not None:
        require(out.shape == tuple(shape), f'Expected shape {shape}, got {out.shape}')
    if nonnegative:
        require(np.all(out >= 0), 'Expected nonnegative values')
    return out


def load_bundle(proposal, parameters=None):
    directory = Path(os.environ.get('SCIEL_BIOLOGY_DATA', str(cache_path('science-biology'))))
    bundle_path, receipt_path = directory / f'{proposal}.json', directory / f'{proposal}.manifest.json'
    if not bundle_path.is_file() or not receipt_path.is_file():
        raise RuntimeError(f'{proposal} requires source data. Run python scripts/prepare_biology_expansion.py --proposal {proposal}; see docs/BIOLOGY_EXPANSION.md. Missing {bundle_path}')
    raw = bundle_path.read_bytes()
    receipt = json.loads(receipt_path.read_text())
    require(hashlib.sha256(raw).hexdigest() == receipt.get('bundle_sha256'), 'Prepared source bundle checksum mismatch')
    data = json.loads(raw)
    require(data.get('proposal_id') == proposal and data.get('schema_version') == 1, 'Wrong source bundle schema/proposal')
    require(data.get('source_kind') in ('measured', 'upstream_simulation', 'computational_targets', 'mixed'), 'Test fixtures are not benchmark datasets')
    require(bool(data.get('sources')) and bool(data.get('split_description')) and bool(data.get('cases')), 'Incomplete dataset provenance or cases')
    for source in data['sources']:
        require(source.get('url', '').startswith('https://') and re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')), 'Source URL and SHA256 are required')
    return data


def spearman(truth, prediction):
    truth, prediction = array(truth), array(prediction)
    require(truth.shape == prediction.shape and truth.ndim == 1 and len(truth) >= 2, 'Invalid rank inputs')
    if np.ptp(truth) == 0:
        raise ValueError('Reference effects have no rank variation')
    return 0.0 if np.ptp(prediction) == 0 else float(stats.spearmanr(truth, prediction).statistic)


def protein_score(module, cases):
    result = []
    for c in cases:
        model = module.fit(c['reference'], list(c['support_variants']), array(c['support_effects']).copy())
        prediction = array(model.score(list(c['query_variants'])), (len(c['query_variants']),))
        truth = array(c['query_effects'], prediction.shape)
        rho = spearman(truth, prediction)
        k = max(1, math.ceil(len(truth) * .1))
        # Stable top-k is a diagnostic, not a tie-sensitive objective.
        selected = np.argsort(-prediction, kind='stable')[:k]
        beneficial = set(np.argsort(-truth, kind='stable')[:k])
        result.append({'assay': c['id'], 'spearman': rho, 'top_decile_recall': len(set(selected) & beneficial) / k})
    return float(np.mean([c['spearman'] for c in result])), {'assays': result, 'aggregation': 'equal assay weight; local supervised protocol, not official ProteinGym leaderboard weighting'}


def pairs(structure):
    stack, paired = [], []
    for i, char in enumerate(structure):
        if char == '(':
            stack.append(i)
        elif char == ')':
            require(bool(stack), 'Unbalanced dot-bracket target')
            paired.append((stack.pop(), i))
        else:
            require(char == '.', 'Only pseudoknot-free dot-bracket targets are supported')
    require(not stack, 'Unbalanced dot-bracket target')
    return paired


class FoldOracle:
    def __init__(self, structure, constraints, budget, version='2.6.4'):
        import RNA
        if RNA.__version__ != version:
            raise RuntimeError(f'ViennaRNA {version} required; installed {RNA.__version__}')
        self.RNA, self.structure, self.constraints = RNA, structure, constraints
        self.budget, self.calls = int(budget), 0
        pairs(structure)

    def validate(self, sequence):
        require(isinstance(sequence, str) and len(sequence) == len(self.structure), 'RNA sequence has wrong length/type')
        require(set(sequence) <= set('ACGU'), 'RNA sequence must use ACGU')
        require(all(b == 'N' or sequence[i] == b for i, b in enumerate(self.constraints)), 'Locked RNA base changed')

    def _fold(self, sequence):
        self.validate(sequence)
        md = self.RNA.md()
        md.temperature = 37.0
        compound = self.RNA.fold_compound(sequence, md)
        structure, energy = compound.mfe()
        return structure, float(energy)

    def __call__(self, sequence):
        require(self.calls < self.budget, 'RNA folding call budget exhausted')
        self.calls += 1
        return self._fold(sequence)


def rna_score(module, cases):
    results = []
    for c in cases:
        target = c['structure']
        constraints = c.get('constraints', 'N' * len(target))
        oracle = FoldOracle(target, constraints, c.get('budget', 64))
        sequence = module.design(target, constraints, oracle)
        folded, energy = oracle._fold(sequence)  # final verification is outside search budget
        results.append({'target': c['id'], 'solved': folded == target, 'base_pair_distance': len(set(pairs(folded)) ^ set(pairs(target))), 'fold_calls': oracle.calls, 'mfe': energy})
    return float(np.mean([r['solved'] for r in results])), {'targets': results, 'engine': 'ViennaRNA 2.6.4, 37 C, deterministic MFE structure equality', 'budget_scope': 'provided oracle calls; trusted candidate protocol, not process-level sandbox enforcement'}


def perturbation_score(module, cases):
    results = []
    for c in cases:
        train = array(c['training_shifts'])
        query = [list(q) for q in c['query_perturbations']]
        prediction = array(module.predict_shift(train.copy(), copy.deepcopy(c['training_perturbations']), query, copy.deepcopy(c['gene_context'])), (len(query), train.shape[1]))
        truth = array(c['query_shifts'], prediction.shape)
        center = train.mean(axis=0)
        reference_mse = float(np.mean((truth - center) ** 2))
        require(reference_mse > 0, 'Degenerate perturbation reference')
        # Subtract the training perturbation mean from both matrices to avoid
        # rewarding the shared transcriptional response (Systema motivation).
        corrected_truth, corrected_prediction = truth - center, prediction - center
        distance = cdist(corrected_prediction, corrected_truth, metric='sqeuclidean')
        retrieval = float(np.mean(np.argmin(distance, axis=1) == np.arange(len(query))))
        nmse = float(np.mean((prediction - truth) ** 2) / reference_mse)
        results.append({'study': c['id'], 'reference_corrected_nmse': nmse, 'perturbation_retrieval_top1': retrieval, 'rmse': float(np.sqrt(np.mean((prediction-truth)**2)))})
    return float(np.mean([x['reference_corrected_nmse'] for x in results])), {'studies': results, 'metric_note': 'independent mean-reference normalized MSE, not the complete Systema published metric suite'}


def integration_metrics(embedding, batches, cell_types, k=10):
    embedding = array(embedding)
    require(embedding.ndim == 2 and 1 <= embedding.shape[1] <= 128 and len(embedding) == len(batches), 'Embedding must be cells x 1..128')
    n = len(embedding)
    require(n > 2 and len(cell_types) == n, 'Too few cells or incompatible labels')
    batches, cell_types = np.asarray(batches), np.asarray(cell_types)
    require(len(set(batches.tolist())) >= 2 and len(set(cell_types.tolist())) >= 2, 'Integration benchmark needs multiple batches and cell types')
    d = cdist(embedding, embedding)
    np.fill_diagonal(d, np.inf)
    k = min(k, n - 1)
    neighbors = np.argsort(d, axis=1, kind='stable')[:, :k]
    # Equal-weight cell-type neighborhood conservation protects rare cell types.
    purity = np.mean(cell_types[neighbors] == cell_types[:, None], axis=1)
    bio = float(np.mean([purity[cell_types == kind].mean() for kind in np.unique(cell_types)]))
    # Mixing is assessed within each biological type. A type represented in one
    # batch supplies no mixing information and is omitted instead of penalized.
    mix = []
    for kind in np.unique(cell_types):
        indices = np.flatnonzero(cell_types == kind)
        labels = batches[indices]
        unique, counts = np.unique(labels, return_counts=True)
        if len(unique) < 2 or len(indices) < 3:
            continue
        dist = d[np.ix_(indices, indices)]
        nn = np.argsort(dist, axis=1, kind='stable')[:, :min(k, len(indices)-1)]
        global_p = counts / len(indices)
        local = np.stack([(labels[nn] == b).mean(axis=1) for b in unique], axis=1)
        mix.append(float(np.mean(1 - .5 * np.abs(local - global_p).sum(axis=1))))
    require(bool(mix), 'No cell type spans multiple batches')
    mixing = float(np.mean(mix))
    return {'score': .6 * bio + .4 * mixing, 'cell_type_macro_neighbor_purity': bio, 'within_type_batch_mixing': mixing, 'rare_type_purity': float(min(purity[cell_types == kind].mean() for kind in np.unique(cell_types)))}


def integration_score(module, cases):
    results = []
    for c in cases:
        embedding = module.integrate(array(c['counts']).copy(), np.asarray(c['batches']).copy())
        result = integration_metrics(embedding, c['batches'], c['cell_types'], c.get('neighbors', 10))
        results.append({'study': c['id'], **result})
    return float(np.mean([c['score'] for c in results])), {'studies': results, 'metric_note': 'explicit local 60% biology/40% batch metric inspired by scIB; not official scIB aggregate, trajectory score not claimed'}


def trusted_forward(spec):
    path = Path(spec['path']).resolve()
    require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256'], 'Trusted forward-model file is absent or its checksum changed')
    module_spec = importlib.util.spec_from_file_location('biology_trusted_forward_' + spec['sha256'][:10], path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def flux_score(module, cases):
    results = []
    for c in cases:
        forward = trusted_forward(c['forward_model']).simulate
        network = copy.deepcopy(c['network'])
        bounds = array(network['bounds'])
        S = array(network['stoichiometry'])
        measured, sigma = array(c['measurements']), array(c['standard_deviations'])
        train = np.asarray(c['training_indices'], dtype=int)
        test = np.asarray(c['evaluation_indices'], dtype=int)
        require(not set(train) & set(test) and len(test) > 0 and np.all(sigma > 0), 'Flux measurement split/noise invalid')
        budget = c.get('budget', 100)
        calls = [0]
        def loss(flux):
            calls[0] += 1
            require(calls[0] <= budget, 'Flux forward-call budget exhausted')
            values = array(forward(array(flux, (len(bounds),))), measured.shape)
            return float(np.mean(((values[train] - measured[train])/sigma[train])**2))
        public = {'indices': train.tolist(), 'values': measured[train].tolist(), 'standard_deviations': sigma[train].tolist()}
        prediction = module.infer_fluxes(network, copy.deepcopy(c['atom_maps']), public, loss, budget)
        flux = array(prediction['fluxes'], (len(bounds),))
        require(np.all(flux >= bounds[:, 0]-1e-8) and np.all(flux <= bounds[:, 1]+1e-8), 'Flux bounds violated')
        residual = float(np.max(np.abs(S @ flux)))
        require(residual <= c.get('balance_tolerance', 1e-6), 'Steady-state mass balance violated')
        intervals = array(prediction['intervals'], (len(bounds), 2))
        require(np.all(intervals[:, 0] <= flux) and np.all(intervals[:, 1] >= flux), 'Flux interval must contain point estimate')
        pred = array(forward(flux), measured.shape)
        nll = float(np.mean(.5*((pred[test]-measured[test])/sigma[test])**2 + np.log(sigma[test]*np.sqrt(2*np.pi))))
        results.append({'experiment': c['id'], 'heldout_gaussian_nll': nll, 'balance_residual': residual, 'forward_calls': calls[0], 'interval_width': float(np.mean(intervals[:, 1]-intervals[:, 0]))})
    return float(np.mean([x['heldout_gaussian_nll'] for x in results])), {'experiments': results, 'uncertainty_note': 'interval validity checked; calibration cannot be established from unknown real fluxes'}


def deconvolution_score(module, cases):
    results = []
    for c in cases:
        counts, reference = array(c['spatial_counts']), array(c['reference_profiles'])
        train, test = np.asarray(c['training_genes'], dtype=int), np.asarray(c['evaluation_genes'], dtype=int)
        require(not set(train) & set(test) and len(test) > 0, 'Spatial held-out genes overlap training')
        # Reference signatures have fixed absolute per-cell scale, so returned
        # abundances are cell counts, not arbitrary normalized mixture weights.
        abund = array(module.deconvolve(counts[:, train].copy(), reference[train].copy(), array(c['coordinates']).copy()), (len(counts), reference.shape[1]), nonnegative=True)
        mean = np.maximum(abund @ reference[test].T, 1e-12)
        y = counts[:, test]
        from scipy.special import gammaln
        poisson_nll = float(np.mean(mean-y*np.log(mean)+gammaln(y+1)))
        diagnostic = {'section': c['id'], 'heldout_gene_poisson_nll': poisson_nll}
        if 'known_abundances' in c:
            truth = array(c['known_abundances'], abund.shape)
            diagnostic['constructed_mixture_abundance_nmse'] = float(np.mean((truth-abund)**2)/max(np.mean(truth**2), 1e-12))
        results.append(diagnostic)
    return float(np.mean([x['heldout_gene_poisson_nll'] for x in results])), {'sections': results, 'evidence_note': 'real tissue held-out count likelihood does not establish true abundance recovery'}


from .science_biology_phylogeny import (
    parse_newick,
    phylogeny_score,
    tree_log_likelihood,
)


def assembly_score(module, cases):
    results = []
    for c in cases:
        contigs = module.assemble(list(c['reads']), copy.deepcopy(c['library_metadata']))
        require(isinstance(contigs, (list, tuple)) and 0 < len(contigs) <= c.get('max_contigs', 10000), 'Return a bounded nonempty list of contigs')
        require(all(isinstance(x, str) and x and set(x) <= set('ACGTN') for x in contigs), 'Invalid contig sequence')
        require(sum(map(len, contigs)) <= c.get('max_bases', 10000000), 'Assembly output too large')
        # QUAST/metaQUAST is the trusted aligner/evaluator; do not equate raw N50
        # or exact matches to reference-aware assembly quality.
        executable = c.get('quast_executable', 'metaquast.py')
        with tempfile.TemporaryDirectory(prefix='sciel-assembly-') as tmp:
            tmp = Path(tmp)
            (tmp/'contigs.fa').write_text(''.join(f'>contig_{i}\n{x}\n' for i,x in enumerate(contigs)))
            refs = []
            for i, sequence in enumerate(c['reference_genomes']):
                path = tmp/f'ref_{i}.fa'; path.write_text(f'>ref_{i}\n{sequence}\n'); refs.append(str(path))
            command = [executable, str(tmp/'contigs.fa'), '-r', ','.join(refs), '-o', str(tmp/'quast'), '--threads', '1', '--min-contig', str(c.get('min_contig', 100))]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=c.get('evaluator_timeout', 180))
            if completed.returncode:
                raise RuntimeError('metaQUAST failed: ' + completed.stderr[-1000:])
            report = tmp/'quast/combined_reference/report.tsv'
            if not report.is_file(): report = tmp/'quast/report.tsv'
            metrics = {row.split('\t')[0]: row.split('\t')[1] for row in report.read_text().splitlines() if '\t' in row}
            fraction = float(metrics['Genome fraction (%)']) / 100
            misassemblies = int(metrics['# misassemblies'])
            errors = float(metrics.get('# mismatches per 100 kbp', '0')) + float(metrics.get('# indels per 100 kbp', '0'))
            score = fraction / (1 + misassemblies + errors/1000)
            results.append({'community': c['id'], 'score': score, 'genome_fraction': fraction, 'misassemblies': misassemblies, 'sequence_errors_per_100kb': errors, 'corrected_NA50': metrics.get('NA50')})
    return float(np.mean([x['score'] for x in results])), {'communities': results}


def image_metrics(truth, prediction, data_range):
    truth, prediction = array(truth), array(prediction, np.shape(truth), nonnegative=True)
    require(truth.ndim == 2 and min(truth.shape) >= 7 and data_range > 0, 'SSIM needs 2D images >=7 pixels and positive calibrated range')
    mse = float(np.mean((prediction-truth)**2))
    psnr = float(10*np.log10(data_range**2/max(mse, np.finfo(float).tiny)))
    # Wang-style local Gaussian SSIM, population covariance, sigma 1.5.
    mu1, mu2 = gaussian_filter(truth, 1.5), gaussian_filter(prediction, 1.5)
    v1 = gaussian_filter(truth*truth, 1.5)-mu1*mu1
    v2 = gaussian_filter(prediction*prediction, 1.5)-mu2*mu2
    covariance = gaussian_filter(truth*prediction, 1.5)-mu1*mu2
    c1, c2 = (.01*data_range)**2, (.03*data_range)**2
    ssim = ((2*mu1*mu2+c1)*(2*covariance+c2))/((mu1**2+mu2**2+c1)*(v1+v2+c2))
    return {'psnr': psnr, 'ssim': float(ssim[3:-3, 3:-3].mean()), 'relative_intensity_bias': float((prediction.mean()-truth.mean())/max(truth.mean(), 1e-12))}


def denoising_score(module, cases):
    results=[]
    for c in cases:
        noisy = array(c['noisy_image'])
        result = image_metrics(c['reference_image'], module.denoise(noisy.copy(), copy.deepcopy(c['metadata'])), c['metadata']['data_range'])
        result['field_of_view'] = c['id']
        results.append(result)
    return float(np.mean([x['psnr'] for x in results])), {'fields': results, 'reference_note': 'averaged acquired exposures are an imperfect clean reference'}


def kinetics_score(module, cases):
    results = []
    for c in cases:
        runner = trusted_forward(c['forward_model'])
        problem = copy.deepcopy(c['problem'])
        rows = copy.deepcopy(c['training_measurements'])
        bounds = array(problem['bounds'])
        budget, calls = c.get('budget', 64), [0]
        def objective(parameters):
            calls[0] += 1
            require(calls[0] <= budget, 'Kinetics likelihood evaluation budget exhausted')
            params = array(parameters, (len(bounds),))
            if np.any(params < bounds[:,0]) or np.any(params > bounds[:,1]): return 1e100
            return float(runner.negative_log_likelihood(params, copy.deepcopy(rows), copy.deepcopy(problem)))
        # Candidate optimizers may normalize or otherwise edit their input.
        # Keep both forward-model configuration and oracle targets canonical.
        public = copy.deepcopy({**problem, 'measurements': rows})
        result = module.fit_kinetics(public, objective, budget)
        parameters = array(result['parameters'], (len(bounds),))
        require(np.all(parameters >= bounds[:,0]) and np.all(parameters <= bounds[:,1]), 'Kinetic parameter bounds violated')
        intervals = array(result['intervals'], (len(bounds),2))
        require(np.all(intervals[:,0] <= parameters) and np.all(intervals[:,1] >= parameters), 'Kinetic intervals must contain estimate')
        nll = float(runner.negative_log_likelihood(parameters, copy.deepcopy(c['evaluation_measurements']), copy.deepcopy(problem)))
        require(np.isfinite(nll) and nll < 1e99, 'Kinetic simulator failed or returned nonfinite likelihood')
        results.append({'model': c['id'], 'heldout_condition_nll': nll, 'objective_calls': calls[0]})
    return float(np.mean([r['heldout_condition_nll'] for r in results])), {'models': results, 'uncertainty_note': 'interval format validated, not calibrated without coverage experiments'}


def average_precision(truth, scores):
    truth, scores = np.asarray(truth, bool), array(scores)
    require(truth.shape == scores.shape and truth.ndim == 1 and truth.any(), 'AP requires nonempty positives and matching vectors')
    order = np.argsort(-scores, kind='stable')
    labels, scores = truth[order], scores[order]
    ends = np.r_[np.flatnonzero(np.diff(scores) != 0), len(scores)-1]
    tp = np.cumsum(labels)[ends]
    precision = tp/(ends+1)
    increments = np.diff(np.r_[0, tp])/truth.sum()
    return float(np.sum(increments * precision))


def network_score(module, cases):
    results=[]
    for c in cases:
        genes = list(c['genes']); regulators = list(c['regulators'])
        output = module.infer_network(array(c['expression']).copy(), list(genes), list(regulators), copy.deepcopy(c.get('ordering')))
        require(isinstance(output, (list, tuple)), 'Network output must be (regulator,target,score) rows')
        allowed = [(r,t) for r in regulators for t in genes if r != t]
        lookup, seen = {}, set()
        for row in output:
            require(isinstance(row,(list,tuple)) and len(row) == 3, 'Malformed network edge')
            r,t,score = row
            require((r,t) in allowed and (r,t) not in seen, 'Forbidden or duplicate network edge')
            seen.add((r,t)); lookup[(r,t)] = float(array([score], (1,))[0])
        # Missing edges tie below every submitted edge; complete denominator.
        floor = min(lookup.values(), default=0)-1
        score = [lookup.get(edge, floor) for edge in allowed]
        positive = set(map(tuple,c['reference_edges']))
        truth = np.array([edge in positive for edge in allowed])
        ap = average_precision(truth, score)
        results.append({'network': c['id'], 'average_precision': ap, 'random_prevalence': float(truth.mean()), 'ap_above_random': ap-float(truth.mean()), 'positive_edges': int(truth.sum()), 'possible_edges': len(allowed)})
    return float(np.mean([r['average_precision'] for r in results])), {'networks': results, 'metric_note': 'tie-grouped stepwise area under precision-recall (average precision); unknown reference edges treated as negatives'}


RESIDUE_MASS = dict(zip('ARNDCEQGHILKMFPSTWYV', [71.037114,156.101111,114.042927,115.026943,103.009185,129.042593,128.058578,57.021464,137.058912,113.084064,113.084064,128.094963,131.040485,147.068414,97.052764,87.032028,101.047679,186.079313,163.063329,99.068414]))
WATER, PROTON = 18.010565, 1.007276466621


def peptide_mass(sequence):
    require(isinstance(sequence, str) and 0 < len(sequence) <= 100 and set(sequence) <= set(RESIDUE_MASS), 'Peptide must use standard unmodified residues')
    return WATER + sum(RESIDUE_MASS[aa] for aa in sequence)


def peptide_score(module, cases):
    result, correct, confidence = [], [], []
    for c in cases:
        neutral_mass = float(c['precursor_mass'])
        prediction = module.decode_spectrum(array(c['peaks']).copy(), neutral_mass, int(c['charge']))
        require(isinstance(prediction, (list,tuple)) and len(prediction) == 2, 'Return (peptide, confidence)')
        peptide, conf = prediction
        conf = float(array([conf], (1,))[0])
        require(0 <= conf <= 1, 'Peptide confidence must lie in [0,1]')
        # Abstention is permitted and receives zero recall/precision credit.
        if peptide == '':
            require(conf == 0, 'Abstention confidence must be zero')
            hit, mass_ppm = False, None
        else:
            mass_ppm = abs(peptide_mass(peptide)-neutral_mass)/neutral_mass*1e6
            require(mass_ppm <= c.get('mass_tolerance_ppm', 50), 'Candidate peptide violates precursor mass tolerance')
            hit = peptide.replace('I','L') == c['peptide'].replace('I','L')
        result.append({'spectrum': c['id'], 'correct_IL_equivalent': bool(hit), 'mass_error_ppm': mass_ppm, 'abstained': peptide == ''})
        correct.append(bool(hit)); confidence.append(conf)
    order = np.argsort(-np.array(confidence), kind='stable')
    scores = np.asarray(confidence)[order]
    hits = np.asarray(correct)[order]
    # Stepwise precision-coverage area; ties grouped to remove arbitrary ordering.
    ends = np.r_[np.flatnonzero(np.diff(scores) != 0), len(scores)-1]
    precision = np.cumsum(hits)[ends]/(ends+1)
    widths = np.diff(np.r_[0,ends+1])/len(scores)
    area = float(np.sum(precision*widths))
    return area, {'spectra': result, 'exact_peptide_recall': float(np.mean(correct)), 'metric': 'stepwise precision-coverage area over all spectra, I/L equivalent; unmodified peptides only'}


SCORERS = {'B01': protein_score, 'B02': rna_score, 'B03': perturbation_score, 'B04': integration_score, 'B05': flux_score, 'B06': deconvolution_score, 'B07': phylogeny_score, 'B08': assembly_score, 'B09': denoising_score, 'B10': kinetics_score, 'B11': network_score, 'B12': peptide_score}


def evaluate(proposal, module, parameters):
    data = load_bundle(proposal, parameters)
    score, details = SCORERS[proposal](module, data['cases'])
    return score, {**details, 'source_kind': data['source_kind'], 'prepared_source_count': len(data['sources']), 'split_description': data['split_description'], 'fixture_validation': False}
