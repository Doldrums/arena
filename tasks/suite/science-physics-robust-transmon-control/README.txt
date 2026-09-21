# Robust multilevel quantum-control pulses

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-robust-transmon-control`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

pulse(target_gate, hardware_model) -> (80,2) IQ amplitudes rad/ns for 40 ns X-pi gate in a three-level Duffing transmon. Enforce amplitude .4 rad/ns and slew .12 rad/ns/ns including endpoints. Independent Lindblad expm and refined DOP853 evaluate six Bloch states over 3x3 detuning/calibration cases, relaxation and dephasing. Score mean plus worst average gate infidelity; report leakage. Explicit simulation, not QuOCS benchmark reproduction.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

pulse(target_gate, hardware_model) -> (80,2) IQ amplitudes rad/ns for 40 ns X-pi gate in a three-level Duffing transmon. Enforce amplitude .4 rad/ns and slew .12 rad/ns/ns including endpoints. Independent Lindblad expm and refined DOP853 evaluate six Bloch states over 3x3 detuning/calibration cases, relaxation and dephasing. Score mean plus worst average gate infidelity; report leakage. Explicit simulation, not QuOCS benchmark reproduction.

Parameters: `{"proposal_id": "P12"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `quantum_information`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Implement fast, accurate gates in weakly anharmonic superconducting qubits while suppressing leakage.

Why it matters: Leakage suppression during physical qubit control is the paper's central quantum-device problem.

- [Simple pulses for elimination of leakage in weakly nonlinear qubits](https://arxiv.org/abs/0901.0534): Main research objective: Construct control pulses that suppress leakage and enable accurate fast gates in weakly nonlinear qubits. Task connection: The local task optimizes a fixed-duration IQ pulse in an explicit three-level Duffing/Lindblad model with detuning and calibration uncertainty. Its ensemble, pulse discretization, bounds, and loss are local choices, not a reproduction of the paper's experimental performance.

The cited work solves a concrete control error mechanism, so a generic optimal-control toolkit citation is unnecessary.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent SCIEL scientific adaptation. Required source packs never fall back to toy data. Fixture tests are distinct from source-data execution. See docs/PHYSICS_EXPANSION.md.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/abs/2212.11144 (Scientific problem, assumptions and evaluation methodology: Robust multilevel quantum-control pulses)
- repository: https://github.com/Quantum-OCS/QuOCS (Optimal-control problem formulation; independent explicit qutrit/Lindblad adaptation, no author pulse reuse.)
- paper: https://arxiv.org/abs/0901.0534 (Develops control pulses that suppress leakage in multilevel superconducting qubits and evaluates gate error. Local robust pulse optimization across parameter uncertainty extends that same control task.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- No external dataset: fully specified physical-model simulation.
