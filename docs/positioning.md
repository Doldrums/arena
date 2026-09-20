# Empira: an arena for recursive self-improvement

Empira provides scientific tasks and experiment records for studying recursive self-improvement (RSI). Its participants are systems that may modify their own research methods: search procedures, memory, tools, code or learning algorithms. The central question is whether a system's modifications improve its ability to produce further improvements.

Arena owns the task catalog, environment and evaluation contracts, participant registry, run lifecycle, records and comparison. Participating frameworks own their search, memory, learning algorithms and state. RSI is the research target; each participant's actual mechanisms and evidence remain explicit.

## Connection to the Era of Experience

Silver and Sutton describe continual learning through interaction with an environment, with observations and consequences informing future behavior. They include adaptation through context as well as neural-network weight updates. This supplies a broader motivation for studying systems that revise their methods through experience. [Welcome to the Era of Experience](https://storage.googleapis.com/deepmind-media/Era-of-Experience%20/The%20Era%20of%20Experience%20Paper.pdf).

Learning from experience is broader than RSI. A system can adapt its behavior without improving the process by which it learns or conducts research. Empira's RSI question concerns that process itself and requires comparisons across system revisions and subsequent research. Saving a trace, changing code or improving one solution does not by itself establish recursive improvement. This is Empira's research framing, not an RSI result attributed to Silver and Sutton.

## The intended combination

- **Tasks and systems keep developing.** Reviewed contributions can introduce new questions, task versions and research-system versions. Continuous discovery is intended to feed both sides of this evolving catalog.
- **Experience remains inspectable.** Outcomes, failures, source revisions, checkpoints and costs provide the record needed to understand what changed between attempts.
- **Research methods can be studied directly.** Comparisons can examine memory, tools, search procedures and system revisions alongside the solutions they produce.
- **Participants retain their native mechanisms.** Shared evaluation conditions and records support comparison while each framework keeps its own research process and detailed views.

These are product priorities, not claims of being first or unique. RE-Bench already supplies open-ended ML research engineering environments and a common task format. [RE-Bench](https://github.com/METR/RE-Bench). ScienceAgentBench already evaluates scientific programs, execution results and costs. [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench). Empira's intended emphasis is the study of systems that modify their research methods, using versioned tasks and records of subsequent experiments.

## Current and incoming

**Working now:** the catalog, versioned participant declarations, registry validation, local SCiEL experiment observer and Cloudflare catalog UI described in the [README](../README.md#working-now). Registration is separate from executable integration; no framework launch adapter is integrated yet.

**Incoming — integration in progress:** according to the project owner, a coauthor is developing continuous discovery and parsing of both research tasks and RSI/self-improving research systems in another workstream. That work will be merged later. It is not implemented in this checkout. The existing PR registry is the contribution path, not evidence of an operating discovery pipeline.

Runner integration, shared execution and longitudinal comparisons remain planned milestones. New catalog versions do not automatically launch experiments or establish compatibility.

## Practical English messaging

**Hero:** An arena for recursive self-improvement.

**Description:** Scientific tasks and experiment records for studying systems that modify their own research methods.

**Contribution labels:** Research tasks · RSI systems.

**Research cycle:** System revision → Experiment → Evidence → Method revision → Further experiments.

**Research question:** Do changes to a system's research methods improve its subsequent research?

Capability labels retain the current/incoming distinction above. Learning from experience is the broader context; recursive self-improvement is the specific object of study. Neither registration nor a successful task result establishes RSI.
