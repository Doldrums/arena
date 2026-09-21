#!/usr/bin/env python3
"""
Qwen3 Benchmark Runner

Simple script to run baseline benchmarks for Qwen3-0.6B optimization.
Includes comparison mode to benchmark standard vs optimized attention.
"""

import argparse
import sys
import os
import time
import json
import numpy as np
from typing import Dict, List, Any

# Add the current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen3_benchmark_suite import Qwen3BenchmarkSuite, BenchmarkResult
from quick_benchmark_test import run_quick_test

from _qwen_benchmark_comparison import (
    analyze_comparison_results, save_comparison_results, print_comparison_summary,
)


def run_compare_benchmarks(args):
    """
    Run comprehensive comparison between standard and optimized attention.
    Uses the full benchmark suite for thorough analysis.
    """
    print(f"\n🔬 Running Comparison Benchmark Mode")
    print(f"📊 Comparing Standard vs OpenEvolve Discovered Optimization")
    print(f"🎯 Model: {args.model}")
    print(f"📁 Output directory: {args.output_dir}")
    print("=" * 80)

    # Change to output directory
    original_dir = os.getcwd()
    if args.output_dir != ".":
        os.makedirs(args.output_dir, exist_ok=True)
        os.chdir(args.output_dir)

    try:
        # Run standard benchmark (baseline)
        print("\n🏃‍♂️ Phase 1: Running Standard MLX-LM Attention Benchmark...")
        print("⏱️  This establishes our baseline performance across all scenarios")

        # Get dynamic test count
        temp_suite = Qwen3BenchmarkSuite(args.model)
        test_count = len(temp_suite.create_benchmark_configs())

        print(f"📊 Running full benchmark suite ({test_count} comprehensive tests)")
        print("⏳ This will take 15-30 minutes depending on your hardware...")

        standard_suite = Qwen3BenchmarkSuite(args.model)
        standard_results = standard_suite.run_full_benchmark_suite()

        print("\n✅ Standard benchmark complete!")
        print(f"📊 Standard results: {len(standard_results['results'])} benchmarks completed")

        # Apply optimized attention hook and run benchmark
        print("\n🚀 Phase 2: Running OpenEvolve Discovered Optimization...")
        print("💡 Applying custom Metal kernel optimized GQA attention")

        # Import and apply the optimized attention
        optimized_results = run_optimized_benchmark(args, original_dir)

        if optimized_results is None:
            print("❌ Failed to run optimized benchmark")
            return 1

        print("\n✅ Optimized benchmark complete!")
        print(f"📊 Optimized results: {len(optimized_results['results'])} benchmarks completed")

        # Generate comparison analysis
        print("\n📈 Generating Comparison Analysis...")
        comparison_results = analyze_comparison_results(
            standard_results, optimized_results, args.model
        )

        if comparison_results is None:
            print("❌ Failed to generate comparison analysis")
            return 1

        # Save comparison results
        save_comparison_results(comparison_results, args.output_dir)

        # Print detailed comparison
        print_comparison_summary(comparison_results)

        return 0

    except Exception as e:
        print(f"❌ Error in comparison benchmark: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        os.chdir(original_dir)


def run_optimized_benchmark(args, original_dir):
    """
    Run benchmark with the optimized attention from best_program.py.
    """
    try:
        # Import the optimized attention implementation
        # First, try the OpenEvolve output directory (most likely location)
        best_program_path = os.path.join(
            original_dir, "openevolve_output", "best", "best_program.py"
        )

        # Fallback to root directory if not found in openevolve_output
        if not os.path.exists(best_program_path):
            best_program_path = os.path.join(original_dir, "best_program.py")

        if not os.path.exists(best_program_path):
            print(f"❌ Error: Optimized program not found")
            print("Searched in the following locations:")
            print(
                f"  1. {os.path.join(original_dir, 'openevolve_output', 'best', 'best_program.py')}"
            )
            print(f"  2. {os.path.join(original_dir, 'best_program.py')}")
            print("Please ensure OpenEvolve has generated an optimized solution")
            print("Expected path: ./openevolve_output/best/best_program.py")
            return None

        print(f"📁 Loading optimized program from: {best_program_path}")

        # Import the optimized module
        import importlib.util

        spec = importlib.util.spec_from_file_location("best_program", best_program_path)
        best_program = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(best_program)

        print("✅ Optimized program loaded successfully")

        # Check for the hook function
        if not hasattr(best_program, "create_metal_qwen3_optimization_hook"):
            print(
                "❌ Error: create_metal_qwen3_optimization_hook function not found in best_program.py"
            )
            print(
                "Available functions:",
                [attr for attr in dir(best_program) if not attr.startswith("_")],
            )
            return None

        # IMPORTANT: the benchmark suite runs `mlx_lm.generate` in a subprocess.
        # Monkey-patching Attention in this parent process does not propagate to the subprocess.
        # Instead, we pass the evolved program path so the subprocess can apply the hook in-process.

        print("📊 Running full benchmark suite with custom Metal kernel optimization...")
        print("⏳ This will take another 15-30 minutes...")
        print("💡 The optimization uses a custom Metal kernel implementation for Apple Silicon GPU")

        optimized_suite = Qwen3BenchmarkSuite(args.model, hook_program_path=best_program_path)
        optimized_results = optimized_suite.run_full_benchmark_suite()

        print("✅ Custom Metal kernel benchmark suite completed successfully")
        return optimized_results

    except Exception as e:
        print(f"❌ Error running Metal kernel optimized benchmark: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Run Qwen3-0.6B benchmarks")
    parser.add_argument(
        "--mode",
        choices=["quick", "full", "compare"],
        default="quick",
        help="Benchmark mode: quick (5 tests), full (comprehensive), or compare (standard vs optimized)",
    )
    parser.add_argument(
        "--model", default="mlx-community/Qwen3-0.6B-bf16", help="Model path or name"
    )
    parser.add_argument("--output-dir", default=".", help="Output directory for results")

    args = parser.parse_args()

    print(f"🚀 Qwen3 Benchmark Runner")
    print(f"📊 Mode: {args.mode}")
    print(f"🤖 Model: {args.model}")
    print(f"📁 Output: {args.output_dir}")

    if args.mode == "quick":
        print("\n🚀 Running Quick Benchmark (5 key tests)...")
        results = run_quick_test()
        print("\n✅ Quick benchmark complete!")

    elif args.mode == "compare":
        print("\n🔬 Running Comprehensive Comparison...")
        print("📊 This will benchmark standard MLX-LM vs OpenEvolve Metal kernel optimization")
        return run_compare_benchmarks(args)

    else:  # full
        # Get dynamic test count for display
        temp_suite = Qwen3BenchmarkSuite(args.model)
        test_count = len(temp_suite.create_benchmark_configs())

        print(f"\n🚀 Running Full Benchmark Suite ({test_count} comprehensive tests)...")
        print("⏱️  This may take 15-30 minutes depending on your hardware...")

        # Change to output directory
        original_dir = os.getcwd()
        if args.output_dir != ".":
            os.makedirs(args.output_dir, exist_ok=True)
            os.chdir(args.output_dir)

        try:
            benchmark_suite = Qwen3BenchmarkSuite(args.model)
            results = benchmark_suite.run_full_benchmark_suite()
            benchmark_suite.print_summary_table()

            print("\n✅ Full benchmark suite complete!")
            print(f"📊 Results saved in: {args.output_dir}")

        finally:
            os.chdir(original_dir)

    if args.mode != "compare":
        print("\n🎯 These results establish the baseline for Metal kernel optimization.")
        print("🔧 Next step: Run with --mode compare to validate OpenEvolve discoveries!")
        print("💡 Example: python run_benchmarks.py --mode compare --output-dir results")
        print("📚 Ensure MLX-LM is installed: pip install mlx-lm")

    return 0


if __name__ == "__main__":
    sys.exit(main())
