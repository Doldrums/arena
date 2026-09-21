"""Read-only journal compatibility extracted from sciel.knowledge_base.eligibility.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

def validate_output_observation(value, *, source_sha256, metric, island, evaluation, status):
    from .output_novelty import validate_verdict
    verdict = validate_verdict(value, source_sha256=source_sha256)
    if source_sha256 is None or evaluation is None or status not in ('evaluated', 'eval_failed'):
        raise ValueError('output novelty requires a source-bound returned evaluation')
    binding = verdict['binding']
    if ((metric or {}).get('task_hash') not in (None, binding['task_hash'])
            or island not in (None, binding['island_id'])):
        raise ValueError('output verdict differs from research task/island')
    if verdict['identity'] is not None:
        stage = verdict['identity']['scope']['stage']
        if (not evaluation['ok'] or status != 'evaluated'
                or stage['reached'] != evaluation['reached']
                or stage['confirmed'] != evaluation['confirmed']):
            raise ValueError('output identity differs from successful selected evaluation')
        geometry = evaluation.get('native_geometry')
        if geometry is not None and verdict['identity']['scope']['adapter'] == 'native-circle-geometry/1':
            from .output_identity import digest
            identity = verdict['identity']
            representation = identity['scope']['representation']
            confirmation = geometry['confirmation']
            if (identity['output_sha256'] != geometry['numeric_sha256']
                    or identity['scope']['evaluator_sha256'] != geometry['evaluator_sha256']
                    or identity['evidence']['invocation_id'] != geometry['invocation_id']
                    or identity['evidence']['artifact_sha256'] != digest(geometry)
                    or identity['evidence']['selected_trial'] != (confirmation['selected_trial'] if confirmation else None)
                    or stage['confirmation'] != ({key: confirmation[key] for key in ('trials', 'selection')}
                                                 if confirmation else None)
                    or any(representation[key] != geometry[key] for key in ('centers_dtype', 'radii_dtype'))):
                raise ValueError('output identity differs from recorded native geometry')
    return verdict
