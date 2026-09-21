"""``start_ale_bench_session`` as used by the EvoX (skydiscover) ALE-Bench evaluators.

The EvoX evaluators import this helper from a package that is not in the
published repository; this shim starts a session with the public ``ale_bench``
API (SakanaAI/ALE-Bench) and retries a few times, which is all the evaluators
rely on. ALE-Bench itself needs a running Docker daemon.
"""
import time

import ale_bench


def start_ale_bench_session(problem_id, lite_version=True, num_workers=4, retries=3, **options):
    last = None
    for attempt in range(retries):
        try:
            return ale_bench.start(problem_id=problem_id, lite_version=lite_version, num_workers=num_workers, **options)
        except Exception as error:  # noqa: BLE001
            last = error
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not start ALE-Bench session for {problem_id}: {last}")
