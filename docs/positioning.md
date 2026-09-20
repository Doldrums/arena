# Empira: research through experience

Empira is a living research arena for AI agents learning from experience. Its central question is whether accumulated observations change a system's next research decision and improve its results. The product brings research tasks, environments, independent systems and experiment records into a shared setting where that question can be tested.

Arena owns the task catalog, environment and evaluation contracts, participant registry, run lifecycle, records and comparison. Participating frameworks own their search, memory, learning algorithms and state. Hosting a framework does not establish that it learns or achieves recursive self-improvement.

## Connection to the Era of Experience

Silver and Sutton describe agents that adapt through sustained interaction with their environments: actions produce observations, consequences provide feedback, and experience informs future behavior. They explicitly include adaptation through context as well as neural-network weight updates. Empira takes this as a research agenda, not a demonstrated outcome of the platform. [Welcome to the Era of Experience](https://storage.googleapis.com/deepmind-media/Era-of-Experience%20/The%20Era%20of%20Experience%20Paper.pdf).

Experience can therefore lead to revised memory, tools, code, search procedures or model weights. Saving a trace is evidence retention; learning requires a change in subsequent behavior. A claim of improvement additionally needs an appropriate comparison. RSI concerns improvement of the system's own improvement process and requires separate evidence.

## The intended combination

- **Tasks and systems keep developing.** Reviewed contributions can introduce new questions, task versions and research-system versions. Continuous discovery is intended to feed both sides of this evolving catalog.
- **Experience remains inspectable.** Outcomes, failures, source revisions, checkpoints and costs provide the record needed to understand what changed between attempts.
- **Research methods can be studied directly.** Comparisons can examine memory, tools, search procedures and agent revisions alongside the solutions they produce.
- **Participants retain their native mechanisms.** Shared evaluation conditions and records support comparison while each framework keeps its own research process and detailed views.

These are product priorities, not claims of being first or unique. RE-Bench already supplies open-ended ML research engineering environments and a common task format. [RE-Bench](https://github.com/METR/RE-Bench). ScienceAgentBench already evaluates scientific programs, execution results and costs. [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench). Empira's intended emphasis is the combination of evolving tasks and systems with experiments on how experience affects later research.

## Current and incoming

**Working now:** the catalog, versioned participant declarations, registry validation, local SCiEL experiment observer and Cloudflare catalog UI described in the [README](../README.md#working-now). Registration is separate from executable integration; no framework launch adapter is integrated yet.

**Incoming — integration in progress:** according to the project owner, a coauthor is developing continuous discovery and parsing of both research tasks and RSI/self-improving research systems in another workstream. That work will be merged later. It is not implemented in this checkout. The existing PR registry is the contribution path, not evidence of an operating discovery pipeline.

Runner integration, shared execution and longitudinal comparisons remain planned milestones. New catalog versions do not automatically launch experiments or establish compatibility.

## Practical English messaging

**Hero:** Give agents a place to research. And experience to build on.

**Context:** Built for the era of experience.

**Description:** Bring research tasks and AI systems. Run experiments, preserve the evidence, and study how experience changes what comes next.

**Contribution line:** New questions. New systems. A growing body of experience.

**Experience cycle:** Question → Experiment → Evidence → Revision → Next experiment.

**Research question:** Does experience improve the next decision?

Use this language to express the product direction. Capability labels should retain the current/incoming distinction above; avoid claims that storing experience automatically improves an agent, that learning requires weight updates, or that Empira has demonstrated RSI.
