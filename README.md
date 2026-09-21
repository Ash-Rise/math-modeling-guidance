# Mathematical Modeling Guidance

**简体中文** | [English](README_EN.md)

> 面向 AI 辅助数学建模的 Git 项目工作区。

[![CI](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml/badge.svg)](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/Python-3.11%E2%80%933.13-3572A5)](requirements.txt)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-2E8B57)](LICENSE-CODE.md)
[![Content: CC BY 4.0](https://img.shields.io/badge/Content-CC_BY_4.0-2E8B57)](LICENSE-CONTENT.md)

配合数学建模 Skill 使用的 Git 项目工作区，让 AI 持续推进建模、计算与论文交付，让人类集中处理关键决策。

[仓库定位](#仓库定位) · [主要优势](#主要优势) · [开始使用](#开始使用) · [持续推进与协作](#持续推进与协作) · [论文与项目证据](#论文与项目证据) · [文档导航](#文档导航)

## 仓库定位

本仓库提供一套可复用的项目组织方式：用治理规则划分人机职责，用文件保存项目事实与当前状态，用 Git 管理变更，再将模型、代码、结果和论文连接起来。它适合需要跨多轮对话、持续计算或多人协作的数学建模任务。

**本仓库是辅助 Skill 使用的工作流工具，不是安装到智能体中的 Skill，也不是一句话生成论文的提示词包。** 两者配合时，Skill 提供建模、编程、检索和文档处理等执行方法；本仓库为这些工作提供明确的项目边界、持久记录和交付结构。

推荐采用“竞赛路由 + 建模执行”的组合：[handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) 负责 CUMCM、MCM/ICM 与电工杯的竞赛路由、规则边界和阶段衔接，[XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill) 提供建模分析、编程计算和论文交付能力。也可以使用其他能够读取仓库文件、运行命令并遵循 `AGENTS.md` 的数学建模 Skill。

| 组成 | 负责什么 |
|---|---|
| 智能体与外部 Skill | 理解任务，选择并调用方法和工具，执行分析、编码、计算与写作 |
| 本仓库 | 组织任务输入、关键决策、当前状态、实现、证据和论文，规定它们的职责与衔接方式 |
| Git；可选配合 GitHub | 保存版本、比较改动、隔离分支、恢复历史，并支持远端同步和团队协作 |
| 人类 | 决定影响问题含义、重要约束、研究范围或结论解释的关键事项 |

仓库提供规则、方法文档、格式配置、共享工具和实际项目供复用。使用时由能够读写项目文件、执行命令的智能体落实这些约定；Skill、模型服务及项目依赖按自己的环境配置。

## 主要优势

- **跨会话继续工作。** 关键决定和执行前沿写入项目文件，新对话可以从当前状态接续，减少旧推理和已淘汰方案对后续判断的干扰。
- **关键模型含义保持稳定。** 原题负责题目事实，决策记录负责已接受的模型含义；实现和测试围绕这些依据推进，降低跨阶段语义漂移。
- **AI 持续执行，人类聚焦关键决策。** 普通实现、数值技术选择、实验、验证和论文同步由 AI 自主完成，真正影响题意或结论的选择在充分分析后交由人类决定。
- **变更可比较、可隔离、可恢复。** Git 提交保存完整改动，分支承载候选方案，团队可以审阅差异、整合成果或恢复到明确版本。
- **论文结论有据可查。** 决策、计算入口、结果文件和图表连接到论文主张；修改上游模型或结果时，同步检查受影响的正文与交付文件。
- **验证投入与实际风险匹配。** 围绕具体失败方式和受影响部分选择检查，把计算与审查用于能够改变判断的问题。

## 开始使用

### 1. 获取工作区

准备 Git 和能够访问本地文件、运行命令的 AI 编程环境，并配置上述推荐 Skill 或功能相当的数学建模 Skill。阅读文档和论文可以直接在网页完成；本地使用可克隆仓库：

```shell
git clone https://github.com/Ash-Rise/math-modeling-guidance.git
cd math-modeling-guidance
```

如果已有自己的项目仓库，也可将 [AGENTS.md](AGENTS.md)、[治理规范](MCM_AI_Governance.md) 和所需的 [共享方法与工具](shared/) 引入项目，保留对应路径和许可证信息。

### 2. 放入自己的任务

在 `projects/` 下建立独立项目目录，放入原始题面和附件，说明本次目标、资源限制与交付格式。公开示例中的 `problem-statement.md` 是任务概要；新项目应保留原题，并按需整理供机器阅读的 Markdown，题目事实始终以原始材料为准。

典型项目结构如下，文件按实际工作需要建立：

```text
projects/my-modeling-project/
├── problem-statement.md   # 题面阅读稿；原题和附件另行保留
├── decisions.md           # 已接受的关键模型决定
├── state.md               # 长任务的当前前沿与下一步
├── requirements.txt       # 项目运行依赖
├── src/                   # 模型实现
├── scripts/               # 求解、复算与绘图入口
├── results/               # 正式结果与支撑证据
├── tests/                 # 关键模型合同与回归检查
└── paper/
    ├── figures/           # 正文图表
    ├── paper.md           # 论文内容
    ├── paper.docx         # Word 交付
    └── paper.pdf          # PDF 交付
```

将新项目纳入版本管理时，检查 [.gitignore](.gitignore)：当前规则为公开示例保留了特定例外，需要按新项目的路径调整决策、状态、正式结果和交付文件的收录范围。

### 3. 让智能体进入项目

在仓库根目录打开智能体，可用下面的指令开始，将项目路径和交付要求替换为自己的内容：

> 请读取根目录 AGENTS.md，定位 projects/my-modeling-project。根据原题、已有 decisions.md 和 state.md 恢复项目，按需读取治理规范与建模手册，结合已配置的数学建模 Skill 推进任务。普通技术工作自主处理；关键语义选择先核对依据并完成分析，再提出决策建议。本次目标是……，交付格式为……。

项目随后沿这条主线推进：整理题意与数据 → 明确模型与关键决策 → 实现、计算与验证 → 整理正式结果 → 写作与图表 → 交付检查。新证据可能触发局部回修，相关改动沿依赖关系同步到下游。

Python 示例建议使用 3.11—3.13，并在项目虚拟环境中安装对应 `requirements.txt`。运行命令见各项目 README；Word/PDF 生成所需的文档工具由所用 Skill 和交付方式确定。更完整的说明见 [工作流入门](docs/getting-started.md)。

## 持续推进与协作

### 人类只处理关键决策

AI 负责题意整理、方案调查、模型实现、实验计算、绘图、验证、状态维护和论文同步。影响数值质量、复现性或效率的重要技术选择可以自主执行，并在阶段报告中说明。

人类负责题意解释、模型含义、重要假设、目标、硬约束、评价口径、允许资源、实质范围和结论解释等关键选择。AI 提问前先核对原题与已接受决策，排除不成立的方案；只有仍有实质分歧、且当前推进确实需要决定时，才提交有依据的建议。重要决定首次建立和后续变更均适用这一边界。

当实现涉及较高集成风险，或最终整合需要独立审阅时，人类还负责是否接受该变更的关键判断。具体触发条件见 [治理规范](MCM_AI_Governance.md)，普通技术工作持续自主推进。

### 积极开启新对话

**将新开对话作为长周期建模的常规做法。** 在一个阶段完成、关键决定确定或正式结果保存后，适合切换新会话；旧对话积累了较多过时分析、反复试探或已淘汰方案时，应及时切换。

切换前让 AI 更新有效决策、保存结果，并将当前进展、未解决事项和下一步压缩进 `state.md`。新会话先读 `AGENTS.md`，再定位原题、有效决策、当前状态和相关产物，按需加载方法手册。`state.md` 保存执行前沿，具体模型含义与数值仍回到各自的权威来源核对。

接续指令可以很短：

> 继续 projects/my-modeling-project。先按 AGENTS.md 从仓库恢复当前状态，核对有效决策和现有结果，再推进 state.md 中的下一步。

### 用分支管理变更，用 GitHub 协作

普通工作在稳定分支持续推进。较高集成风险的实现或需要独立审阅的候选变更放在临时分支，在明确版本上完成比较与验证，再按仓库规则审阅、合并。分支隔离实现；改变模型含义仍需先解决对应的关键决策。

多人协作时可使用 GitHub 作为共享远端。成员从共同版本出发，按子任务或产物划分工作，通过分支并行推进，再通过提交差异和 Pull Request 审阅、整合。每次接手先核对本地修改与远端状态；合并时除文件冲突外，还要检查模型假设、结果版本和论文引用是否一致。Word/PDF 适合在正文与结果整合后统一生成并审阅。

### 保持记录各司其职

| 信息 | 当前依据 |
|---|---|
| 题目事实、数据条件与要求 | 原始题面和附件 |
| 已接受的模型含义与重要假设 | 项目 `decisions.md` |
| 当前执行前沿、未解决事项与下一步 | 项目 `state.md`，长任务按需维护 |
| 实现与正式数值 | 源代码；已接受的结果文件 |
| 论文内容与版式 | `paper.md`；经确认的 Word 版式；格式配置 |
| 版本演进、差异与回退 | Git |

决策文件保持精简，状态文件随当前进展更新。交付时检查代码、结果、图表、正文和最终格式是否一致，移除已无用途的临时产物，历史由 Git 保留。

## 论文与项目证据

以下两个项目展示工作流形成的论文与支撑材料。论文提供 PDF、Word 和 Markdown，各项目入口连接任务概要、决策、状态、代码、脚本与测试。

| 项目 | 论文 | 关键决策与结果 |
|---|---|---|
| [2026 B：无线电干扰源定位与清除](projects/2026-cumcm/solutions/problem-b-radio-interference/README.md) | [PDF](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.md) | [决策记录](projects/2026-cumcm/solutions/problem-b-radio-interference/decisions.md) · [几何与离线任务证据](projects/2026-cumcm/solutions/problem-b-radio-interference/results/) |
| [2026 C：微网购电及储能调度](projects/2026-cumcm/solutions/problem-c-microgrid/README.md) | [PDF](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.md) | [决策记录](projects/2026-cumcm/solutions/problem-c-microgrid/decisions.md) · [论文结果摘要](projects/2026-cumcm/solutions/problem-c-microgrid/results/paper-summary.json) |

B 题公开几何、局部推进与离线任务的结果和复算脚本；接口运行需要另行启动竞赛模拟器。C 题公开核心调度代码、论文数值摘要和合成输入合同测试，核验脚本检查摘要与正文一致性；全年费用复算还需要原始竞赛附件。这些入口分别呈现实际可检查的证据范围。

想了解决策如何影响论文，可阅读 [从决策到论文主张：波动电价下的信息边界](docs/decision-to-claim-case-study.md)。

## 文档导航

| 入口 | 用途 |
|---|---|
| [AGENTS.md](AGENTS.md) | 智能体进入仓库时读取的工作规则与路由 |
| [工作流入门](docs/getting-started.md) | 项目结构、执行顺序和示例运行准备 |
| [AI 治理规范](MCM_AI_Governance.md) | 权威分层、决策门槛、自主执行、状态恢复和集成规则 |
| [建模与论文方法手册](shared/templates/personal-modeling-playbook.md) | 模型选择、实验设计、证据强度、论文推理与表达 |
| [论文格式配置](shared/templates/personal-paper-profile.yaml) | 可复用的排版参数 |
| [共享工具与测试](shared/) | 论文格式、图表样式和文档链接等公共检查 |
| [2026 项目入口](projects/2026-cumcm/README.md) | B/C 题论文与项目材料 |

## 方法来源

| 来源 | 参考范围 |
|---|---|
| [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) | 竞赛任务路由、Agent 工作入口与跨阶段衔接 |
| [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill) | 建模执行流程、工具组织与论文交付思路 |

在上述方法启发下，本仓库进一步组织了以 Git 项目为中心的权威分层、关键决策边界、状态恢复、结果证据链和多格式论文同步。来源链接说明方法参考关系，具体项目规则以本仓库治理文档为准。

## 版权与使用

代码采用 [MIT License](LICENSE-CODE.md)，文档、论文、图表、结果数据与模板采用 [CC BY 4.0](LICENSE-CONTENT.md)。欢迎按相应许可证复制、修改和再分发，完整适用范围见 [许可证说明](LICENSE.md)。
