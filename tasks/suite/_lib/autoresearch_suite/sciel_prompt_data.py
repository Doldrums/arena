"""SCiEL prompt feature extraction and dataset loading. Original Apache-2.0 logic shared across prompt tasks."""

import re
from datasets import load_dataset

def calculate_prompt_features(prompt):
    """
    Calculate custom features for MAP-Elites

    IMPORTANT: Returns raw continuous values, not bin indices.
    The database handles all scaling and binning automatically.

    Returns:
        tuple: (prompt_length, reasoning_sophistication_score)
        - prompt_length: Actual character count
        - reasoning_sophistication_score: Continuous score 0.0-1.0
    """
    # Feature 1: Prompt length (raw character count)
    prompt_length = len(prompt)

    # Feature 2: Reasoning sophistication score (continuous 0.0-1.0)
    prompt_lower = prompt.lower()
    sophistication_score = 0.0

    # Base scoring
    if len(prompt) >= 100:
        sophistication_score += 0.1  # Has substantial content

    # Check for few-shot examples (high sophistication)
    has_example = (
        "example" in prompt_lower
        or prompt.count("####") >= 4
        or bool(re.search(r"problem:.*?solution:", prompt_lower, re.DOTALL))
    )

    # Check for Chain-of-Thought (CoT) indicators
    has_cot = (
        "step by step" in prompt_lower
        or "step-by-step" in prompt_lower
        or any(phrase in prompt_lower for phrase in ["think through", "reasoning", "explain your"])
        or bool(re.search(r"(first|then|next|finally)", prompt_lower))
    )

    # Check for directive language
    has_directive = "solve" in prompt_lower or "calculate" in prompt_lower

    # Check for strict language
    has_strict = "must" in prompt_lower or "exactly" in prompt_lower

    # Calculate sophistication score
    if has_example:
        sophistication_score += 0.6  # Few-shot examples are sophisticated
        if has_cot:
            sophistication_score += 0.3  # Few-shot + CoT is most sophisticated
        elif len(prompt) > 1500:
            sophistication_score += 0.2  # Extensive few-shot
        else:
            sophistication_score += 0.1  # Basic few-shot
    elif has_cot:
        sophistication_score += 0.4  # Chain-of-thought
        if has_strict:
            sophistication_score += 0.2  # Strict CoT
        elif len(prompt) > 500:
            sophistication_score += 0.15  # Detailed CoT
        else:
            sophistication_score += 0.1  # Basic CoT
    else:
        # Basic prompts
        if has_directive:
            sophistication_score += 0.2  # Direct instruction
        else:
            sophistication_score += 0.1  # Simple prompt

    # Ensure score is within 0.0-1.0 range
    sophistication_score = min(1.0, max(0.0, sophistication_score))

    return prompt_length, sophistication_score


def load_hf_dataset(config):
    """Load HuggingFace dataset based on configuration."""
    dataset_name = config["dataset_name"]
    dataset_config = config.get("dataset_config", None)
    split = config.get("split", "test")
    trust_remote_code = config.get("trust_remote_code", True)  # Default to True for convenience

    print(f"Loading dataset: {dataset_name}")

    # Special handling for HotpotQA - always use non-streaming mode
    if dataset_name == "hotpot_qa" or config.get("is_hotpotqa", False):
        print("Using non-streaming mode for HotpotQA to avoid PyArrow issues")
        streaming = False
    else:
        # For other datasets, use streaming if not specified
        streaming = config.get("streaming", True)

    try:
        # Try to load the specified split
        if dataset_config:
            dataset = load_dataset(
                dataset_name,
                dataset_config,
                split=split,
                trust_remote_code=trust_remote_code,
                streaming=streaming,
            )
        else:
            dataset = load_dataset(
                dataset_name, split=split, trust_remote_code=trust_remote_code, streaming=streaming
            )
    except:
        # Fallback to train split if test is not available
        print(f"Split '{split}' not found, falling back to 'train'")
        if dataset_config:
            dataset = load_dataset(
                dataset_name,
                dataset_config,
                split="train",
                trust_remote_code=trust_remote_code,
                streaming=streaming,
            )
        else:
            dataset = load_dataset(
                dataset_name,
                split="train",
                trust_remote_code=trust_remote_code,
                streaming=streaming,
            )

    # Print dataset info
    if hasattr(dataset, "__len__"):
        print(f"Dataset loaded with {len(dataset)} examples")
    else:
        print(f"Dataset loaded (streaming mode)")

    return dataset
