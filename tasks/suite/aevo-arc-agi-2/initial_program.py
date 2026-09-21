"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def _grid(g):
    return "\n".join(" ".join(str(v) for v in row) for row in g)


def solve(task, llm):
    prompt = ("You are solving an ARC puzzle. Infer the transformation from the examples and output the test output grid "
              "only, as rows of space-separated digits.\n\n")
    for example in task["train"]:
        prompt += "Input:\n" + _grid(example["input"]) + "\nOutput:\n" + _grid(example["output"]) + "\n\n"
    outputs = []
    for test in task["test"]:
        text = llm(prompt + "Input:\n" + _grid(test["input"]) + "\nOutput:\n", max_tokens=2000)
        rows = [[int(v) for v in line.split()] for line in text.strip().splitlines() if line.split() and all(t.isdigit() for t in line.split())]
        outputs.append(rows)
    return outputs
# EVOLVE-BLOCK-END
