"""MetalCorrectness implementation for the bundled MLX task."""
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


class MetalCorrectness:

    def _memory_safe_correctness_test(self, custom_attention_class: Any) -> Dict[str, Any]:
        """Memory-safe correctness testing with GPU protection"""
        print("  🔍 Running memory-safe correctness testing...")

        try:
            # Safe test configuration
            class MockArgs:
                # Must match the default model `mlx-community/Qwen3-0.6B-bf16`
                hidden_size = 2048
                num_attention_heads = 16
                num_key_value_heads = 8
                head_dim = 128
                rms_norm_eps = 1e-06
                rope_theta = 1000000
                rope_scaling = None
                max_position_embeddings = 40960

            args = MockArgs()

            # Conservative test cases (smaller sequences for safety)
            test_cases = [
                (1, 8, 2048),  # Micro sequence
                (1, 16, 2048),  # Very short
                (1, 32, 2048),  # Short sequence
                (1, 64, 2048),  # Medium sequence
            ]

            correctness_scores = []
            local_command_buffer_errors = 0
            local_memory_violations = 0

            for B, L, D in test_cases:
                print(f"      🧪 Memory-safe testing sequence length {L}...")

                retry_count = 0
                while retry_count <= self.max_retry_attempts:
                    try:
                        # Clean GPU state
                        self._ensure_clean_gpu_state()

                        # Create conservative test inputs
                        # IMPORTANT: Match the real inference dtype used by the default model
                        # (`mlx-community/Qwen3-0.6B-bf16`), otherwise Metal kernels may compile
                        # for float32 in correctness tests but fail under bfloat16 in practice.
                        x = (mx.random.normal((B, L, D)) * 0.1).astype(mx.bfloat16)
                        mask = "causal"

                        # Test with maximum GPU protection
                        success, result = self._bulletproof_execute_with_gpu_protection(
                            lambda: self._test_single_sequence_memory_safe(
                                custom_attention_class, args, x, mask
                            )
                        )

                        if success:
                            correctness_scores.append(result)
                            print(f"      ✅ Sequence {L}: PASS (score={result:.3f})")
                            break
                        else:
                            error_msg = str(result)

                            # Enhanced error classification
                            if "command buffer" in error_msg.lower():
                                local_command_buffer_errors += 1
                            elif "memory violation" in error_msg.lower():
                                local_memory_violations += 1

                            # EARLY EXIT: Metal compilation errors are deterministic - no retry
                            if "unable to build metal library" in error_msg.lower():
                                self.metal_compilation_errors += 1
                                print(
                                    f"      ❌ Metal compilation error (no retry): {error_msg[:200]}..."
                                )
                                # Return early - compilation errors won't be fixed by retrying
                                return {
                                    "success": False,
                                    "score": 0.0,
                                    "error": "Metal kernel compilation failed - bfloat16 incompatible code",
                                    "command_buffer_errors": local_command_buffer_errors,
                                    "memory_violations": local_memory_violations,
                                    "compilation_error": True,
                                }

                            if retry_count < self.max_retry_attempts:
                                print(
                                    f"      🔄 Retry {retry_count + 1} for length {L}: {error_msg}"
                                )
                                retry_count += 1
                                time.sleep(self.retry_base_delay * (2**retry_count))
                                continue
                            else:
                                print(f"      ❌ All retries failed for length {L}: {error_msg}")
                                correctness_scores.append(0.0)
                                break

                    except Exception as e:
                        error_msg = str(e)
                        print(f"      ❌ Exception for length {L}: {error_msg}")

                        # EARLY EXIT: Metal compilation errors are deterministic - no retry
                        if "unable to build metal library" in error_msg.lower():
                            self.metal_compilation_errors += 1
                            print(
                                f"      ❌ Metal compilation error (no retry): {error_msg[:200]}..."
                            )
                            return {
                                "success": False,
                                "score": 0.0,
                                "error": "Metal kernel compilation failed - bfloat16 incompatible code",
                                "command_buffer_errors": local_command_buffer_errors,
                                "memory_violations": local_memory_violations,
                                "compilation_error": True,
                            }

                        if retry_count < self.max_retry_attempts:
                            retry_count += 1
                            time.sleep(self.retry_base_delay * (2**retry_count))
                            continue
                        else:
                            correctness_scores.append(0.0)
                            break

            # Update global error counters
            self.metal_command_buffer_errors += local_command_buffer_errors
            self.metal_memory_violations += local_memory_violations
            self.total_metal_errors += local_command_buffer_errors + local_memory_violations

            # Calculate overall correctness with partial credit
            overall_correctness = np.mean(correctness_scores) if correctness_scores else 0.0

            print(f"    📊 Memory-safe overall correctness: {overall_correctness:.3f}")
            print(f"    🛡️  Command buffer errors: {local_command_buffer_errors}")
            print(f"    🛡️  Memory violations: {local_memory_violations}")

            return {
                "success": True,
                "score": overall_correctness,
                "command_buffer_errors": local_command_buffer_errors,
                "memory_violations": local_memory_violations,
            }

        except Exception as e:
            self.total_metal_errors += 1
            print(f"    ❌ Memory-safe correctness testing failed: {e}")
            return {"success": False, "error": str(e)}

    def _test_single_sequence_memory_safe(
        self, custom_attention_class: Any, args: Any, x: Any, mask: Any
    ) -> float:
        """Test single sequence with enhanced memory safety"""
        try:
            # Force bfloat16 to exercise the same kernel template/compilation path as production
            # inference with `mlx-community/Qwen3-0.6B-bf16`.
            if x.dtype != mx.bfloat16:
                x = x.astype(mx.bfloat16)

            # Pre-execution safety checks
            if x.shape[1] > self.max_sequence_length_safe:
                raise MetalKernelSafetyError(
                    f"Sequence length {x.shape[1]} exceeds safe limit {self.max_sequence_length_safe}"
                )

            if x.shape[0] > self.max_batch_size_safe:
                raise MetalKernelSafetyError(
                    f"Batch size {x.shape[0]} exceeds safe limit {self.max_batch_size_safe}"
                )

            # Instantiate with error checking
            custom_attn = custom_attention_class(args)
            if custom_attn is None:
                raise ValueError("Failed to instantiate custom attention")

            # Ensure module parameters follow the intended compute dtype as well.
            # Otherwise, float32 weights can upcast intermediate Q/K/V tensors and
            # accidentally avoid bfloat16 kernel compilation.
            if hasattr(custom_attn, "set_dtype"):
                custom_attn.set_dtype(mx.bfloat16)

            # Conservative forward pass with timeout simulation
            start_time = time.time()
            output = custom_attn(x, mask=mask)
            elapsed_time = time.time() - start_time

            # Timeout check (soft limit)
            if elapsed_time > self.kernel_validation_timeout:
                print(f"        ⚠️  Slow execution detected: {elapsed_time:.2f}s")
                return 0.5  # Partial credit for slow but working kernel

            # Enhanced output validation
            if output is None:
                raise ValueError("Custom attention returned None")

            # Shape validation
            expected_shape = x.shape
            if output.shape != expected_shape:
                raise ValueError(f"Wrong output shape: {output.shape}, expected {expected_shape}")

            # Enhanced finite value check
            finite_mask = mx.isfinite(output)
            if not mx.all(finite_mask):
                finite_ratio = float(mx.mean(finite_mask.astype(mx.float32)))
                if finite_ratio < 0.9:
                    raise ValueError(f"Too many non-finite values: {finite_ratio:.2%} finite")
                else:
                    print(f"        ⚠️  Some non-finite values: {finite_ratio:.2%} finite")
                    return 0.7  # Partial credit

            # Enhanced statistical validation
            output_mean = float(mx.mean(output))
            output_std = float(mx.std(output))
            output_max = float(mx.max(mx.abs(output)))

            # More lenient bounds for complex kernels
            if abs(output_mean) > 10.0:
                print(f"        ⚠️  Large mean: {output_mean:.6f}")
                return 0.6

            if output_std > 100.0 or output_std < 0.00001:
                print(f"        ⚠️  Unusual std: {output_std:.6f}")
                return 0.6

            if output_max > 1000.0:
                print(f"        ⚠️  Large max value: {output_max:.6f}")
                return 0.7

            # All checks passed
            return 1.0

        except MetalKernelSafetyError as e:
            raise e  # Re-raise safety errors
        except Exception as e:
            error_msg = str(e)
            if any(
                keyword in error_msg.lower()
                for keyword in ["metal", "kernel", "gpu", "command buffer"]
            ):
                raise GPUCommandBufferError(f"GPU execution error: {error_msg}")
            else:
                raise ValueError(f"Sequence test error: {error_msg}")
