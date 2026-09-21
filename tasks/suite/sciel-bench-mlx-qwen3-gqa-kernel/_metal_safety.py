"""MetalSafety implementation for the bundled MLX task."""
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


class MetalSafety:

    def _validate_metal_kernel_safety(self, custom_attention_class: Any) -> Dict[str, Any]:
        """Pre-execution validation of Metal kernel safety"""
        try:
            print("  🔍 Validating Metal kernel safety parameters...")

            # Mock arguments for safety testing
            class MockArgs:
                # NOTE: This should reflect the default model used by this evaluator:
                # `mlx-community/Qwen3-0.6B-bf16` (16 Q heads : 8 KV heads, head_dim=128).
                hidden_size = 2048
                num_attention_heads = 16
                num_key_value_heads = 8
                head_dim = 128
                rms_norm_eps = 1e-06
                rope_theta = 1000000
                rope_scaling = None
                max_position_embeddings = 40960

            args = MockArgs()

            # Try to instantiate with safety checks
            try:
                instance = custom_attention_class(args)
                if instance is None:
                    return {"success": False, "error": "Failed to instantiate custom attention"}

                print("  ✅ Custom attention instantiation successful")

                # Basic parameter validation (should match the args we instantiated with)
                if hasattr(instance, "n_heads") and instance.n_heads != args.num_attention_heads:
                    return {
                        "success": False,
                        "error": f"Invalid head count: {instance.n_heads} (expected {args.num_attention_heads})",
                    }

                if (
                    hasattr(instance, "n_kv_heads")
                    and instance.n_kv_heads != args.num_key_value_heads
                ):
                    return {
                        "success": False,
                        "error": f"Invalid KV head count: {instance.n_kv_heads}",
                    }

                return {"success": True, "validated": True}

            except Exception as e:
                error_msg = str(e)
                if any(keyword in error_msg.lower() for keyword in ["metal", "kernel", "gpu"]):
                    self.metal_compilation_errors += 1
                return {"success": False, "error": f"Instantiation failed: {error_msg}"}

        except Exception as e:
            self.total_metal_errors += 1
            return {"success": False, "error": f"Safety validation error: {e}"}

    def _bulletproof_execute_with_gpu_protection(self, func) -> Tuple[bool, Any]:
        """Execute function with maximum GPU and Metal kernel protection"""
        try:
            # Clear any existing GPU state
            mx.eval(mx.array([1.0]))  # Simple operation to ensure GPU is responsive

            # Execute with comprehensive error catching
            result = func()
            return True, result

        except RuntimeError as e:
            error_msg = str(e)

            # Classify specific Metal/GPU errors
            if "kIOGPUCommandBufferCallbackErrorInvalidResource" in error_msg:
                self.metal_command_buffer_errors += 1
                self.total_metal_errors += 1
                return False, f"GPU Command Buffer Error (memory violation): {error_msg}"
            elif "METAL" in error_msg.upper():
                self.metal_memory_violations += 1
                self.total_metal_errors += 1
                return False, f"Metal Memory Violation: {error_msg}"
            elif any(keyword in error_msg.lower() for keyword in ["gpu", "metal", "kernel"]):
                self.gpu_resource_errors += 1
                self.total_metal_errors += 1
                return False, f"GPU Resource Error: {error_msg}"
            else:
                return False, f"Runtime Error: {error_msg}"

        except Exception as e:
            error_msg = str(e)

            # Additional classification for other Metal-related exceptions
            if any(
                keyword in error_msg.lower() for keyword in ["metal", "kernel", "gpu", "mps", "mtl"]
            ):
                self.total_metal_errors += 1
                return False, f"General Metal Error: {error_msg}"
            else:
                return False, f"Execution Error: {error_msg}"

    def _gpu_protected_measure_baseline(self) -> Optional[List[BenchmarkResult]]:
        """GPU-protected baseline measurement with enhanced error handling"""
        try:
            print("  📊 Running GPU-protected baseline benchmark...")

            # Ensure clean GPU state
            self._ensure_clean_gpu_state()
            self._ensure_standard_attention()

            # Get baseline configurations
            baseline_configs = self._get_safe_benchmark_configs()
            if not baseline_configs:
                print("  ❌ No safe benchmark configurations available")
                return None

            baseline_results = []
            successful_count = 0

            for i, config in enumerate(baseline_configs, 1):
                print(f"  [{i}/{len(baseline_configs)}] GPU-protected baseline: {config.name}")

                retry_count = 0
                while retry_count <= self.max_retry_attempts:
                    try:
                        # Clean GPU state before each attempt
                        self._ensure_clean_gpu_state()

                        # Run with GPU protection
                        success, result = self._bulletproof_execute_with_gpu_protection(
                            lambda: self.benchmark_suite.run_single_benchmark(config)
                        )

                        if success and result:
                            baseline_results.append(result)
                            successful_count += 1
                            print(
                                f"    ✅ GPU-protected {config.name}: {result.decode_tokens_per_sec:.1f} tokens/sec"
                            )
                            break
                        else:
                            if retry_count < self.max_retry_attempts:
                                print(f"    🔄 Retry {retry_count + 1}: {result}")
                                retry_count += 1
                                time.sleep(self.retry_base_delay * (2**retry_count))
                                continue
                            else:
                                print(f"    ❌ All retries exhausted for {config.name}: {result}")
                                break

                    except Exception as e:
                        if retry_count < self.max_retry_attempts:
                            print(f"    🔄 Exception retry {retry_count + 1}: {e}")
                            retry_count += 1
                            time.sleep(self.retry_base_delay * (2**retry_count))
                            continue
                        else:
                            print(f"    ❌ Final exception for {config.name}: {e}")
                            break

            # Check success rate
            min_required = max(2, len(baseline_configs) * 0.5)  # At least 50% success
            if successful_count < min_required:
                print(
                    f"  ❌ Insufficient baseline results: {successful_count}/{len(baseline_configs)}"
                )
                return None

            # Store baseline metrics
            self._store_enhanced_baseline_metrics(baseline_results)
            print(f"  ✅ GPU-protected baseline complete ({successful_count} successful)")

            return baseline_results

        except Exception as e:
            print(f"  ❌ GPU-protected baseline measurement failed: {e}")
            return None

    def _ensure_clean_gpu_state(self):
        """Ensure clean GPU state before operations"""
        try:
            # Simple operation to ensure GPU responsiveness
            test_op = mx.array([1.0, 2.0, 3.0])
            mx.eval(test_op * 2)

            # Small delay to let GPU settle
            time.sleep(0.1)

        except Exception as e:
            print(f"    ⚠️  GPU state cleanup warning: {e}")

    def _gpu_protected_apply_hook(self, custom_attention_class: Any) -> Dict[str, Any]:
        """GPU-protected application of custom attention hook"""
        try:
            success, result = self._bulletproof_execute_with_gpu_protection(
                lambda: self._apply_attention_hook_safely(custom_attention_class)
            )

            if success:
                return {"success": True, "original": result}
            else:
                return {"success": False, "error": result}

        except Exception as e:
            return {"success": False, "error": f"GPU-protected hook application failed: {e}"}

    def _apply_attention_hook_safely(self, custom_attention_class: Any) -> Any:
        """Safely apply attention hook"""
        import mlx_lm.models.qwen3 as qwen3_module

        # Store original attention class
        original_attention = getattr(qwen3_module, "Attention", None)
        if original_attention is None:
            raise RuntimeError("Could not find original Attention class")

        # Apply custom attention
        qwen3_module.Attention = custom_attention_class

        # Verify the hook was applied
        if qwen3_module.Attention != custom_attention_class:
            raise RuntimeError("Hook application verification failed")

        print("      ✅ Custom attention hook applied with GPU protection")
        return original_attention

    def _gpu_protected_remove_hook(self, original_attention: Any):
        """GPU-protected removal of custom attention hook"""
        try:
            success, result = self._bulletproof_execute_with_gpu_protection(
                lambda: self._remove_attention_hook_safely(original_attention)
            )

            if not success:
                print(f"      ⚠️  Hook removal warning: {result}")

        except Exception as e:
            print(f"      ⚠️  Hook removal error (non-fatal): {e}")

    def _remove_attention_hook_safely(self, original_attention: Any):
        """Safely remove attention hook"""
        import mlx_lm.models.qwen3 as qwen3_module

        qwen3_module.Attention = original_attention
        print("      ✅ Hook removed with GPU protection")

    def _create_bulletproof_execution_environment(self) -> Dict[str, Any]:
        """Create bulletproof execution environment with enhanced imports"""
        import math
        import numpy as np
        import time
        from typing import Optional, Tuple, Any

        exec_globals = {
            "__builtins__": __builtins__,
            "mx": mx,
            "nn": nn,
            "np": np,
            "math": math,
            "time": time,
            "Optional": Optional,
            "Tuple": Tuple,
            "Any": Any,
        }

        # Enhanced MLX-LM import with error handling
        try:
            exec_globals["mlx_lm"] = __import__("mlx_lm")
            print("  ✅ MLX-LM imported for bulletproof execution")
        except ImportError:
            print("  ⚠️  MLX-LM not available for bulletproof execution")
        except Exception as e:
            print(f"  ⚠️  MLX-LM import error in bulletproof environment: {e}")

        return exec_globals

    def _ensure_standard_attention(self):
        """Ensure standard attention is active"""
        try:
            import mlx_lm.models.qwen3 as qwen3_module

            if hasattr(self, "_original_attention") and self._original_attention:
                qwen3_module.Attention = self._original_attention
                print("  🔄 Restored standard attention for baseline")
        except ImportError:
            print("  ⚠️  Could not access qwen3 module for standard attention")
