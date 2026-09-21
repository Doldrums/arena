"""
🛡️ BULLETPROOF METAL KERNEL EVALUATOR 🛡️

This evaluator provides MAXIMUM protection against Metal kernel failures during evolution:

🔧 METAL-SPECIFIC PROTECTION:
1. Pre-execution kernel parameter validation
2. Memory safety checks before GPU execution
3. Command buffer error detection and recovery
4. Thread-safe Metal kernel execution wrapping
5. Graceful fallback to standard attention on ANY Metal failure

🚀 EVOLUTION SAFETY:
- NEVER crashes the evolution process
- Handles kIOGPUCommandBufferCallbackErrorInvalidResource errors
- Catches GPU memory violations, out-of-bounds access, race conditions
- Provides detailed error classification for debugging
- Maintains evolution progress even with buggy kernel code

🎯 ROBUST ERROR RECOVERY:
- Multiple retry attempts with exponential backoff
- Automatic fallback mechanisms
- Comprehensive error statistics tracking
- Safe cleanup of GPU resources
"""

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

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mlx.core as mx
import mlx.nn as nn

# Import the comprehensive benchmark suite for consistent testing
from qwen3_benchmark_suite import Qwen3BenchmarkSuite, BenchmarkConfig, BenchmarkResult
from _metal_errors import MetalKernelSafetyError, GPUCommandBufferError, MetalMemoryViolationError
from _metal_safety import MetalSafety
from _metal_correctness import MetalCorrectness
from _metal_performance import MetalPerformance
from _metal_reporting import MetalReporting


class BulletproofMetalEvaluator(MetalSafety, MetalCorrectness, MetalPerformance, MetalReporting):

    """Bulletproof evaluator that NEVER crashes from Metal kernel failures"""

    def __init__(self):
        self.model_path = "mlx-community/Qwen3-0.6B-bf16"

        # Enhanced error handling configuration
        self.max_retry_attempts = 3
        self.retry_base_delay = 1.0  # Base delay for exponential backoff
        self.kernel_validation_timeout = 30  # Timeout for kernel validation

        # Comprehensive error tracking
        self.metal_command_buffer_errors = 0
        self.metal_memory_violations = 0
        self.metal_compilation_errors = 0
        self.gpu_resource_errors = 0
        self.total_metal_errors = 0
        self.successful_fallbacks = 0
        self.retry_attempts_used = 0

        # Safety thresholds
        self.max_sequence_length_safe = 512  # Start with safer sequence lengths
        self.max_batch_size_safe = 1
        self.max_head_dimension_safe = 128

        # Baseline metrics storage
        self.baseline_metrics = None
        self.baseline_results = None

        # Use comprehensive benchmark suite
        self.benchmark_suite = Qwen3BenchmarkSuite(self.model_path)

        print("🛡️  BULLETPROOF METAL KERNEL EVALUATOR INITIALIZED")
        print(f"📱 Model: {self.model_path}")
        print(f"🔁 Max retry attempts: {self.max_retry_attempts}")
        print(f"⚡ GPU error protection: MAXIMUM")
        print(f"🧠 Memory safety validation: ENABLED")
        print(f"🎯 Command buffer error handling: ACTIVE")

    def evaluate(self, program_text: str) -> Dict[str, Any]:
        """
        BULLETPROOF evaluation that handles ALL Metal kernel failures:
        1. Enhanced program extraction with syntax validation
        2. Pre-execution kernel safety validation
        3. Protected baseline measurement with fallback
        4. GPU-safe correctness testing with memory checks
        5. Armored benchmarking with command buffer protection
        6. Comprehensive Metal error recovery and statistics
        """

        print("\n" + "🛡️ " * 50)
        print("🛡️  BULLETPROOF METAL KERNEL EVALUATION STARTING")
        print("🛡️ " * 50)
        print("✅ GPU Command Buffer Error Protection: ACTIVE")
        print("✅ Metal Memory Violation Detection: ENABLED")
        print("✅ Automatic Fallback Mechanisms: READY")
        print("✅ Multi-layer Error Recovery: ARMED")
        print("✅ Evolution Process Protection: MAXIMUM")
        print("🛡️ " * 50)

        try:
            # Reset all error counters
            self._reset_error_counters()

            # Step 1: Enhanced program extraction with Metal validation
            print("\n🔧 STEP 1: Enhanced Program Extraction with Metal Validation")
            extraction_result = self._bulletproof_extract_custom_attention(program_text)
            if not extraction_result["success"]:
                return self._create_comprehensive_failure_result(
                    f"Program extraction failed: {extraction_result['error']}"
                )

            custom_attention_class = extraction_result["class"]
            program_source = extraction_result["program_text"]

            # Step 2: Pre-execution Metal kernel safety validation
            print("\n🔍 STEP 2: Pre-execution Metal Kernel Safety Validation")
            safety_result = self._validate_metal_kernel_safety(custom_attention_class)
            if not safety_result["success"]:
                print(f"⚠️  Metal kernel safety validation failed: {safety_result['error']}")
                print("🛡️  Proceeding with enhanced protection...")

            # Step 3: Memory-safe correctness testing FIRST (fail fast, skip baseline if invalid)
            print("\n🔍 STEP 3: Memory-Safe Custom Attention Correctness Testing")
            correctness_result = self._memory_safe_correctness_test(custom_attention_class)
            if not correctness_result["success"]:
                return self._create_comprehensive_failure_result(
                    f"Memory-safe correctness test failed: {correctness_result['error']}"
                )

            correctness_score = correctness_result["score"]
            if correctness_score < 0.90:  # Slightly more lenient for complex kernels
                return self._create_comprehensive_failure_result(
                    f"Correctness score too low: {correctness_score:.3f} (required: 0.90)"
                )

            # Step 4: GPU-protected baseline measurement (only if correctness passed)
            print("\n📊 STEP 4: GPU-Protected Baseline Performance Measurement")
            baseline_results = self._gpu_protected_measure_baseline()
            if not baseline_results:
                return self._create_comprehensive_failure_result(
                    "Failed to measure baseline performance with GPU protection"
                )

            # Step 5: Command-buffer-protected benchmarking
            print("\n🚀 STEP 5: Command-Buffer-Protected Performance Benchmarking")
            benchmark_result = self._command_buffer_protected_benchmark(
                program_source, custom_attention_class
            )
            if not benchmark_result["success"]:
                return self._create_comprehensive_failure_result(
                    f"Command-buffer-protected benchmarking failed: {benchmark_result['error']}"
                )

            custom_results = benchmark_result["results"]

            # Step 6: Enhanced performance analysis
            print("\n📈 STEP 6: Enhanced Performance Analysis")
            performance_analysis = self._analyze_performance_with_safety_metrics(
                baseline_results, custom_results
            )

            # Step 7: Calculate safety-adjusted final score
            final_score = self._calculate_safety_adjusted_score(
                performance_analysis, correctness_score
            )

            # Step 8: Generate comprehensive result with full error statistics
            result = {
                "success": True,
                "final_score": final_score,
                "combined_score": final_score,
                "performance_metrics": performance_analysis["aggregate_metrics"],
                "correctness_score": correctness_score,
                "benchmark_results": [self._result_to_dict(r) for r in custom_results],
                "baseline_comparison": performance_analysis["comparison_summary"],
                "individual_comparisons": performance_analysis["individual_comparisons"],
                "summary": self._generate_comprehensive_summary(
                    performance_analysis, correctness_score
                ),
                "metal_safety_statistics": self._get_comprehensive_error_statistics(),
                "safety_validation": safety_result,
            }

            self._print_bulletproof_evaluation_results(result)
            return result

        except Exception as e:
            # Ultimate protection: even this top-level catch must never crash evolution
            self.total_metal_errors += 1
            error_msg = f"TOP-LEVEL BULLETPROOF CATCH: {str(e)}"
            print(f"🛡️  {error_msg}")
            traceback.print_exc()
            return self._create_comprehensive_failure_result(error_msg)

    def _reset_error_counters(self):
        """Reset all error tracking counters"""
        self.metal_command_buffer_errors = 0
        self.metal_memory_violations = 0
        self.metal_compilation_errors = 0
        self.gpu_resource_errors = 0
        self.total_metal_errors = 0
        self.successful_fallbacks = 0
        self.retry_attempts_used = 0

    def _bulletproof_extract_custom_attention(self, program_text: str) -> Dict[str, Any]:
        """Bulletproof extraction with comprehensive Metal kernel validation"""
        try:
            print("  🔍 Bulletproof program analysis with Metal validation...")

            # Handle file paths vs direct text
            if (
                program_text.startswith("/")
                and "\n" not in program_text
                and len(program_text) < 500
            ):
                print(f"  📁 Reading program from file: {program_text}")
                if os.path.exists(program_text):
                    try:
                        with open(program_text, "r") as f:
                            actual_program_text = f.read()
                    except Exception as e:
                        return {"success": False, "error": f"File read error: {e}"}
                else:
                    return {"success": False, "error": f"Program file not found: {program_text}"}
            else:
                actual_program_text = program_text

            # Enhanced syntax validation
            try:
                compile(actual_program_text, "<evolved_program>", "exec")
                print("  ✅ Enhanced syntax validation passed")
            except SyntaxError as e:
                return {"success": False, "error": f"Syntax error: {e}"}

            # Pre-validate Metal kernel syntax (static analysis)
            metal_validation = self._static_validate_metal_kernel_syntax(actual_program_text)
            if not metal_validation["safe"]:
                print(
                    f"  ⚠️  Metal kernel static validation warning: {metal_validation['warnings']}"
                )

            # Create ultra-safe execution environment
            exec_globals = self._create_bulletproof_execution_environment()

            # Execute program with maximum protection
            print("  ⚙️  Executing program with MAXIMUM protection...")
            try:
                success, result = self._bulletproof_execute_with_gpu_protection(
                    lambda: exec(actual_program_text, exec_globals)
                )

                if not success:
                    self.total_metal_errors += 1
                    return {"success": False, "error": f"Protected execution failed: {result}"}

            except Exception as e:
                self.total_metal_errors += 1
                return {"success": False, "error": f"Execution error with GPU protection: {e}"}

            # Enhanced class extraction and validation
            custom_class = exec_globals.get("CustomGQAAttention")
            if custom_class is None:
                return {
                    "success": False,
                    "error": "CustomGQAAttention class not found in executed code",
                }

            # Comprehensive class validation
            validation_result = self._validate_custom_attention_class(custom_class)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}

            print(f"  ✅ Successfully extracted and validated CustomGQAAttention class")
            print(f"  🛡️  Metal safety pre-checks: {metal_validation['safe']}")

            return {
                "success": True,
                "class": custom_class,
                "metal_validation": metal_validation,
                "program_text": actual_program_text,
            }

        except Exception as e:
            self.total_metal_errors += 1
            return {"success": False, "error": f"Bulletproof extraction failed: {str(e)}"}

    def _static_validate_metal_kernel_syntax(self, program_text: str) -> Dict[str, Any]:
        """Static analysis of Metal kernel syntax for common safety issues"""
        warnings = []

        # Check for common Metal safety issues
        dangerous_patterns = [
            ("buffer overflow", ["queries[", "keys[", "values[", "output[", "mask["]),
            ("unguarded loops", ["for (", "while ("]),
            ("raw pointers", ["*queries", "*keys", "*values", "*output"]),
            ("thread sync issues", ["threadgroup", "simdgroup"]),
        ]

        for issue_type, patterns in dangerous_patterns:
            for pattern in patterns:
                if pattern in program_text:
                    warnings.append(f"{issue_type}: {pattern}")

        # Check for bounds checking
        has_bounds_checking = any(
            check in program_text
            for check in [
                "batch_idx >= BATCH_SIZE",
                "head_idx >= NUM_HEADS",
                "query_pos >= SEQ_LEN",
                "d < HEAD_DIM",
            ]
        )

        if not has_bounds_checking:
            warnings.append("missing bounds checking")

        return {
            "safe": len(warnings) == 0,
            "warnings": warnings,
            "has_bounds_checking": has_bounds_checking,
        }

    def _validate_custom_attention_class(self, custom_class: Any) -> Dict[str, Any]:
        """Comprehensive validation of custom attention class"""
        try:
            # Basic type checking
            if not isinstance(custom_class, type):
                return {"valid": False, "error": "CustomGQAAttention is not a valid class"}

            # Check for required methods
            required_methods = ["__init__", "__call__"]
            for method in required_methods:
                if not hasattr(custom_class, method):
                    return {"valid": False, "error": f"Missing required method: {method}"}

            # Check if it inherits from nn.Module (recommended)
            if not issubclass(custom_class, nn.Module):
                print("  ⚠️  CustomGQAAttention doesn't inherit from nn.Module")

            print("  ✅ Custom attention class validation passed")
            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Class validation error: {e}"}


def evaluate(program_text: str) -> Dict[str, Any]:
    """🛡️ BULLETPROOF evaluation function called by OpenEvolve"""
    evaluator = BulletproofMetalEvaluator()
    return evaluator.evaluate(program_text)


def test_bulletproof_evaluator():
    """Test the bulletproof Metal kernel evaluator"""
    print("🧪 Testing Bulletproof Metal Kernel Evaluator")
    print("🛡️ " * 40)

    initial_program_path = os.path.join(os.path.dirname(__file__), "initial_program.py")

    if not os.path.exists(initial_program_path):
        print(f"❌ Initial program not found: {initial_program_path}")
        return

    print(f"📁 Testing with bulletproof protection: {initial_program_path}")
    result = evaluate(initial_program_path)

    print(f"\n{'🛡️ '*20}")
    print(f"🔬 BULLETPROOF EVALUATOR TEST RESULTS")
    print(f"{'🛡️ '*20}")
    print(f"Success: {result['success']}")
    print(f"Final Score: {result.get('final_score', 'N/A')}")

    if result.get("metal_safety_statistics"):
        stats = result["metal_safety_statistics"]
        print(f"Metal Command Buffer Errors: {stats.get('metal_command_buffer_errors', 0)}")
        print(f"Metal Memory Violations: {stats.get('metal_memory_violations', 0)}")
        print(f"Total Metal Errors Handled: {stats.get('total_metal_errors', 0)}")
        print(f"Safety Score: {stats.get('safety_score', 0):.1f}/100")

    print(f"Summary: {result.get('summary', 'N/A')}")

    return result


if __name__ == "__main__":
    test_bulletproof_evaluator()
