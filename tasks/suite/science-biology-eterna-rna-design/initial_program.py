"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import random

def design(dot_bracket, constraints, oracle):
    rng = random.Random(17)
    stack, pairs = [], []
    for i, c in enumerate(dot_bracket):
        if c == "(": stack.append(i)
        elif c == ")": pairs.append((stack.pop(), i))
    current = list("A" * len(dot_bracket))
    for a,b in pairs: current[a],current[b] = "G","C"
    for i,c in enumerate(constraints):
        if c != "N": current[i] = c
    best = "".join(current); best_error = len(best)+1
    for iteration in range(oracle.budget):
        trial = list(best)
        if iteration:
            if pairs and rng.random() < .8:
                a,b = rng.choice(pairs); pair = rng.choice(["AU","UA","CG","GC","GU","UG"])
                if constraints[a] == "N": trial[a] = pair[0]
                if constraints[b] == "N": trial[b] = pair[1]
            else:
                free = [i for i,c in enumerate(constraints) if c == "N"]
                if free: trial[rng.choice(free)] = rng.choice("ACGU")
        sequence = "".join(trial)
        folded, energy = oracle(sequence)
        error = sum(a != b for a,b in zip(folded,dot_bracket))
        if error <= best_error: best,best_error = sequence,error
        if error == 0: return sequence
    return best
# EVOLVE-BLOCK-END
