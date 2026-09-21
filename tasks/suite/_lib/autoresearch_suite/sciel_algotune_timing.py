"""SCiEL AlgoTune timing and speedup helpers. Original Apache-2.0 scoring shared across tasks."""

import concurrent.futures
import time
import numpy as np

def run_with_timeout(func, args=(), kwargs={}, timeout_seconds=30):
    """
    Run a function with a timeout using concurrent.futures

    Args:
        func: Function to run
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        timeout_seconds: Timeout in seconds

    Returns:
        Result of the function or raises TimeoutError
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")


def safe_convert(value):
    """Convert a value safely for evaluation"""
    try:
        if isinstance(value, (list, tuple)):
            return [safe_convert(v) for v in value]
        elif isinstance(value, np.ndarray):
            return value.tolist()
        else:
            return value
    except Exception:
        return value


def calculate_speedup(
    baseline_time_ms: float, evolved_time_ms: float, is_valid: bool
) -> Optional[float]:
    """
    Calculate speedup between baseline and evolved solution.

    Speedup = (Baseline Time) / (Evolved Time)
    Higher is better.

    Args:
        baseline_time_ms: Time taken by baseline implementation
        evolved_time_ms: Time taken by evolved solution
        is_valid: Whether the evolved solution is valid

    Returns:
        Speedup value or None if calculation is not possible
    """
    if not is_valid:
        return None

    if baseline_time_ms is None or baseline_time_ms <= 0:
        return None

    if evolved_time_ms is None:
        return None

    if evolved_time_ms <= 0:
        return float("inf")  # Infinite speedup for instant solution

    return baseline_time_ms / evolved_time_ms


def measure_baseline_performance(task_instance, problem, num_runs=3, warmup_runs=1):
    """
    Measure baseline performance using the original AlgoTune implementation.

    Args:
        task_instance: The AlgoTune task instance
        problem: Problem to solve
        num_runs: Number of timing runs
        warmup_runs: Number of warmup runs

    Returns:
        Dictionary with baseline timing results
    """
    try:
        # Warmup runs
        for _ in range(warmup_runs):
            try:
                task_instance.solve(problem)
            except Exception:
                pass  # Ignore warmup errors

        # Timing runs
        times = []
        for _ in range(num_runs):
            start_time = time.perf_counter()
            try:
                result = run_with_timeout(task_instance.solve, args=(problem,), timeout_seconds=30)
                end_time = time.perf_counter()
                if result is not None:
                    elapsed_ms = (end_time - start_time) * 1000
                    times.append(elapsed_ms)
            except Exception as e:
                print(f"Baseline run failed: {e}")
                continue

        if not times:
            return {
                "success": False,
                "error": "All baseline runs failed",
                "avg_time_ms": None,
                "min_time_ms": None,
                "std_time_ms": None,
            }

        return {
            "success": True,
            "avg_time_ms": float(np.mean(times)),
            "min_time_ms": float(np.min(times)),
            "std_time_ms": float(np.std(times)),
            "times": times,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "avg_time_ms": None,
            "min_time_ms": None,
            "std_time_ms": None,
        }


def measure_evolved_performance(program, problem, num_runs=3, warmup_runs=1, timeout_seconds=30):
    """
    Measure evolved solution performance.

    Args:
        program: The evolved program module
        problem: Problem to solve
        num_runs: Number of timing runs
        warmup_runs: Number of warmup runs
        timeout_seconds: Timeout per run

    Returns:
        Dictionary with evolved timing results
    """
    try:
        # Warmup runs
        for _ in range(warmup_runs):
            try:
                run_with_timeout(
                    program.run_solver, args=(problem,), timeout_seconds=timeout_seconds
                )
            except Exception:
                pass  # Ignore warmup errors

        # Timing runs
        times = []
        results = []
        for _ in range(num_runs):
            start_time = time.perf_counter()
            try:
                result = run_with_timeout(
                    program.run_solver, args=(problem,), timeout_seconds=timeout_seconds
                )
                end_time = time.perf_counter()
                elapsed_ms = (end_time - start_time) * 1000
                times.append(elapsed_ms)
                results.append(result)
            except TimeoutError:
                print(f"Evolved solution timed out after {timeout_seconds} seconds")
                continue
            except Exception as e:
                print(f"Evolved run failed: {e}")
                continue

        if not times:
            return {
                "success": False,
                "error": "All evolved runs failed",
                "avg_time_ms": None,
                "min_time_ms": None,
                "std_time_ms": None,
                "results": [],
            }

        return {
            "success": True,
            "avg_time_ms": float(np.mean(times)),
            "min_time_ms": float(np.min(times)),
            "std_time_ms": float(np.std(times)),
            "times": times,
            "results": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "avg_time_ms": None,
            "min_time_ms": None,
            "std_time_ms": None,
            "results": [],
        }
