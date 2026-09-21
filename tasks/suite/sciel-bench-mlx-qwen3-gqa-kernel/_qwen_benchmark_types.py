"""Value types shared by Qwen benchmark components."""
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Single benchmark result"""

    name: str
    prompt_tokens: int
    generated_tokens: int
    prefill_tokens_per_sec: float
    decode_tokens_per_sec: float
    total_tokens_per_sec: float
    peak_memory_gb: float
    total_time_sec: float
    prompt: str
    generated_text: str


@dataclass
class BenchmarkConfig:
    """Benchmark configuration"""

    name: str
    prompt: str
    max_tokens: int
    description: str
