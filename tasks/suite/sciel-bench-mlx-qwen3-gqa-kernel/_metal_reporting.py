"""MetalReporting implementation for the bundled MLX task."""
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


class MetalReporting:

    def _safe_calculate_improvement(self, new_value: float, old_value: float) -> float:
        """Safely calculate percentage improvement with bounds"""
        if old_value <= 0 or np.isnan(old_value) or np.isnan(new_value):
            return 0.0

        improvement = (new_value - old_value) / old_value * 100

        # Clamp extreme values for safety
        return max(-100.0, min(1000.0, improvement))

    def _calculate_safety_score(self) -> float:
        """Calculate overall safety score based on error statistics"""
        total_operations = (
            self.metal_command_buffer_errors
            + self.metal_memory_violations
            + self.metal_compilation_errors
            + self.gpu_resource_errors
            + 10  # Assumed successful operations
        )

        error_rate = self.total_metal_errors / total_operations
        safety_score = max(0.0, 1.0 - error_rate) * 100

        return safety_score

    def _calculate_safety_adjusted_score(
        self, performance_analysis: Dict[str, Any], correctness: float
    ) -> float:
        """Calculate final score adjusted for safety"""
        if correctness < 0.90:
            return -1000.0

        comparison = performance_analysis["comparison_summary"]
        avg_improvement = comparison["avg_decode_improvement_pct"]
        memory_change = comparison["memory_change_gb"]
        success_rate = comparison["num_benchmarks_improved"] / max(
            1, comparison["total_benchmarks"]
        )
        safety_score = comparison["safety_score"]

        # Enhanced score components
        performance_score = avg_improvement * 3  # Primary component
        memory_bonus = max(0, -memory_change * 10)  # Bonus for memory reduction
        consistency_bonus = success_rate * 10  # Bonus for consistent improvements
        correctness_bonus = correctness * 5  # Bonus for correctness
        safety_bonus = (safety_score / 100) * 5  # Bonus for safety

        # Penalty for excessive errors
        error_penalty = min(self.total_metal_errors * 2, 20)  # Cap penalty

        final_score = (
            performance_score
            + memory_bonus
            + consistency_bonus
            + correctness_bonus
            + safety_bonus
            - error_penalty
        )

        print(f"  🎯 Safety-adjusted score breakdown:")
        print(f"    • Performance: {avg_improvement:.2f}% × 3 = {performance_score:.2f}")
        print(f"    • Memory: {memory_bonus:.2f}")
        print(f"    • Consistency: {success_rate:.2f} × 10 = {consistency_bonus:.2f}")
        print(f"    • Correctness: {correctness:.3f} × 5 = {correctness_bonus:.2f}")
        print(f"    • Safety: {safety_score:.1f}/100 × 5 = {safety_bonus:.2f}")
        print(f"    • Error penalty: -{error_penalty:.2f}")
        print(f"    • Final score: {final_score:.2f}")

        return final_score

    def _generate_comprehensive_summary(
        self, performance_analysis: Dict[str, Any], correctness: float
    ) -> str:
        """Generate comprehensive evaluation summary with safety info"""
        comparison = performance_analysis["comparison_summary"]
        metrics = performance_analysis["aggregate_metrics"]

        avg_improvement = comparison["avg_decode_improvement_pct"]
        current_decode = metrics["avg_decode_speed"]
        baseline_decode = self.baseline_metrics["avg_decode_speed"]
        safety_score = comparison["safety_score"]

        summary = f"""Bulletproof Custom GQA Implementation Results:
• Decode Speed: {current_decode:.1f} tokens/sec (baseline: {baseline_decode:.1f})
• Improvement: {avg_improvement:+.1f}%
• Memory Usage: {metrics['avg_memory_gb']:.2f} GB
• Correctness: {correctness:.1%}
• Safety Score: {safety_score:.1f}/100
• Tests Passed: {metrics['num_successful_tests']}/{len(self._get_safe_benchmark_configs())}
• Benchmarks Improved: {comparison['num_benchmarks_improved']}/{comparison['total_benchmarks']}
• Metal Errors Handled: {self.total_metal_errors}"""

        if self.total_metal_errors == 0:
            summary += "\n🛡️  PERFECT SAFETY: No Metal kernel errors"
        elif self.total_metal_errors < 3:
            summary += f"\n🛡️  GOOD SAFETY: {self.total_metal_errors} Metal errors handled"
        else:
            summary += f"\n⚠️  SAFETY CONCERNS: {self.total_metal_errors} Metal errors handled"

        if avg_improvement >= 15:
            summary += "\n🎯 EXCELLENT: 15%+ improvement achieved!"
        elif avg_improvement >= 10:
            summary += "\n🚀 STRONG IMPROVEMENT: 10%+ speedup"
        elif avg_improvement >= 5:
            summary += "\n✅ GOOD IMPROVEMENT: 5%+ speedup"
        elif avg_improvement > 0:
            summary += "\n📈 MINOR IMPROVEMENT: Some speedup achieved"
        else:
            summary += "\n⚠️  NO IMPROVEMENT: Performance regression"

        return summary

    def _get_comprehensive_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            "metal_command_buffer_errors": self.metal_command_buffer_errors,
            "metal_memory_violations": self.metal_memory_violations,
            "metal_compilation_errors": self.metal_compilation_errors,
            "gpu_resource_errors": self.gpu_resource_errors,
            "total_metal_errors": self.total_metal_errors,
            "successful_fallbacks": self.successful_fallbacks,
            "retry_attempts_used": self.retry_attempts_used,
            "safety_score": self._calculate_safety_score(),
            "error_breakdown": {
                "command_buffer_pct": (
                    self.metal_command_buffer_errors / max(1, self.total_metal_errors)
                )
                * 100,
                "memory_violation_pct": (
                    self.metal_memory_violations / max(1, self.total_metal_errors)
                )
                * 100,
                "compilation_error_pct": (
                    self.metal_compilation_errors / max(1, self.total_metal_errors)
                )
                * 100,
                "resource_error_pct": (self.gpu_resource_errors / max(1, self.total_metal_errors))
                * 100,
            },
        }

    def _print_bulletproof_evaluation_results(self, result: Dict[str, Any]):
        """Print comprehensive bulletproof evaluation results"""
        print(f"\n{'🛡️ '*25}")
        print(f"{'🛡️  BULLETPROOF EVALUATION RESULTS  🛡️':^100}")
        print(f"{'🛡️ '*25}")

        if result["success"]:
            performance = result["performance_metrics"]
            comparison = result["baseline_comparison"]
            safety_stats = result["metal_safety_statistics"]

            print(f"📊 FINAL SCORE: {result['final_score']:.2f}")
            print(f"")
            print(f"📈 PERFORMANCE COMPARISON:")
            print(f"  • Average Decode Speed: {performance['avg_decode_speed']:.1f} tokens/sec")
            print(
                f"  • Baseline Decode Speed: {self.baseline_metrics['avg_decode_speed']:.1f} tokens/sec"
            )
            print(f"  • Average Improvement: {comparison['avg_decode_improvement_pct']:+.1f}%")
            print(
                f"  • Absolute Improvement: {comparison['avg_decode_improvement_absolute']:+.1f} tokens/sec"
            )
            print(f"")
            print(f"🛡️  SAFETY STATISTICS:")
            print(f"  • Safety Score: {safety_stats['safety_score']:.1f}/100")
            print(f"  • Command Buffer Errors: {safety_stats['metal_command_buffer_errors']}")
            print(f"  • Memory Violations: {safety_stats['metal_memory_violations']}")
            print(f"  • Total Metal Errors: {safety_stats['total_metal_errors']}")
            print(f"  • Retry Attempts Used: {safety_stats['retry_attempts_used']}")
            print(f"")
            print(f"💾 MEMORY USAGE:")
            print(f"  • Average Memory: {performance['avg_memory_gb']:.2f} GB")
            print(f"  • Baseline Memory: {self.baseline_metrics['avg_memory_gb']:.2f} GB")
            print(f"  • Memory Change: {comparison['memory_change_gb']:+.2f} GB")
            print(f"")
            print(f"✓ RELIABILITY:")
            print(f"  • Correctness Score: {result['correctness_score']:.1%}")
            print(f"  • Successful Tests: {performance['num_successful_tests']}")
            print(
                f"  • Benchmarks Improved: {comparison['num_benchmarks_improved']}/{comparison['total_benchmarks']}"
            )

            if comparison["target_achieved"]:
                print(f"\n🎯 TARGET ACHIEVED: Significant improvement with safety!")

            if safety_stats["total_metal_errors"] == 0:
                print(f"\n🛡️  PERFECT EXECUTION: No Metal kernel errors encountered!")

        else:
            print(f"❌ EVALUATION FAILED (SAFELY)")
            print(f"📋 Error: {result.get('error', 'Unknown error')}")
            safety_stats = result.get("metal_safety_statistics", {})
            print(f"🛡️  Metal Errors Handled: {safety_stats.get('total_metal_errors', 0)}")

        print(f"{'🛡️ '*25}")

    def _create_comprehensive_failure_result(self, error_message: str) -> Dict[str, Any]:
        """Create comprehensive failure result with full error statistics"""
        return {
            "success": False,
            "final_score": -1000.0,
            "combined_score": -1000.0,
            "error": error_message,
            "performance_metrics": {},
            "correctness_score": 0.0,
            "summary": f"Bulletproof evaluation failed (safely): {error_message}",
            "metal_safety_statistics": self._get_comprehensive_error_statistics(),
            "safety_validation": {"success": False, "error": error_message},
        }

    def _result_to_dict(self, result: BenchmarkResult) -> Dict:
        """Convert BenchmarkResult to dictionary"""
        return {
            "name": result.name,
            "decode_tokens_per_sec": result.decode_tokens_per_sec,
            "prefill_tokens_per_sec": result.prefill_tokens_per_sec,
            "peak_memory_gb": result.peak_memory_gb,
            "generated_tokens": result.generated_tokens,
            "total_time_sec": result.total_time_sec,
        }
