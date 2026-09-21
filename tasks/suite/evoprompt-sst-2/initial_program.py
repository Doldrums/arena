"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def solve(question, llm):
    """Zero-shot chain-of-thought prompt; the last line of the reply is taken as the answer."""
    system = "You are a careful expert. Think step by step, then finish with a final line of the form 'Answer: <answer>'."
    return llm(question + "\n\nThink step by step and end with 'Answer: <answer>'.", system=system, max_tokens=1024)
# EVOLVE-BLOCK-END
