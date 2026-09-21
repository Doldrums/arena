# Quantum information: shallow-circuit Ising ground states

**Source collection:** [Quantum information: source-based research tasks](../../papers/science-quantum.md)\
**Task id:** `science-quantum-ising-vqe`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Optimize parameters of a fixed three-layer Ry/CZ circuit to approximate ground states of open transverse-field Ising chains. The evaluator builds each state itself and minimizes the mean energy gap per spin relative to an independent exact eigensolution.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

angles(n, coupling, field, layers) -> finite real array (layers,n) in radians. H=-coupling*sum Z_i Z_(i+1)-field*sum X_i, open chain, qubit i is bit i. Start |0>^n; each layer applies Ry(theta) to every qubit; between layers apply CZ on every adjacent pair in ascending order. No entangler after final layer. Fixed layers=3, n=4,6, coupling=1, fields=0.45,1,1.65. Objective: mean (circuit energy - exact ground energy)/n. Development fields: 0.3,0.8,1.4. Return circuit parameters, not a statevector or reported energy.

Parameters: `{"layers": 3, "qubits": [4, 6], "fields": [0.45, 1.0, 1.65]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `quantum_information`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Optimize a fixed three-layer variational circuit for small open-chain Ising Hamiltonians.

Why it matters: Qualifying evidence that this local task addresses a primary scientific problem has not been established.


The reviewed hardware-efficient VQE paper (https://arxiv.org/abs/1704.05018) chiefly demonstrates a quantum eigensolver, with quantum magnetism used to show its flexibility. It does not establish the local fixed-ansatz Ising benchmark as a primary investigation of a physical question. Further problem-focused evidence is needed; this is not a finding that Ising physics is scientifically unimportant.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Variational principle from Peruzzo et al. and shallow-circuit optimization motivated by Kandala et al.; this exact Ry/CZ ansatz and ideal transverse-field Ising test suite are local choices. Dense eigensolutions independently establish reference energies. No hardware noise, molecular data, quantum-advantage or published-score reproduction claim.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/1304.3061v3 (Peruzzo et al. (2014), variational eigenvalue estimation and Rayleigh-Ritz energy minimization.)
- paper: https://arxiv.org/abs/1704.05018v2 (Kandala et al. (2017), hardware-efficient variational circuits and quantum magnetism application; motivation rather than a copied ansatz.)

## Limitations

- The open Ising Hamiltonian, exact Ry/CZ ansatz, field values and statevector simulator are local reduced choices, not the molecular experiments in the papers.
- No noise, measurement cost or hardware connectivity penalty is modeled. A lower circuit energy does not establish a new physical ground-state result or quantum advantage.
- The minimum within the restricted ansatz can exceed the exact ground energy; zero error is not assumed reachable.
