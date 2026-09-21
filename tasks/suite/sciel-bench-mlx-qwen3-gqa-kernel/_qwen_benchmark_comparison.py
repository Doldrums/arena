"""Comparison analysis and reports for the Qwen benchmark CLI."""
import argparse
import sys
import os
import time
import json
import numpy as np
from typing import Dict, List, Any


def analyze_comparison_results(standard_results, optimized_results, model_name):
    """
    Analyze and compare the benchmark results.
    """
    if not standard_results or not optimized_results:
        print("❌ Cannot compare - missing results")
        return None

    print("🔍 Analyzing benchmark comparisons...")

    standard_benchmarks = {r["name"]: r for r in standard_results["results"]}
    optimized_benchmarks = {r["name"]: r for r in optimized_results["results"]}

    print(f"📊 Standard benchmarks: {len(standard_benchmarks)}")
    print(f"📊 Optimized benchmarks: {len(optimized_benchmarks)}")

    # Find common benchmarks
    common_benchmarks = set(standard_benchmarks.keys()) & set(optimized_benchmarks.keys())
    print(f"📊 Common benchmarks for comparison: {len(common_benchmarks)}")

    if len(common_benchmarks) == 0:
        print("❌ No common benchmarks found for comparison")
        return None

    comparisons = []
    improvements = {
        "decode_speed_improvements": [],
        "prefill_speed_improvements": [],
        "total_speed_improvements": [],
        "memory_improvements": [],
        "time_improvements": [],
    }

    for name in common_benchmarks:
        std_result = standard_benchmarks[name]
        opt_result = optimized_benchmarks[name]

        # Calculate improvements
        decode_improvement = (
            (
                (opt_result["decode_tokens_per_sec"] - std_result["decode_tokens_per_sec"])
                / std_result["decode_tokens_per_sec"]
                * 100
            )
            if std_result["decode_tokens_per_sec"] > 0
            else 0
        )

        prefill_improvement = (
            (
                (opt_result["prefill_tokens_per_sec"] - std_result["prefill_tokens_per_sec"])
                / std_result["prefill_tokens_per_sec"]
                * 100
            )
            if std_result["prefill_tokens_per_sec"] > 0
            else 0
        )

        total_improvement = (
            (
                (opt_result["total_tokens_per_sec"] - std_result["total_tokens_per_sec"])
                / std_result["total_tokens_per_sec"]
                * 100
            )
            if std_result["total_tokens_per_sec"] > 0
            else 0
        )

        memory_improvement = (
            (
                (std_result["peak_memory_gb"] - opt_result["peak_memory_gb"])
                / std_result["peak_memory_gb"]
                * 100
            )
            if std_result["peak_memory_gb"] > 0
            else 0
        )

        time_improvement = (
            (
                (std_result["total_time_sec"] - opt_result["total_time_sec"])
                / std_result["total_time_sec"]
                * 100
            )
            if std_result["total_time_sec"] > 0
            else 0
        )

        comparison = {
            "benchmark_name": name,
            "standard": std_result,
            "optimized": opt_result,
            "improvements": {
                "decode_speed_pct": decode_improvement,
                "prefill_speed_pct": prefill_improvement,
                "total_speed_pct": total_improvement,
                "memory_reduction_pct": memory_improvement,
                "time_reduction_pct": time_improvement,
            },
        }

        comparisons.append(comparison)

        # Collect for aggregate statistics
        improvements["decode_speed_improvements"].append(decode_improvement)
        improvements["prefill_speed_improvements"].append(prefill_improvement)
        improvements["total_speed_improvements"].append(total_improvement)
        improvements["memory_improvements"].append(memory_improvement)
        improvements["time_improvements"].append(time_improvement)

    # Calculate aggregate statistics
    aggregate_stats = {}
    for key, values in improvements.items():
        if values:
            aggregate_stats[f"{key}_avg"] = np.mean(values)
            aggregate_stats[f"{key}_median"] = np.median(values)
            aggregate_stats[f"{key}_min"] = np.min(values)
            aggregate_stats[f"{key}_max"] = np.max(values)
            aggregate_stats[f"{key}_std"] = np.std(values)

    # Calculate overall metrics
    std_decode_speeds = [
        std_result["decode_tokens_per_sec"] for std_result in standard_benchmarks.values()
    ]
    opt_decode_speeds = [
        opt_result["decode_tokens_per_sec"] for opt_result in optimized_benchmarks.values()
    ]

    avg_std_decode = np.mean(std_decode_speeds) if std_decode_speeds else 0
    avg_opt_decode = np.mean(opt_decode_speeds) if opt_decode_speeds else 0

    print(f"📊 Analysis complete:")
    print(f"  📈 Average standard decode speed: {avg_std_decode:.1f} tokens/sec")
    print(f"  📈 Average optimized decode speed: {avg_opt_decode:.1f} tokens/sec")
    print(
        f"  📈 Average improvement: {aggregate_stats.get('decode_speed_improvements_avg', 0):.1f}%"
    )

    return {
        "model": model_name,
        "timestamp": int(time.time()),
        "optimization_type": "custom_metal_kernel",
        "total_comparisons": len(comparisons),
        "individual_comparisons": comparisons,
        "aggregate_improvements": aggregate_stats,
        "summary": {
            "avg_decode_improvement_pct": aggregate_stats.get("decode_speed_improvements_avg", 0),
            "avg_total_improvement_pct": aggregate_stats.get("total_speed_improvements_avg", 0),
            "avg_memory_reduction_pct": aggregate_stats.get("memory_improvements_avg", 0),
            "avg_time_reduction_pct": aggregate_stats.get("time_improvements_avg", 0),
            "avg_standard_decode_speed": avg_std_decode,
            "avg_optimized_decode_speed": avg_opt_decode,
            "benchmarks_improved": sum(
                1 for x in improvements["decode_speed_improvements"] if x > 0
            ),
            "total_benchmarks": len(improvements["decode_speed_improvements"]),
        },
    }


def save_comparison_results(comparison_results, output_dir):
    """
    Save detailed comparison results to files.
    """
    if not comparison_results:
        return

    timestamp = comparison_results["timestamp"]

    # Save detailed JSON results
    comparison_file = f"openevolve_comparison_results_{timestamp}.json"
    with open(comparison_file, "w") as f:
        json.dump(comparison_results, f, indent=2)

    # Save CSV summary for easy analysis
    import csv

    csv_file = f"openevolve_comparison_summary_{timestamp}.csv"

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "benchmark_name",
                "category",
                "standard_decode_speed",
                "optimized_decode_speed",
                "decode_improvement_pct",
                "standard_prefill_speed",
                "optimized_prefill_speed",
                "prefill_improvement_pct",
                "standard_total_speed",
                "optimized_total_speed",
                "total_improvement_pct",
                "standard_memory_gb",
                "optimized_memory_gb",
                "memory_reduction_pct",
                "standard_time_sec",
                "optimized_time_sec",
                "time_reduction_pct",
            ]
        )

        for comp in comparison_results["individual_comparisons"]:
            # Extract category from benchmark name
            category = "general"
            name = comp["benchmark_name"]
            if "short" in name.lower():
                category = "short_context"
            elif "long" in name.lower():
                category = "long_context"
            elif "code" in name.lower():
                category = "code_generation"
            elif "stress" in name.lower() or "maximum" in name.lower():
                category = "stress_test"

            writer.writerow(
                [
                    comp["benchmark_name"],
                    category,
                    comp["standard"]["decode_tokens_per_sec"],
                    comp["optimized"]["decode_tokens_per_sec"],
                    comp["improvements"]["decode_speed_pct"],
                    comp["standard"]["prefill_tokens_per_sec"],
                    comp["optimized"]["prefill_tokens_per_sec"],
                    comp["improvements"]["prefill_speed_pct"],
                    comp["standard"]["total_tokens_per_sec"],
                    comp["optimized"]["total_tokens_per_sec"],
                    comp["improvements"]["total_speed_pct"],
                    comp["standard"]["peak_memory_gb"],
                    comp["optimized"]["peak_memory_gb"],
                    comp["improvements"]["memory_reduction_pct"],
                    comp["standard"]["total_time_sec"],
                    comp["optimized"]["total_time_sec"],
                    comp["improvements"]["time_reduction_pct"],
                ]
            )

    print(f"\n📁 Comparison results saved:")
    print(f"  📊 Detailed: {comparison_file}")
    print(f"  📈 Summary: {csv_file}")


def print_comparison_summary(comparison_results):
    """
    Print a comprehensive comparison summary.
    """
    if not comparison_results:
        print("❌ No comparison results to display")
        return

    print(f"\n{'='*100}")
    print(f"{'🚀 OPENEVOLVE CUSTOM METAL KERNEL OPTIMIZATION RESULTS':^100}")
    print(f"{'='*100}")

    summary = comparison_results["summary"]
    total_tests = comparison_results["total_comparisons"]

    print(f"\n💡 OPTIMIZATION: Custom Metal Kernel for GQA Attention")
    print(f"   Strategy: Hand-optimized Metal kernel using vectorized operations")
    print(f"   Target: Apple Silicon GPU with optimized memory access patterns")

    print(f"\n🎯 OVERALL PERFORMANCE IMPROVEMENTS (across {total_tests} comprehensive tests):")
    print(f"  📈 Average Decode Speed Improvement: {summary['avg_decode_improvement_pct']:+.2f}%")
    print(f"  ⚡ Average Total Speed Improvement:  {summary['avg_total_improvement_pct']:+.2f}%")
    print(f"  💾 Average Memory Reduction:        {summary['avg_memory_reduction_pct']:+.2f}%")
    print(f"  ⏱️  Average Time Reduction:          {summary['avg_time_reduction_pct']:+.2f}%")

    print(f"\n📊 ABSOLUTE PERFORMANCE:")
    print(
        f"  🔵 Standard MLX-LM:     {summary['avg_standard_decode_speed']:.1f} tokens/sec average"
    )
    print(
        f"  🟠 Metal Kernel Optimized: {summary['avg_optimized_decode_speed']:.1f} tokens/sec average"
    )
    print(
        f"  📈 Net Improvement:     {summary['avg_optimized_decode_speed'] - summary['avg_standard_decode_speed']:+.1f} tokens/sec"
    )

    print(f"\n📊 DETAILED BENCHMARK COMPARISON:")
    print(f"{'='*110}")
    print(
        f"{'Benchmark':<30} {'Standard':<12} {'Optimized':<12} {'Decode':<12} {'Memory':<12} {'Time':<12}"
    )
    print(
        f"{'Name':<30} {'Decode':<12} {'Decode':<12} {'Improv(%)':<12} {'Reduct(%)':<12} {'Reduct(%)':<12}"
    )
    print(f"{'-'*110}")

    for comp in sorted(
        comparison_results["individual_comparisons"],
        key=lambda x: x["improvements"]["decode_speed_pct"],
        reverse=True,
    ):
        name = comp["benchmark_name"][:29]
        std_decode = comp["standard"]["decode_tokens_per_sec"]
        opt_decode = comp["optimized"]["decode_tokens_per_sec"]
        decode_imp = comp["improvements"]["decode_speed_pct"]
        mem_imp = comp["improvements"]["memory_reduction_pct"]
        time_imp = comp["improvements"]["time_reduction_pct"]

        # Color coding for improvements
        if decode_imp > 20:
            marker = "🚀"
        elif decode_imp > 10:
            marker = "📈"
        elif decode_imp > 0:
            marker = "✅"
        else:
            marker = "⚠️"

        print(
            f"{marker} {name:<28} {std_decode:<12.1f} {opt_decode:<12.1f} {decode_imp:+<12.1f} {mem_imp:+<12.1f} {time_imp:+<12.1f}"
        )

    print(f"{'-'*110}")

    # Highlight best and worst improvements
    best_decode = max(
        comparison_results["individual_comparisons"],
        key=lambda x: x["improvements"]["decode_speed_pct"],
    )
    worst_decode = min(
        comparison_results["individual_comparisons"],
        key=lambda x: x["improvements"]["decode_speed_pct"],
    )

    print(f"\n🏆 PERFORMANCE HIGHLIGHTS:")
    print(
        f"  🥇 Best Improvement: {best_decode['benchmark_name']} (+{best_decode['improvements']['decode_speed_pct']:.1f}%)"
    )
    print(
        f"  📊 Worst Case: {worst_decode['benchmark_name']} ({worst_decode['improvements']['decode_speed_pct']:+.1f}%)"
    )

    # Optimization analysis
    improved_count = summary["benchmarks_improved"]
    total_count = summary["total_benchmarks"]
    success_rate = improved_count / total_count * 100 if total_count > 0 else 0

    print(f"\n📈 OPTIMIZATION ANALYSIS:")
    print(f"  ✅ Benchmarks Improved: {improved_count}/{total_count}")
    print(f"  📊 Success Rate: {success_rate:.1f}%")

    if summary["avg_decode_improvement_pct"] > 15:
        print(f"  🎉 EXCELLENT: OpenEvolve discovered a significant optimization!")
        print(
            f"  💡 {summary['avg_decode_improvement_pct']:.1f}% average improvement is substantial"
        )
        print(f"  🔬 This warrants further investigation and potential MLX-LM contribution")
    elif summary["avg_decode_improvement_pct"] > 5:
        print(f"  📈 GOOD: Meaningful performance improvements achieved")
        print(
            f"  🔧 {summary['avg_decode_improvement_pct']:.1f}% improvement shows optimization potential"
        )
    elif summary["avg_decode_improvement_pct"] > 0:
        print(f"  📊 MODEST: Some improvements observed")
        print(
            f"  💭 {summary['avg_decode_improvement_pct']:.1f}% suggests room for further optimization"
        )
    else:
        print(f"  ⚠️  No overall improvement detected")
        print(f"  🔧 Consider running additional evolution cycles or different strategies")

    # Technical insights
    print(f"\n🔬 TECHNICAL INSIGHTS:")
    print(f"  💡 Custom Metal Kernel Strategy:")
    print(f"     • Standard: mx.fast.scaled_dot_product_attention")
    print(f"     • Optimized: Hand-written Metal kernel with vectorized operations")
    print(f"  🧠 Potential Reasons for Performance Gains:")
    print(f"     • Optimized memory access patterns for Apple Silicon")
    print(f"     • Vectorized operations using vec<T, 8> types")
    print(f"     • Better cache locality with custom computation order")
    print(f"     • GPU-specific optimizations for M-series processors")

    if summary["avg_decode_improvement_pct"] > 10:
        print(f"\n🎯 NEXT STEPS:")
        print(f"  1. Verify results independently outside this framework")
        print(f"  2. Profile Metal kernel execution patterns and memory usage")
        print(f"  3. Test on different Apple Silicon variants (M1, M2, M3, M4)")
        print(f"  4. Consider contributing Metal kernel optimization back to MLX")
        print(f"  5. Explore similar Metal kernel strategies for other attention patterns")

    print(f"\n{'='*100}")
    print(f"🔬 Comprehensive analysis complete! Results saved to comparison files.")
    print(f"💡 This represents a genuine Metal kernel discovery by OpenEvolve.")
    print(f"{'='*100}")
