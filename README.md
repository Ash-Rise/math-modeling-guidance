# Mathematical Modeling Guidance

**简体中文** | [English](README_EN.md)

> 把题目、计算、结果和论文放在一个工作区里，换对话也能接着做。

你提供题目、目标和截止时间，AI 负责组织文件、计算、验证和整理报告；需要你判断的重要假设会用自然语言说明。Git 在背后保存版本，你不必先学会分支和提交命令。

**第一次使用：[跟着入门指南开始](docs/getting-started.md)。想先体验：[运行自包含的食堂备餐示例](projects/quickstart-canteen/README.md)。**

## 需要准备什么

- 一个能打开整个项目文件夹、读写文件并执行终端命令的 AI 编程环境。只有聊天窗口、只能读 GitHub 链接的环境不能完成本地计算。
- Git，用于本地保存历史；示例还需要 Python 3.11—3.13。让 AI 先检查，缺什么再安装。
- 真实建模任务使用已配置的数学建模 Skill 或功能相当的执行能力；小示例仅使用 Python 标准库，不需要另装 Skill 或项目依赖。

本仓库提供工作区和规则，不自带模型服务，也不是自动运行的平台。GitHub 账号只在远端同步、协作时需要；本地提交不会自动上传。

## 第一次开始

1. 在本页绿色 **Code → Download ZIP** 下载并解压，或让 AI 克隆本仓库。
2. 在 AI 编程环境中打开解压后的文件夹，确认能看到根目录的 `AGENTS.md`。
3. 将下面的话发给 AI：

> 请读取根目录 AGENTS.md，带我运行 projects/quickstart-canteen 的教学示例。先检查 Git 和 Python 环境；若这是下载解压的独立文件夹，检查它不属于其他仓库后初始化本地 Git。按示例 README 运行，告诉我结果在哪里、结论是什么，并在完成后保存本次工作到本地检查点。不要推送到远端。

首次 Git 提交如果缺少作者姓名和邮箱，AI 应询问你要使用的身份，只配置当前仓库。若暂不配置，可以先运行示例，但尚未建立提交检查点。

准备好自己的题目后，照 [入门指南](docs/getting-started.md) 放入附件并替换任务目标；不需要复制完整目录或阅读治理手册。

## 日常直接这样说

| 你想做什么 | 可以发给 AI 的话 |
|---|---|
| 开始自己的题目 | 题目在 projects/my-project/input，请先理解每问要求，再完成一个可检查的基础方案。目标是……，截止时间是……。 |
| 查看进度 | 现在完成了什么？结果在哪里？有什么需要我决定？ |
| 今天暂停 | 保存当前文件和接续状态，创建本地检查点，告诉我下次从哪里继续。 |
| 换对话继续 | 请读取 AGENTS.md，从 projects/my-project 的文件恢复进度，继续下一步。 |
| 比较新方案 | 保留当前可用方案，比较这个候选方案是否值得采用，先别替换正式结果。 |
| 找回旧方案 | 帮我找到上次可用版本，先说明恢复哪些文件会影响当前工作。 |
| 整理论文 | 根据已核验的结果更新论文，说明证据不足的部分。 |

这些是给 AI 的自然语言指令，不是仓库自带的按钮。文件保存、Git 提交、远端同步是三件事；AI 应明确报告实际完成了哪一步。

## 文件会随着任务逐步出现

开始只需题目、附件和目标。有重要模型选择时才维护 `decisions.md`；需要跨会话接续时才维护 `state.md`；计算和写作开始后再建立代码、结果和论文目录。无需预先填满模板。

你主要查看结果和报告，AI 维护实现与记录。原题决定题意，已接受的决定约束模型，代码产生结果，论文解释证据；Git 保存它们的演进。规范和测试能够减少错误，不能替代对模型是否符合题目的判断。

## 一个人使用与团队协作

单人使用可先在本地完成工作，需要备份时再连接自己的远端仓库。不要把“本地有提交”当成异地备份。

不熟悉 Git 的团队可以先由一人维护主工作区，其他成员交付各自负责的分析或正文，由负责人整合。需要多人直接改文件时，再使用分支和 Pull Request（变更审阅请求），并约定各问负责人及整合人。具体操作见 [进阶工作流](docs/workflow-details.md)。

## 示例与成果

[食堂备餐教学示例](projects/quickstart-canteen/README.md) 自带合成数据，一条命令即可生成结果和 Markdown 报告；还可以改变成本参数、对比方案并练习换会话接续。它用于学习操作，不代表真实食堂预测效果。

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
| [工作流入门](docs/getting-started.md) | 首次使用、运行示例、开始自己的题目与接续 |
| [进阶工作流](docs/workflow-details.md) | 文件职责、Git 同步、团队协作与完整流程 |
| [AI 治理规范](MCM_AI_Governance.md) | 权威分层、决策门槛、自主执行、状态恢复和集成规则 |
| [建模与论文方法手册](shared/templates/personal-modeling-playbook.md) | 模型选择、实验设计、证据强度、论文推理与表达 |
| [论文格式配置](shared/templates/personal-paper-profile.yaml) | 可复用的排版参数 |
| [共享工具与测试](shared/) | 论文格式、图表样式和文档链接等公共检查 |
| [2026 项目入口](projects/2026-cumcm/README.md) | B/C 题论文与项目材料 |

## 检查与运行环境

小示例直接使用 Python 标准库运行，无需安装根目录依赖。开发者修改共享工具时，可按 [进阶工作流](docs/workflow-details.md) 准备项目环境并运行 `python -m pytest shared/tests -q`。B/C 项目各自的复算范围和依赖见其 README；测试通过不代表缺失原始附件的全年结果已经复算。

## 方法来源

| 来源 | 参考范围 |
|---|---|
| [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill) | 竞赛任务路由、Agent 工作入口与跨阶段衔接 |
| [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill) | 建模执行流程、工具组织与论文交付思路 |

在上述方法启发下，本仓库进一步组织了以 Git 项目为中心的权威分层、关键决策边界、状态恢复、结果证据链和多格式论文同步。来源链接说明方法参考关系，具体项目规则以本仓库治理文档为准。

## 版权与使用

代码采用 [MIT License](LICENSE-CODE.md)，文档、论文、图表、结果数据与模板采用 [CC BY 4.0](LICENSE-CONTENT.md)。欢迎按相应许可证复制、修改和再分发，完整适用范围见 [许可证说明](LICENSE.md)。
