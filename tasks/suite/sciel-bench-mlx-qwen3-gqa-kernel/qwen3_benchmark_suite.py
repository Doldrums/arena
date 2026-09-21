"""
Comprehensive Benchmark Suite for Qwen3-0.6B Metal Kernel Optimization
======================================================================

This benchmark suite tests various scenarios to establish baseline performance
and validate evolved Metal kernel optimizations. Tests the custom Metal kernel
discovered by OpenEvolve against MLX's standard attention implementation.

Target Model: mlx-community/Qwen3-0.6B-bf16
Target Hardware: Apple M4 24GB
Optimization: Custom Metal kernel for GQA attention (16 query heads : 8 KV heads)
Baseline: mx.fast.scaled_dot_product_attention
"""

import time
import json
import subprocess
import tempfile
import os
import sys
from typing import Dict, List, Tuple, Optional
import mlx.core as mx
import mlx.nn as nn
import numpy as np
from _qwen_benchmark_types import BenchmarkConfig, BenchmarkResult
from _qwen_benchmark_configs import BenchmarkConfigurations
from _qwen_benchmark_prompts import BenchmarkPrompts
from _qwen_benchmark_reporting import BenchmarkReporting


class Qwen3BenchmarkSuite(BenchmarkConfigurations, BenchmarkPrompts, BenchmarkReporting):

    """Comprehensive benchmark suite for Qwen3-0.6B Metal kernel optimization"""

    def __init__(
        self,
        model_path: str = "mlx-community/Qwen3-0.6B-bf16",
        hook_program_path: Optional[str] = None,
    ):
        self.model_path = model_path
        # When set, benchmarks will run via `mlx_lm_generate_with_hook.py` so that
        # the attention monkey-patch is applied inside the subprocess.
        self.hook_program_path = hook_program_path
        self.results: List[BenchmarkResult] = []

    def run_single_benchmark(self, config: BenchmarkConfig) -> BenchmarkResult:
        """Run a single benchmark configuration with proper warmup"""
        print(f"\n{'='*60}")
        print(f"Running: {config.name}")
        print(f"Description: {config.description}")
        print(f"Max tokens: {config.max_tokens}")
        print(f"{'='*60}")

        # Performance measurement parameters
        WARMUP_RUNS = 2  # Warmup runs to eliminate cold start effects
        MEASUREMENT_RUNS = 3  # Multiple measurement runs for reliability

        # Create temporary prompt file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(config.prompt)
            prompt_file = f.name

        try:
            # Build command
            if self.hook_program_path:
                wrapper_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "mlx_lm_generate_with_hook.py",
                )
                cmd = [
                    sys.executable,
                    "-W",
                    "ignore::RuntimeWarning",  # Suppress harmless import warnings
                    wrapper_path,
                    "--hook-program",
                    self.hook_program_path,
                    "--model",
                    self.model_path,
                    "--prompt",
                    config.prompt,
                    "--max-tokens",
                    str(config.max_tokens),
                ]
            else:
                cmd = [
                    sys.executable,
                    "-W",
                    "ignore::RuntimeWarning",  # Suppress harmless import warnings
                    "-m",
                    "mlx_lm.generate",
                    "--model",
                    self.model_path,
                    "--prompt",
                    config.prompt,
                    "--max-tokens",
                    str(config.max_tokens),
                ]

            # Clear MLX cache before starting
            print(f"🧹 Clearing MLX cache...")
            mx.clear_cache()

            # Warmup runs - don't measure these
            print(f"🔥 Running {WARMUP_RUNS} warmup runs to eliminate cold start effects...")
            for i in range(WARMUP_RUNS):
                try:
                    print(f"   Warmup run {i+1}/{WARMUP_RUNS}...")
                    warmup_result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if warmup_result.returncode != 0:
                        # Filter out harmless warnings from stderr
                        stderr_clean = "\n".join(
                            line
                            for line in warmup_result.stderr.split("\n")
                            if "RuntimeWarning" not in line and line.strip()
                        )
                        if stderr_clean:
                            print(
                                f"   ⚠️  Warmup run {i+1} failed (code {warmup_result.returncode}): {stderr_clean[:200]}..."
                            )
                        else:
                            print(
                                f"   ⚠️  Warmup run {i+1} failed (code {warmup_result.returncode})"
                            )
                    else:
                        print(f"   ✅ Warmup run {i+1} completed")

                    # Clear cache and add small delay between runs to reduce GPU contention
                    mx.clear_cache()
                    time.sleep(0.5)

                except subprocess.TimeoutExpired:
                    print(f"   ⏰ Warmup run {i+1} timed out")
                except Exception as e:
                    print(f"   ❌ Warmup run {i+1} error: {e}")

            print(f"📊 Running {MEASUREMENT_RUNS} measurement runs...")

            # Measurement runs
            successful_results = []
            for run_idx in range(MEASUREMENT_RUNS):
                try:
                    print(f"   Measurement run {run_idx+1}/{MEASUREMENT_RUNS}...")

                    # Clear cache before each measurement run for consistency
                    mx.clear_cache()
                    initial_memory = mx.get_active_memory()

                    # Run benchmark
                    start_time = time.perf_counter()
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    end_time = time.perf_counter()

                    if result.returncode != 0:
                        # Filter out harmless warnings from stderr
                        stderr_clean = "\n".join(
                            line
                            for line in result.stderr.split("\n")
                            if "RuntimeWarning" not in line and line.strip()
                        )
                        if stderr_clean:
                            print(
                                f"   ❌ Measurement run {run_idx+1} failed (code {result.returncode}): {stderr_clean[:200]}..."
                            )
                        else:
                            print(
                                f"   ❌ Measurement run {run_idx+1} failed (code {result.returncode})"
                            )
                        time.sleep(0.5)  # Small delay before retry
                        continue

                    # Parse output
                    parsed_result = self._parse_benchmark_output(
                        result.stdout, config, end_time - start_time
                    )

                    if parsed_result:
                        successful_results.append(parsed_result)
                        print(
                            f"   ✅ Run {run_idx+1}: {parsed_result.decode_tokens_per_sec:.1f} tokens/sec"
                        )
                    else:
                        print(f"   ❌ Run {run_idx+1}: Failed to parse output")

                except subprocess.TimeoutExpired:
                    print(f"   ⏰ Measurement run {run_idx+1} timed out")
                except Exception as e:
                    print(f"   ❌ Measurement run {run_idx+1} error: {e}")

            # Require at least 2 successful runs for reliable results
            if len(successful_results) < 2:
                print(
                    f"❌ Only {len(successful_results)}/{MEASUREMENT_RUNS} measurement runs succeeded"
                )
                print(f"❌ Need at least 2 successful runs for reliable results")
                raise RuntimeError(
                    f"Insufficient successful runs: {len(successful_results)}/{MEASUREMENT_RUNS}"
                )

            # Calculate statistics from multiple runs
            decode_speeds = [r.decode_tokens_per_sec for r in successful_results]
            prefill_speeds = [r.prefill_tokens_per_sec for r in successful_results]
            memories = [r.peak_memory_gb for r in successful_results]
            times = [r.total_time_sec for r in successful_results]

            # Use median for more robust results (less sensitive to outliers)
            final_result = BenchmarkResult(
                name=config.name,
                prompt_tokens=int(np.median([r.prompt_tokens for r in successful_results])),
                generated_tokens=int(np.median([r.generated_tokens for r in successful_results])),
                prefill_tokens_per_sec=float(np.median(prefill_speeds)),
                decode_tokens_per_sec=float(np.median(decode_speeds)),
                total_tokens_per_sec=float(
                    np.median([r.total_tokens_per_sec for r in successful_results])
                ),
                peak_memory_gb=float(np.median(memories)),
                total_time_sec=float(np.median(times)),
                prompt=config.prompt[:200] + "..." if len(config.prompt) > 200 else config.prompt,
                generated_text=successful_results[0].generated_text,  # Use first result's text
            )

            # Print final results with statistics
            print(f"\n📈 Final Results (median of {len(successful_results)} runs):")
            print(f"  Prompt tokens: {final_result.prompt_tokens}")
            print(f"  Generated tokens: {final_result.generated_tokens}")
            print(f"  Prefill speed: {final_result.prefill_tokens_per_sec:.2f} tokens/sec")
            print(
                f"  Decode speed: {final_result.decode_tokens_per_sec:.2f} tokens/sec (σ={np.std(decode_speeds):.2f})"
            )
            print(f"  Overall speed: {final_result.total_tokens_per_sec:.2f} tokens/sec")
            print(f"  Peak memory: {final_result.peak_memory_gb:.3f} GB")
            print(f"  Total time: {final_result.total_time_sec:.2f} seconds")

            if len(decode_speeds) > 1:
                print(
                    f"  Performance consistency: {np.std(decode_speeds)/np.mean(decode_speeds)*100:.1f}% CV"
                )

            return final_result

        finally:
            # Clean up
            if os.path.exists(prompt_file):
                os.unlink(prompt_file)

    def _parse_benchmark_output(
        self, stdout: str, config: BenchmarkConfig, total_time: float
    ) -> Optional[BenchmarkResult]:
        """Parse mlx-lm output to extract performance metrics"""
        output_lines = stdout.strip().split("\n")

        # Find the generated text (between ========== markers)
        generated_text = ""
        in_generation = False
        prompt_tokens = 0
        generation_tokens = 0
        prompt_speed = 0.0
        generation_speed = 0.0
        peak_memory_str = ""

        for line in output_lines:
            if line.strip() == "==========":
                in_generation = not in_generation
            elif in_generation:
                generated_text += line + "\n"
            elif "Prompt:" in line and "tokens-per-sec" in line:
                # Parse: "Prompt: 13 tokens, 310.367 tokens-per-sec"
                parts = line.split(",")
                prompt_tokens = int(parts[0].split(":")[1].strip().split()[0])
                prompt_speed = float(parts[1].strip().split()[0])
            elif "Generation:" in line and "tokens-per-sec" in line:
                # Parse: "Generation: 468 tokens, 69.860 tokens-per-sec"
                parts = line.split(",")
                generation_tokens = int(parts[0].split(":")[1].strip().split()[0])
                generation_speed = float(parts[1].strip().split()[0])
            elif "Peak memory:" in line:
                peak_memory_str = line.split(":")[1].strip()

        # Parse peak memory
        peak_memory_gb = 0.0
        if peak_memory_str:
            if "GB" in peak_memory_str:
                peak_memory_gb = float(peak_memory_str.replace("GB", "").strip())
            elif "MB" in peak_memory_str:
                peak_memory_gb = float(peak_memory_str.replace("MB", "").strip()) / 1024

        # Validate we got meaningful results
        if generation_tokens == 0 or generation_speed == 0:
            return None

        # Calculate overall tokens per second
        total_tokens_per_sec = generation_tokens / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=config.name,
            prompt_tokens=prompt_tokens,
            generated_tokens=generation_tokens,
            prefill_tokens_per_sec=prompt_speed,
            decode_tokens_per_sec=generation_speed,
            total_tokens_per_sec=total_tokens_per_sec,
            peak_memory_gb=peak_memory_gb,
            total_time_sec=total_time,
            prompt=config.prompt[:200] + "..." if len(config.prompt) > 200 else config.prompt,
            generated_text=(
                generated_text.strip()[:200] + "..."
                if len(generated_text.strip()) > 200
                else generated_text.strip()
            ),
        )


def main():
    """Run the complete benchmark suite"""
    print("Running Qwen3-0.6B Comprehensive Benchmark Suite")
    print("Ensure mlx-lm is installed: pip install mlx-lm")
    print("Target: Validate custom Metal kernel optimization performance")

    benchmark_suite = Qwen3BenchmarkSuite()
    results = benchmark_suite.run_full_benchmark_suite()
    benchmark_suite.print_summary_table()

    print(f"\n{'='*80}")
    print("Benchmark Suite Complete!")
    print("These results will serve as baseline for Metal kernel optimization validation.")
    print("Target: Improve decode speed by 10%+ through evolved custom Metal kernels")
    print(f"{'='*80}")

    return results


if __name__ == "__main__":
    main()
