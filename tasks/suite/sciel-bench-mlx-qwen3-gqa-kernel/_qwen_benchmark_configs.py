"""BenchmarkConfigurations implementation for the bundled MLX task."""
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


class BenchmarkConfigurations:

    def create_benchmark_configs(self) -> List[BenchmarkConfig]:
        """Create comprehensive benchmark configurations"""

        configs = []

        # 1. Context Length Variations
        configs.extend(
            [
                BenchmarkConfig(
                    name="short_context_quick",
                    prompt="Brief answer: What is artificial intelligence?",
                    max_tokens=50,
                    description="Short context, quick response - chat scenario",
                ),
                BenchmarkConfig(
                    name="medium_context_analysis",
                    prompt=self._create_medium_context_prompt(),
                    max_tokens=200,
                    description="Medium context, analytical response",
                ),
                BenchmarkConfig(
                    name="long_context_detailed",
                    prompt=self._create_long_context_prompt(),
                    max_tokens=500,
                    description="Long context, detailed analysis",
                ),
                BenchmarkConfig(
                    name="very_long_context_comprehensive",
                    prompt=self._create_very_long_context_prompt(),
                    max_tokens=1000,
                    description="Very long context, comprehensive response",
                ),
            ]
        )

        # 2. Generation Length Patterns
        configs.extend(
            [
                BenchmarkConfig(
                    name="micro_generation",
                    prompt="Complete this sentence: The future of AI is",
                    max_tokens=10,
                    description="Micro generation - attention prefill dominated",
                ),
                BenchmarkConfig(
                    name="short_generation",
                    prompt="Explain in one paragraph: What makes transformers effective?",
                    max_tokens=100,
                    description="Short generation - balanced prefill/decode",
                ),
                BenchmarkConfig(
                    name="long_generation",
                    prompt="Write a detailed technical explanation of how neural networks learn:",
                    max_tokens=1000,
                    description="Long generation - decode performance critical",
                ),
                BenchmarkConfig(
                    name="very_long_generation",
                    prompt="Write a comprehensive guide to machine learning for beginners:",
                    max_tokens=2000,
                    description="Very long generation - sustained decode performance",
                ),
                BenchmarkConfig(
                    name="ultra_long_generation",
                    prompt="The future of AI is",
                    max_tokens=5000,
                    description="Ultra long generation - memory scaling test",
                ),
            ]
        )

        # 3. Different Use Case Patterns
        configs.extend(
            [
                BenchmarkConfig(
                    name="code_generation",
                    prompt="""Write a Python function to implement binary search:

def binary_search(arr, target):
    \"\"\"
    Implement binary search algorithm
    Args:
        arr: sorted array
        target: element to find
    Returns:
        index of target or -1 if not found
    \"\"\"
""",
                    max_tokens=300,
                    description="Code generation - structured output patterns",
                ),
                BenchmarkConfig(
                    name="step_by_step_reasoning",
                    prompt="""Solve this step by step:

A train travels from City A to City B at 80 mph. The distance is 240 miles. 
If it leaves at 2:00 PM, what time will it arrive? Show your work.""",
                    max_tokens=400,
                    description="Step-by-step reasoning - logical sequence patterns",
                ),
                BenchmarkConfig(
                    name="creative_writing",
                    prompt="""Write a short story about a robot who discovers emotions for the first time. 
Include dialogue and describe the robot's internal experience as it learns about feelings like 
joy, sadness, and wonder. Make it engaging and thoughtful.""",
                    max_tokens=800,
                    description="Creative writing - diverse vocabulary and narrative",
                ),
                BenchmarkConfig(
                    name="technical_documentation",
                    prompt="""Create comprehensive documentation for a REST API with the following endpoints:
- GET /users - List all users
- POST /users - Create new user  
- GET /users/{id} - Get specific user
- PUT /users/{id} - Update user
- DELETE /users/{id} - Delete user

Include request/response examples, error codes, and authentication details.""",
                    max_tokens=1200,
                    description="Technical documentation - structured information",
                ),
                BenchmarkConfig(
                    name="conversational_assistant",
                    prompt="""You are a helpful AI assistant. A user asks:

"I'm planning a trip to Japan for 2 weeks. I've never been there before. I like 
history, food, and nature. I have a moderate budget. Can you help me plan an 
itinerary with recommendations for cities to visit, things to do, and travel tips?"

Provide a detailed, helpful response:""",
                    max_tokens=1500,
                    description="Conversational assistant - helpful response patterns",
                ),
            ]
        )

        # 4. Memory Pressure Scenarios
        configs.extend(
            [
                BenchmarkConfig(
                    name="progressive_context_building",
                    prompt=self._create_progressive_context_prompt(),
                    max_tokens=600,
                    description="Progressive context building - KV cache growth",
                ),
                BenchmarkConfig(
                    name="repetitive_pattern_generation",
                    prompt="Generate a list of 100 creative product names for a tech startup, with explanations:",
                    max_tokens=2000,
                    description="Repetitive patterns - memory efficiency test",
                ),
            ]
        )

        # 5. Extended Long Generation Tests (for sustained decode performance)
        configs.extend(
            [
                BenchmarkConfig(
                    name="extreme_long_generation",
                    prompt="Write a complete tutorial on deep learning from basics to advanced topics, including mathematical foundations, architectures, training techniques, and real-world applications:",
                    max_tokens=8000,
                    description="Extreme long generation - maximum decode performance test",
                ),
                BenchmarkConfig(
                    name="sustained_dialogue_generation",
                    prompt="Create a detailed dialogue between an AI researcher and a software engineer discussing the future of artificial intelligence, covering topics like AGI, safety, ethics, and technological implications. Make it engaging and informative:",
                    max_tokens=6000,
                    description="Sustained dialogue - consistent long-form generation",
                ),
                BenchmarkConfig(
                    name="comprehensive_analysis_generation",
                    prompt="Analyze the evolution of computer programming languages from assembly to modern high-level languages. Discuss paradigms, performance considerations, developer productivity, and future trends:",
                    max_tokens=7000,
                    description="Comprehensive analysis - complex reasoning with long output",
                ),
                BenchmarkConfig(
                    name="maximum_context_stress_test",
                    prompt=self._create_maximum_context_prompt(),
                    max_tokens=10000,
                    description="Maximum context stress test - ultimate performance challenge",
                ),
            ]
        )

        return configs
