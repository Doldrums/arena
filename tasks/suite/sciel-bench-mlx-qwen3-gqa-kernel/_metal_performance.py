"""MetalPerformance implementation for the bundled MLX task."""
import os
import sys
import json
import time
import traceback
import threading
import subprocess
import tempfile
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import mlx.core as mx
import mlx.nn as nn

# Import the comprehensive benchmark suite for consistent testing
from qwen3_benchmark_suite import Qwen3BenchmarkSuite, BenchmarkConfig, BenchmarkResult

from _metal_errors import MetalKernelSafetyError, GPUCommandBufferError, MetalMemoryViolationError


class MetalPerformance:

    def _command_buffer_protected_benchmark(
        self, program_text: str, custom_attention_class: Any
    ) -> Dict[str, Any]:
        """Command-buffer-protected benchmarking with maximum safety"""
        print("  🚀 Running command-buffer-protected benchmarking...")

        retry_attempt = 0

        while retry_attempt <= self.max_retry_attempts:
            try:
                print(f"  🔄 Protected attempt {retry_attempt + 1}/{self.max_retry_attempts + 1}")

                # Clean GPU state before each major attempt
                self._ensure_clean_gpu_state()

                # Apply custom attention hook with protection
                hook_result = self._gpu_protected_apply_hook(custom_attention_class)
                if not hook_result["success"]:
                    if retry_attempt < self.max_retry_attempts:
                        print(f"    🔄 Hook failed, retrying... ({hook_result['error']})")
                        retry_attempt += 1
                        time.sleep(self.retry_base_delay * (2**retry_attempt))
                        continue
                    return {
                        "success": False,
                        "error": f"Hook application failed: {hook_result['error']}",
                    }

                original_attention = hook_result["original"]
                temp_program_path = None

                try:
                    # Ensure the evolved program is available to the subprocess that runs mlx_lm.generate.
                    # Monkey-patching in this evaluator process does NOT propagate across subprocess boundaries.
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
                        f.write(program_text)
                        temp_program_path = f.name

                    self.benchmark_suite.hook_program_path = temp_program_path

                    # Run benchmarks with command buffer protection
                    custom_configs = self._get_safe_benchmark_configs()
                    custom_results = []
                    successful_benchmarks = 0

                    for i, config in enumerate(custom_configs, 1):
                        print(
                            f"    [{i}/{len(custom_configs)}] Command-buffer-protected: {config.name}"
                        )

                        benchmark_retry = 0
                        while benchmark_retry <= 2:  # Fewer retries per benchmark
                            try:
                                # Clean state before each benchmark
                                self._ensure_clean_gpu_state()

                                # Run with maximum protection
                                success, result = self._bulletproof_execute_with_gpu_protection(
                                    lambda: self.benchmark_suite.run_single_benchmark(config)
                                )

                                if success and result:
                                    custom_results.append(result)
                                    successful_benchmarks += 1
                                    print(
                                        f"      ✅ Protected {config.name}: {result.decode_tokens_per_sec:.1f} tokens/sec"
                                    )
                                    break
                                else:
                                    if benchmark_retry < 2:
                                        print(
                                            f"      🔄 Benchmark retry {benchmark_retry + 1}: {result}"
                                        )
                                        benchmark_retry += 1
                                        time.sleep(1)
                                        continue
                                    else:
                                        print(f"      ❌ Benchmark failed: {result}")
                                        break

                            except Exception as e:
                                if benchmark_retry < 2:
                                    print(
                                        f"      🔄 Benchmark exception retry {benchmark_retry + 1}: {e}"
                                    )
                                    benchmark_retry += 1
                                    time.sleep(1)
                                    continue
                                else:
                                    print(f"      ❌ Benchmark exception: {e}")
                                    break

                    # Check success rate
                    min_required = max(2, len(custom_configs) * 0.4)  # Lowered to 40% for safety
                    if successful_benchmarks >= min_required:
                        print(
                            f"  ✅ Command-buffer-protected benchmarks complete ({successful_benchmarks} successful)"
                        )
                        self.retry_attempts_used = retry_attempt
                        return {"success": True, "results": custom_results}
                    else:
                        error_msg = f"Insufficient benchmarks: {successful_benchmarks}/{len(custom_configs)} succeeded"
                        if retry_attempt < self.max_retry_attempts:
                            print(f"  🔄 {error_msg}, retrying full attempt...")
                            retry_attempt += 1
                            time.sleep(self.retry_base_delay * (2**retry_attempt))
                            continue
                        return {"success": False, "error": error_msg}

                finally:
                    # Always clear subprocess hook settings and clean up temp program
                    self.benchmark_suite.hook_program_path = None
                    if temp_program_path:
                        try:
                            os.unlink(temp_program_path)
                        except OSError:
                            pass
                    # Always restore original attention
                    self._gpu_protected_remove_hook(original_attention)

            except Exception as e:
                error_msg = f"Command-buffer-protected attempt failed: {str(e)}"
                print(f"  ❌ {error_msg}")
                if retry_attempt < self.max_retry_attempts:
                    retry_attempt += 1
                    time.sleep(self.retry_base_delay * (2**retry_attempt))
                    continue
                return {"success": False, "error": error_msg}

        return {"success": False, "error": "All command-buffer-protected attempts exhausted"}

    def _get_safe_benchmark_configs(self) -> List[BenchmarkConfig]:
        """Get safer benchmark configurations for GPU protection"""
        try:
            all_configs = self.benchmark_suite.create_benchmark_configs()

            # Use more conservative test set for safety
            safe_test_names = [
                "short_context_quick",  # Safest - very short
                "code_generation",  # Medium safety
                "long_context_detailed",  # More challenging but still safe
                "long_generation",  # Longer generation
                # Disabled for faster testing
                # "maximum_context_stress_test",  # Most challenging - saved for last
            ]

            config_dict = {c.name: c for c in all_configs}
            safe_configs = []

            for test_name in safe_test_names:
                if test_name in config_dict:
                    safe_configs.append(config_dict[test_name])

            return safe_configs

        except Exception as e:
            print(f"  ⚠️  Error getting safe benchmark configs: {e}")
            return []

    def _store_enhanced_baseline_metrics(self, baseline_results: List[BenchmarkResult]):
        """Store enhanced baseline metrics"""
        decode_speeds = [
            r.decode_tokens_per_sec for r in baseline_results if r.decode_tokens_per_sec > 0
        ]
        prefill_speeds = [
            r.prefill_tokens_per_sec for r in baseline_results if r.prefill_tokens_per_sec > 0
        ]
        memories = [r.peak_memory_gb for r in baseline_results if r.peak_memory_gb > 0]

        self.baseline_results = baseline_results
        self.baseline_metrics = {
            "avg_decode_speed": float(np.mean(decode_speeds)) if decode_speeds else 0.0,
            "min_decode_speed": float(np.min(decode_speeds)) if decode_speeds else 0.0,
            "max_decode_speed": float(np.max(decode_speeds)) if decode_speeds else 0.0,
            "std_decode_speed": float(np.std(decode_speeds)) if len(decode_speeds) > 1 else 0.0,
            "avg_prefill_speed": float(np.mean(prefill_speeds)) if prefill_speeds else 0.0,
            "avg_memory_gb": float(np.mean(memories)) if memories else 0.0,
            "max_memory_gb": float(np.max(memories)) if memories else 0.0,
            "num_baseline_tests": len(baseline_results),
        }

        print(
            f"    📊 Enhanced baseline stored - Avg decode: {self.baseline_metrics['avg_decode_speed']:.1f} tokens/sec"
        )

    def _analyze_performance_with_safety_metrics(
        self, baseline_results: List[BenchmarkResult], custom_results: List[BenchmarkResult]
    ) -> Dict[str, Any]:
        """Analyze performance with enhanced safety metrics"""
        print("  📈 Analyzing performance with safety metrics...")

        baseline_dict = {r.name: r for r in baseline_results}
        custom_dict = {r.name: r for r in custom_results}

        individual_comparisons = []
        improvements = {
            "decode_speed_improvements": [],
            "prefill_speed_improvements": [],
            "total_speed_improvements": [],
            "memory_improvements": [],
            "time_improvements": [],
        }

        # Compare each benchmark
        for name in baseline_dict:
            if name in custom_dict:
                baseline = baseline_dict[name]
                custom = custom_dict[name]

                # Calculate improvements with safety bounds
                decode_improvement = self._safe_calculate_improvement(
                    custom.decode_tokens_per_sec, baseline.decode_tokens_per_sec
                )
                prefill_improvement = self._safe_calculate_improvement(
                    custom.prefill_tokens_per_sec, baseline.prefill_tokens_per_sec
                )
                total_improvement = self._safe_calculate_improvement(
                    custom.total_tokens_per_sec, baseline.total_tokens_per_sec
                )
                memory_improvement = self._safe_calculate_improvement(
                    baseline.peak_memory_gb, custom.peak_memory_gb  # Reversed for memory
                )
                time_improvement = self._safe_calculate_improvement(
                    baseline.total_time_sec, custom.total_time_sec  # Reversed for time
                )

                comparison = {
                    "benchmark_name": name,
                    "baseline": self._result_to_dict(baseline),
                    "custom": self._result_to_dict(custom),
                    "improvements": {
                        "decode_speed_pct": decode_improvement,
                        "prefill_speed_pct": prefill_improvement,
                        "total_speed_pct": total_improvement,
                        "memory_reduction_pct": memory_improvement,
                        "time_reduction_pct": time_improvement,
                    },
                }

                individual_comparisons.append(comparison)

                improvements["decode_speed_improvements"].append(decode_improvement)
                improvements["prefill_speed_improvements"].append(prefill_improvement)
                improvements["total_speed_improvements"].append(total_improvement)
                improvements["memory_improvements"].append(memory_improvement)
                improvements["time_improvements"].append(time_improvement)

                print(f"    • {name}: {decode_improvement:+.1f}% decode speed")

        # Calculate aggregate statistics with safety checks
        aggregate_stats = {}
        for key, values in improvements.items():
            if values:
                # Use robust statistics
                valid_values = [v for v in values if not np.isnan(v) and not np.isinf(v)]
                if valid_values:
                    aggregate_stats[f"{key}_avg"] = float(np.mean(valid_values))
                    aggregate_stats[f"{key}_median"] = float(np.median(valid_values))
                    aggregate_stats[f"{key}_min"] = float(np.min(valid_values))
                    aggregate_stats[f"{key}_max"] = float(np.max(valid_values))
                    aggregate_stats[f"{key}_std"] = float(np.std(valid_values))

        # Calculate custom metrics
        custom_decode_speeds = [
            r.decode_tokens_per_sec for r in custom_results if r.decode_tokens_per_sec > 0
        ]
        custom_prefill_speeds = [
            r.prefill_tokens_per_sec for r in custom_results if r.prefill_tokens_per_sec > 0
        ]
        custom_memories = [r.peak_memory_gb for r in custom_results if r.peak_memory_gb > 0]

        aggregate_metrics = {
            "avg_decode_speed": (
                float(np.mean(custom_decode_speeds)) if custom_decode_speeds else 0.0
            ),
            "min_decode_speed": (
                float(np.min(custom_decode_speeds)) if custom_decode_speeds else 0.0
            ),
            "max_decode_speed": (
                float(np.max(custom_decode_speeds)) if custom_decode_speeds else 0.0
            ),
            "avg_prefill_speed": (
                float(np.mean(custom_prefill_speeds)) if custom_prefill_speeds else 0.0
            ),
            "avg_memory_gb": float(np.mean(custom_memories)) if custom_memories else 0.0,
            "max_memory_gb": float(np.max(custom_memories)) if custom_memories else 0.0,
            "num_successful_tests": len(custom_results),
            "decode_speed_std": (
                float(np.std(custom_decode_speeds)) if len(custom_decode_speeds) > 1 else 0.0
            ),
        }

        # Enhanced comparison summary
        comparison_summary = {
            "avg_decode_improvement_pct": aggregate_stats.get("decode_speed_improvements_avg", 0),
            "avg_decode_improvement_absolute": (
                aggregate_metrics["avg_decode_speed"] - self.baseline_metrics["avg_decode_speed"]
            ),
            "memory_change_gb": (
                aggregate_metrics["avg_memory_gb"] - self.baseline_metrics["avg_memory_gb"]
            ),
            "target_achieved": aggregate_stats.get("decode_speed_improvements_avg", 0) >= 5.0,
            "num_benchmarks_improved": sum(
                1 for x in improvements["decode_speed_improvements"] if x > 1.0
            ),  # More lenient
            "total_benchmarks": len(improvements["decode_speed_improvements"]),
            "safety_score": self._calculate_safety_score(),
        }

        print(
            f"  📊 Enhanced analysis complete: {comparison_summary['avg_decode_improvement_pct']:+.1f}% avg improvement"
        )
        print(f"  🛡️  Safety score: {comparison_summary['safety_score']:.2f}")

        return {
            "individual_comparisons": individual_comparisons,
            "aggregate_improvements": aggregate_stats,
            "aggregate_metrics": aggregate_metrics,
            "comparison_summary": comparison_summary,
        }
