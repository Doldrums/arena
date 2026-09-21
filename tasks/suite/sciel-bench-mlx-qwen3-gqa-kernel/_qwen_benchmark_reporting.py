"""BenchmarkReporting implementation for the bundled MLX task."""
import time
import json
import subprocess
import tempfile
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import mlx.core as mx
import mlx.nn as nn
import numpy as np
from _qwen_benchmark_types import BenchmarkConfig, BenchmarkResult


class BenchmarkReporting:

    def run_full_benchmark_suite(self) -> Dict:
        """Run the complete benchmark suite"""
        print(f"\n{'='*80}")
        print(f"Qwen3-0.6B Comprehensive Benchmark Suite")
        print(f"Model: {self.model_path}")
        print(f"Hardware: Apple M4 24GB")
        print(f"Target: Custom Metal kernel optimization validation")
        print(f"{'='*80}")

        configs = self.create_benchmark_configs()
        results = []

        for i, config in enumerate(configs, 1):
            print(f"\n[{i}/{len(configs)}] Starting benchmark: {config.name}")
            try:
                result = self.run_single_benchmark(config)
                results.append(result)
                self.results.append(result)
            except Exception as e:
                print(f"Failed to run benchmark {config.name}: {e}")
                continue

        # Generate summary
        summary = self.generate_summary(results)
        self.save_results(results, summary)

        return {"results": [self._result_to_dict(r) for r in results], "summary": summary}

    def generate_summary(self, results: List[BenchmarkResult]) -> Dict:
        """Generate benchmark summary statistics"""
        if not results:
            return {}

        # Overall statistics
        decode_speeds = [r.decode_tokens_per_sec for r in results if r.decode_tokens_per_sec > 0]
        prefill_speeds = [r.prefill_tokens_per_sec for r in results if r.prefill_tokens_per_sec > 0]
        memories = [r.peak_memory_gb for r in results if r.peak_memory_gb > 0]

        summary = {
            "total_benchmarks": len(results),
            "avg_decode_speed": np.mean(decode_speeds) if decode_speeds else 0,
            "min_decode_speed": np.min(decode_speeds) if decode_speeds else 0,
            "max_decode_speed": np.max(decode_speeds) if decode_speeds else 0,
            "avg_prefill_speed": np.mean(prefill_speeds) if prefill_speeds else 0,
            "min_prefill_speed": np.min(prefill_speeds) if prefill_speeds else 0,
            "max_prefill_speed": np.max(prefill_speeds) if prefill_speeds else 0,
            "avg_memory_usage": np.mean(memories) if memories else 0,
            "max_memory_usage": np.max(memories) if memories else 0,
            "min_memory_usage": np.min(memories) if memories else 0,
        }

        # Category analysis
        categories = {
            "context_length": [r for r in results if "context" in r.name],
            "generation_length": [r for r in results if "generation" in r.name],
            "use_cases": [
                r
                for r in results
                if any(
                    x in r.name
                    for x in ["code", "reasoning", "creative", "technical", "conversational"]
                )
            ],
            "memory_pressure": [
                r for r in results if any(x in r.name for x in ["progressive", "repetitive"])
            ],
        }

        for category, cat_results in categories.items():
            if cat_results:
                cat_decode_speeds = [
                    r.decode_tokens_per_sec for r in cat_results if r.decode_tokens_per_sec > 0
                ]
                summary[f"{category}_avg_decode_speed"] = (
                    np.mean(cat_decode_speeds) if cat_decode_speeds else 0
                )
                summary[f"{category}_count"] = len(cat_results)

        return summary

    def save_results(self, results: List[BenchmarkResult], summary: Dict):
        """Save benchmark results to files"""
        timestamp = int(time.time())

        # Save detailed results
        detailed_results = {
            "timestamp": timestamp,
            "model": self.model_path,
            "hardware": "Apple M4 24GB",
            "optimization": "Custom Metal kernel for GQA attention",
            "mlx_version": mx.__version__,
            "results": [self._result_to_dict(r) for r in results],
            "summary": summary,
        }

        with open(f"qwen3_benchmark_results_{timestamp}.json", "w") as f:
            json.dump(detailed_results, f, indent=2)

        # Save CSV for easy analysis
        import csv

        with open(f"qwen3_benchmark_results_{timestamp}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "name",
                    "description",
                    "prompt_tokens",
                    "generated_tokens",
                    "prefill_tokens_per_sec",
                    "decode_tokens_per_sec",
                    "total_tokens_per_sec",
                    "peak_memory_gb",
                    "total_time_sec",
                ]
            )

            configs = self.create_benchmark_configs()
            config_dict = {c.name: c for c in configs}

            for result in results:
                config = config_dict.get(result.name)
                writer.writerow(
                    [
                        result.name,
                        config.description if config else "",
                        result.prompt_tokens,
                        result.generated_tokens,
                        result.prefill_tokens_per_sec,
                        result.decode_tokens_per_sec,
                        result.total_tokens_per_sec,
                        result.peak_memory_gb,
                        result.total_time_sec,
                    ]
                )

        print(f"\n{'='*60}")
        print(f"Results saved to:")
        print(f"  - qwen3_benchmark_results_{timestamp}.json")
        print(f"  - qwen3_benchmark_results_{timestamp}.csv")
        print(f"{'='*60}")

    def _result_to_dict(self, result: BenchmarkResult) -> Dict:
        """Convert BenchmarkResult to dictionary"""
        return {
            "name": result.name,
            "prompt_tokens": result.prompt_tokens,
            "generated_tokens": result.generated_tokens,
            "prefill_tokens_per_sec": result.prefill_tokens_per_sec,
            "decode_tokens_per_sec": result.decode_tokens_per_sec,
            "total_tokens_per_sec": result.total_tokens_per_sec,
            "peak_memory_gb": result.peak_memory_gb,
            "total_time_sec": result.total_time_sec,
            "prompt": result.prompt,
            "generated_text": result.generated_text,
        }

    def print_summary_table(self):
        """Print a summary table of all results"""
        if not self.results:
            print("No benchmark results available")
            return

        print(f"\n{'='*120}")
        print(f"{'Benchmark Summary':^120}")
        print(f"{'='*120}")
        print(
            f"{'Name':<25} {'Tokens':<8} {'Prefill':<10} {'Decode':<10} {'Overall':<10} {'Memory':<8} {'Time':<8}"
        )
        print(f"{'='*120}")

        for result in self.results:
            print(
                f"{result.name:<25} "
                f"{result.generated_tokens:<8} "
                f"{result.prefill_tokens_per_sec:<10.1f} "
                f"{result.decode_tokens_per_sec:<10.1f} "
                f"{result.total_tokens_per_sec:<10.1f} "
                f"{result.peak_memory_gb:<8.2f} "
                f"{result.total_time_sec:<8.1f}"
            )

        print(f"{'='*120}")

        # Summary statistics
        decode_speeds = [
            r.decode_tokens_per_sec for r in self.results if r.decode_tokens_per_sec > 0
        ]
        if decode_speeds:
            print(f"Average decode speed: {np.mean(decode_speeds):.1f} tokens/sec")
            print(f"Best decode speed: {np.max(decode_speeds):.1f} tokens/sec")
            print(f"Worst decode speed: {np.min(decode_speeds):.1f} tokens/sec")
