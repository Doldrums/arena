"""Phylogenetic tree parsing and independent likelihood evaluation."""
from __future__ import annotations

from .science_biology_expansion import (
    CandidateError,
    np,
    re,
    require,
)

# A small independent Felsenstein-pruning likelihood, deliberately fixed to JC69.
# It does not invoke the candidate, RAxML, or a candidate-supplied score.
def parse_newick(text):
    require(isinstance(text, str) and len(text) < 200000, 'Expected bounded Newick string')
    tokens = re.findall(r'[^\s(),:;]+|[(),:;]', text)
    require(''.join(tokens) == re.sub(r'\s+', '', text), 'Invalid Newick characters')
    pos = 0
    def node():
        nonlocal pos
        require(pos < len(tokens), 'Truncated Newick')
        children, name = [], None
        if tokens[pos] == '(':
            pos += 1
            children.append(node())
            while pos < len(tokens) and tokens[pos] == ',':
                pos += 1; children.append(node())
            require(pos < len(tokens) and tokens[pos] == ')' and len(children) >= 2, 'Invalid internal Newick node')
            pos += 1
            if pos < len(tokens) and tokens[pos] not in ':,);':
                pos += 1  # optional internal support label
        else:
            require(tokens[pos] not in '(),:;', 'Missing taxon label')
            name = tokens[pos]; pos += 1
        length = 0.0
        if pos < len(tokens) and tokens[pos] == ':':
            pos += 1
            require(pos < len(tokens), 'Missing branch length')
            try: length = float(tokens[pos])
            except ValueError: raise CandidateError('Invalid branch length')
            pos += 1
            require(np.isfinite(length) and 0 <= length <= 100, 'Branch length outside [0,100]')
        return name, length, children
    tree = node()
    require(pos == len(tokens)-1 and tokens[pos] == ';', 'Tree must end with one semicolon')
    return tree


def tree_log_likelihood(alignment, newick):
    names = list(alignment)
    require(len(names) >= 2 and len(set(map(len, alignment.values()))) == 1, 'Invalid alignment')
    sites = len(alignment[names[0]])
    require(sites > 0, 'Empty alignment')
    ambiguous = {'A':'A','C':'C','G':'G','T':'T','U':'T','N':'ACGT','?':'ACGT','-':'ACGT','R':'AG','Y':'CT','S':'CG','W':'AT','K':'GT','M':'AC','B':'CGT','D':'AGT','H':'ACT','V':'ACG'}
    leaves = []
    def visit(node):
        name, length, children = node
        if not children:
            require(name in alignment, 'Unknown taxon in candidate tree')
            leaves.append(name)
            sequence = alignment[name].upper()
            require(set(sequence) <= set(ambiguous), 'Unsupported alignment characters')
            partial = np.array([[b in ambiguous[c] for b in 'ACGT'] for c in sequence], float)
            scales = np.zeros(sites)
        else:
            partial, scales = np.ones((sites, 4)), np.zeros(sites)
            for child in children:
                p, scale = visit(child)
                edge = child[1]
                decay = np.exp(-4*edge/3)
                transition = np.full((4, 4), (1-decay)/4)
                np.fill_diagonal(transition, (1+3*decay)/4)
                partial *= p @ transition.T
                scales += scale
                factor = np.max(partial, axis=1)
                require(np.all(factor > 0), 'Tree gives zero likelihood for alignment')
                partial /= factor[:, None]
                scales += np.log(factor)
        return partial, scales
    partial, scales = visit(parse_newick(newick))
    require(sorted(leaves) == sorted(names), 'Tree must contain each input taxon exactly once')
    return float(np.sum(np.log(partial.mean(axis=1)) + scales))


def phylogeny_score(module, cases):
    results = []
    for c in cases:
        alignment = dict(c['alignment'])
        newick = module.infer_tree(dict(alignment), {'name': 'JC69', 'rate': 1.0}, c.get('budget', 60))
        ll = tree_log_likelihood(alignment, newick)
        nll = -ll / len(next(iter(alignment.values())))
        results.append({'alignment': c['id'], 'negative_log_likelihood_per_site': nll, 'taxa': len(alignment), 'sites': len(next(iter(alignment.values())))})
    return float(np.mean([x['negative_log_likelihood_per_site'] for x in results])), {'alignments': results, 'model': 'JC69; no true empirical topology claim; wall deadline enforced by outer runtime'}
