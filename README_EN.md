# Mathematical Modeling Guidance

[简体中文](README.md) | **English**

> Keep the problem, computation, results, and paper together so a new conversation can continue the work.

Provide the problem, objective, and deadline. Your agent organizes files, computes and checks results, and explains important modeling choices in plain language. Git preserves local history; you do not need to learn branching before trying the workspace.

**Start here: [beginner guide (Chinese)](docs/getting-started.md). Try the [self-contained canteen example](projects/quickstart-canteen/README.md).**

## Requirements

Use an AI coding environment that can open the project folder, read and write files, and execute terminal commands. A chat-only interface or read-only GitHub connection cannot run the local workflow. Git is needed for local version history; the example needs Python 3.11–3.13 and only its standard library. Let the agent check the environment first.

Real modeling projects use configured modeling Skills or equivalent capabilities. This repository supplies project organization, not a model service or an autonomous application. A GitHub account is only needed for remote synchronization and collaboration; local commits do not upload files.

## First run

1. Download **Code → Download ZIP** and extract it, or clone this repository.
2. Open the folder containing `AGENTS.md` in your AI coding environment.
3. Send this prompt:

> Read AGENTS.md and run the teaching example in projects/quickstart-canteen. Check Git and Python first. For a standalone ZIP download, verify that it is not inside another repository before initializing local Git. Follow the example README, explain the result and output paths, and save the completed work as a local checkpoint. Do not push to a remote.

If Git has no commit identity, the agent should ask which name and email to configure locally. You can run the example without configuring an identity, but no commit checkpoint exists until a commit succeeds.

For your own task, create `projects/my-project/input/`, add the original problem and attachments, and tell the agent the objective, deadline, and required output. Files for decisions, recovery, computation, and writing are added only when needed.

## Everyday requests

| Goal | Tell the agent |
|---|---|
| Start a task | Read AGENTS.md and the inputs in projects/my-project/input. Build a checkable baseline for this objective and deadline. |
| Check progress | What is complete, where are the results, and what needs my decision? |
| Pause | Save files and recovery state, then create a local checkpoint. |
| Resume | Read AGENTS.md and recover projects/my-project from its files. Continue the next action. |
| Compare a model | Preserve the usable baseline and evaluate this candidate before replacing accepted results. |
| Restore work | Locate the last usable version and explain which files restoring it would affect. |
| Update the paper | Update the paper from verified results and identify unsupported claims. |

These are natural-language requests, not built-in application controls. Saving files, committing locally, and synchronizing remotely are separate actions. The agent should report which actually succeeded.

## Collaboration and further setup

Start locally. For a team unfamiliar with Git, one member can maintain the main workspace and integrate contributions. Teams editing the repository concurrently should agree on ownership and use branches and pull requests where appropriate. See the [advanced workflow (Chinese)](docs/workflow-details.md) for file responsibilities, synchronization, and integration.

The [canteen example](projects/quickstart-canteen/README.md) includes synthetic data and generates results and a Markdown report with one command. It demonstrates execution, a parameter comparison, and session recovery; it is not evidence of real-world predictive performance.

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
| [Getting Started](docs/getting-started.md) | First run, daily requests, and session recovery (Chinese) |
| [Advanced Workflow](docs/workflow-details.md) | File responsibilities, Git, and team integration (Chinese) |
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
