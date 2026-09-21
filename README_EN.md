# Mathematical Modeling Guidance

[简体中文](README.md) | **English**

> A Git-based workspace for AI-assisted mathematical modeling.

[![CI](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml/badge.svg)](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/Python-3.11%E2%80%933.13-3572A5)](requirements.txt)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-2E8B57)](LICENSE-CODE.md)
[![Content: CC BY 4.0](https://img.shields.io/badge/Content-CC_BY_4.0-2E8B57)](LICENSE-CONTENT.md)

A Git project workspace designed to complement mathematical-modeling Skills: AI continuously advances modeling, computation, and paper delivery, while humans focus on consequential decisions.

[Positioning](#positioning) · [Advantages](#advantages) · [Getting started](#getting-started) · [Continuity and collaboration](#continuity-and-collaboration) · [Papers and project evidence](#papers-and-project-evidence) · [Documentation](#documentation)

## Positioning

This repository provides a reusable way to organize a modeling project. Governance rules define human and AI responsibilities, project files preserve facts and current state, Git manages changes, and the model, code, results, and paper remain connected. It is intended for mathematical-modeling work that spans multiple conversations, sustained computation, or team collaboration.

**This repository is a workflow tool that complements a Skill. It is not a Skill installed into an agent or a one-prompt paper generator.** A Skill supplies execution methods for modeling, programming, research, and document production; this repository supplies persistent project boundaries, records, and delivery structure.

The recommended setup combines contest routing with modeling execution: [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) handles contest routing, rule boundaries, and phase continuity for CUMCM, MCM/ICM, and the Diangong Cup, while [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill) supplies modeling analysis, computational implementation, and paper-delivery capabilities. Other mathematical-modeling Skills are also suitable when they can read repository files, run commands, and follow `AGENTS.md`.

| Component | Responsibility |
|---|---|
| Agent and external Skills | Understand the task, select methods and tools, and perform analysis, coding, computation, and writing |
| This repository | Organize task inputs, consequential decisions, current state, implementation, evidence, and papers, and define how they connect |
| Git, optionally with GitHub | Preserve versions, compare changes, isolate branches, recover history, synchronize remotely, and support collaboration |
| Humans | Decide matters that change problem meaning, important constraints, substantive scope, or interpretation of conclusions |

The repository provides rules, method guides, formatting profiles, shared utilities, and real projects for reuse. An agent capable of reading and writing project files and running commands applies these conventions. Skills, model services, and project dependencies are configured in the user's own environment.

## Advantages

- **Continuity across conversations.** Consequential decisions and the execution frontier live in project files, so a new conversation can resume from the current state without being distracted by obsolete reasoning or rejected approaches.
- **Stable model semantics.** The original problem owns problem facts, while decision records own accepted model meaning. Implementation and tests proceed from those sources, reducing semantic drift across phases.
- **Continuous AI execution with focused human control.** AI handles routine implementation, numerical choices, experiments, validation, and paper synchronization. Humans decide choices that materially affect problem meaning or conclusions after the relevant analysis is ready.
- **Comparable, isolated, recoverable changes.** Git commits preserve concrete changes, branches hold candidate implementations, and teams can review differences, integrate work, or return to a known version.
- **Traceable paper claims.** Decisions, computation entry points, result files, and figures connect to claims in the paper. When an upstream model or result changes, affected text and deliverables can be updated together.
- **Risk-matched validation.** Checks target concrete failure modes and affected surfaces, directing computation and review toward evidence that can change a decision.

## Getting started

### 1. Obtain the workspace

Prepare Git and an AI coding environment that can access local files and run commands, then configure the recommended Skills above or an equivalent mathematical-modeling Skill. Documentation and papers can be read directly on GitHub; for local use, clone the repository:

```shell
git clone https://github.com/Ash-Rise/math-modeling-guidance.git
cd math-modeling-guidance
```

If you already have a project repository, you can bring in [AGENTS.md](AGENTS.md), the [governance specification](MCM_AI_Governance.md), and the required [shared methods and utilities](shared/), while preserving their paths and license information.

### 2. Add your task

Create a project directory under `projects/`, add the original problem and attachments, and state the objective, resource constraints, and required deliverables. The public examples use `problem-statement.md` as a task summary. A new project should retain the original problem and may add a Markdown reading copy for repeated machine use; the original material remains authoritative for problem facts.

A typical project layout follows. Create only the files the project needs:

```text
projects/my-modeling-project/
├── problem-statement.md   # Readable problem copy; retain originals and attachments separately
├── decisions.md           # Accepted consequential modeling decisions
├── state.md               # Current frontier and next action for a long-running task
├── requirements.txt       # Project runtime dependencies
├── src/                   # Model implementation
├── scripts/               # Solving, reproduction, and figure entry points
├── results/               # Accepted results and supporting evidence
├── tests/                 # Model contracts and regression checks
└── paper/
    ├── figures/           # Figures used in the paper
    ├── paper.md           # Paper content
    ├── paper.docx         # Word deliverable
    └── paper.pdf          # PDF deliverable
```

Before tracking a new project, inspect [.gitignore](.gitignore). Its current exceptions are scoped to the public examples, so add precise exceptions for the new project's decisions, state, accepted results, and deliverables when appropriate.

### 3. Start the agent in the project

Open the agent at the repository root and adapt the following prompt with your project path and delivery requirements:

> Read AGENTS.md at the repository root and locate projects/my-modeling-project. Recover the project from the original problem, decisions.md, and state.md. Read the governance specification and modeling playbook only as needed, and use the configured mathematical-modeling Skill to continue the task. Handle routine technical work autonomously. For consequential semantic choices, first check the relevant authority and complete the analysis, then present a decision recommendation. The current objective is ..., and the required deliverables are ....

The project then follows this main path: organize the problem and data → establish the model and consequential decisions → implement, compute, and validate → accept formal results → write the paper and figures → verify delivery. New evidence may trigger a local revision, with dependent artifacts updated downstream.

The Python examples recommend versions 3.11–3.13 and a project virtual environment using the relevant `requirements.txt`. Each project README lists its commands. Word and PDF generation depend on the document tools and delivery path supplied by the configured Skill. See [Getting Started](docs/getting-started.md) for more detail.

## Continuity and collaboration

### Humans handle consequential decisions

AI continuously handles problem organization, investigation, model implementation, experiments, computation, figures, validation, state maintenance, and paper synchronization. Important technical choices that affect numerical quality, reproducibility, or efficiency may proceed autonomously and be reported at a meaningful phase boundary.

Humans decide choices involving problem interpretation, model meaning, important assumptions, objectives, hard constraints, evaluation semantics, allowed resources, substantive scope, or interpretation of conclusions. Before asking, AI checks the original problem and accepted decisions, eliminates unsupported alternatives, and completes enough analysis to present a grounded recommendation. This boundary applies both when a decision is first made and when an accepted decision may need to change.

When an implementation carries substantial integration risk or final integration benefits from independent review, humans also decide whether to accept that change. The [governance specification](MCM_AI_Governance.md) defines the exact boundary, while routine technical work continues autonomously.

### Start new conversations proactively

**Treat a new conversation as a normal part of long-running modeling work.** A phase completion, accepted decision, or saved formal result is a natural point to switch. Switch promptly when an old conversation has accumulated obsolete analysis, repeated exploration, or rejected approaches.

Before switching, ask AI to update effective decisions, preserve results, and compress current progress, unresolved items, and the next action into `state.md`. A new conversation first reads `AGENTS.md`, then locates the original problem, accepted decisions, current state, and relevant artifacts, loading method guides only as needed. `state.md` holds the execution frontier; model semantics and numerical claims remain grounded in their respective authorities.

A continuation prompt can be short:

> Continue projects/my-modeling-project. First recover the current state from the repository according to AGENTS.md, check accepted decisions and existing results, and then carry out the next action in state.md.

### Use branches for changes and GitHub for collaboration

Routine work proceeds on the stable integration branch. Candidate changes with substantial integration risk or a need for independent review use a temporary branch, where comparison and impact-scoped validation are completed against an exact version before integration. A branch isolates implementation; a change in model meaning still follows the consequential-decision process first.

For team projects, GitHub can serve as the shared remote. Members begin from a common version, divide work by subproblem or artifact, develop in parallel branches, and integrate through commit diffs and pull-request review. Before taking over work, compare local changes with upstream state. At merge time, inspect model assumptions, result versions, and paper references in addition to resolving file conflicts. Generate and review Word/PDF deliverables after the content and results are integrated.

### Keep each record in its proper role

| Information | Current authority |
|---|---|
| Problem facts, data conditions, and requirements | Original problem and attachments |
| Accepted model meaning and important assumptions | Project `decisions.md` |
| Current execution frontier, unresolved items, and next action | Project `state.md`, maintained when a long task needs it |
| Implementation and formal numerical claims | Source code and accepted result files |
| Paper content and layout | `paper.md`, approved Word layout, and formatting profile |
| Version evolution, differences, and rollback | Git |

Keep the decision file compact and update the state file as the frontier changes. At delivery, check consistency across code, results, figures, prose, and final formats. Remove temporary artifacts after their consumers are finished; Git retains ordinary history.

## Papers and project evidence

The following projects show the papers and supporting artifacts produced by the workflow. Papers are available as PDF, Word, and Markdown. Each project entry connects to its task summary, decisions, state, code, scripts, and tests.

| Project | Paper | Decisions and results |
|---|---|---|
| [2026 B: Radio Interference Source Localization and Removal](projects/2026-cumcm/solutions/problem-b-radio-interference/README.md) | [PDF](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.md) | [Decision record](projects/2026-cumcm/solutions/problem-b-radio-interference/decisions.md) · [Geometry and offline-mission evidence](projects/2026-cumcm/solutions/problem-b-radio-interference/results/) |
| [2026 C: Microgrid Purchasing and Storage Scheduling](projects/2026-cumcm/solutions/problem-c-microgrid/README.md) | [PDF](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.md) | [Decision record](projects/2026-cumcm/solutions/problem-c-microgrid/decisions.md) · [Paper result summary](projects/2026-cumcm/solutions/problem-c-microgrid/results/paper-summary.json) |

Problem B publishes geometry, local-refinement, and offline-mission results with reproduction scripts; interface runs additionally require the competition simulator. Problem C publishes its core scheduling implementation, paper-result summary, and synthetic-input contract tests. Its verification script checks that the summary remains synchronized with the paper; reproducing the full-year costs additionally requires the original competition attachments. These boundaries state what the public evidence can directly support.

For a concrete example of how a decision propagates into a paper claim, read [From Decision to Paper Claim: Information Boundaries under Volatile Electricity Prices](docs/decision-to-claim-case-study.md).

## Documentation

| Entry | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Repository rules and routing read by an agent on entry |
| [Getting Started](docs/getting-started.md) | Project structure, execution sequence, and example setup |
| [AI Governance](MCM_AI_Governance.md) | Authority boundaries, decision gate, autonomous execution, state recovery, and integration rules |
| [Modeling and Paper Playbook](shared/templates/personal-modeling-playbook.md) | Model selection, experiment design, evidence strength, paper reasoning, and expression |
| [Paper Formatting Profile](shared/templates/personal-paper-profile.yaml) | Reusable formatting parameters |
| [Shared Utilities and Tests](shared/) | Common checks for paper formatting, figure style, and document links |
| [2026 Project Index](projects/2026-cumcm/README.md) | Papers and project materials for Problems B and C |

## Method sources

| Source | Referenced scope |
|---|---|
| [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) | Contest-task routing, agent entry points, and cross-phase continuity |
| [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill) | Modeling execution, tool organization, and paper delivery concepts |

Inspired by these methods, this repository further organizes Git-centered authority boundaries, consequential decision control, state recovery, result evidence, and multi-format paper synchronization. The links document methodological provenance; the governance documents in this repository define its actual project rules.

## License

Code is available under the [MIT License](LICENSE-CODE.md). Documentation, papers, figures, result data, and templates are available under [CC BY 4.0](LICENSE-CONTENT.md). Copying, modification, and redistribution are welcome under the applicable license; see the [license overview](LICENSE.md) for the complete scope.
