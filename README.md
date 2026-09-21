# Mathematical Modeling Guidance

> Public guidance and complete paper examples for AI-assisted mathematical modeling.

[![CI](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml/badge.svg)](https://github.com/Ash-Rise/math-modeling-guidance/actions/workflows/quality.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/Python-3.11%E2%80%933.13-3572A5)](requirements.txt)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-2E8B57)](LICENSE.md)

本仓库汇集一套面向 AI 辅助数学建模的公开方法与项目示例，覆盖题意权威、模型决策、真实计算、证据链、论文同步和交付验证，便于阅读方法、理解工作流并查看完整项目产物。

## 成品论文

| 示例 | 论文 | 展示重点 |
|---|---|---|
| 2026 B：无线电干扰源定位 | [PDF](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-b-radio-interference/paper/paper.md) | 集合定位、覆盖构造与离线任务验证 |
| 2026 C：微网调度 | [PDF](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.pdf) · [Word](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.docx) · [Markdown](projects/2026-cumcm/solutions/problem-c-microgrid/paper/paper.md) | 预测误差、滚动优化、储能控制与波动电价 |

## 从这里开始

1. 先看上方成品论文，了解最终呈现效果。
2. 阅读 [工作流入门](docs/getting-started.md)，建立完整项目结构。
3. 阅读 [从决策到论文主张的案例](docs/decision-to-claim-case-study.md)，观察方法如何支撑论文中的一个关键主张。

## 工作流

```mermaid
flowchart LR
    A[题意权威] --> B[模型决策]
    B --> C[真实计算]
    C --> D[正式结果]
    D --> E[论文同步]
    E --> F[交付验证]
```

公开项目采用同一套完整工作流，以原题、Accepted Decisions、当前状态、实现、正式结果和论文分别承载对应信息。

## 方法入口

- [Agent 入口](AGENTS.md)：仓库内工作的权威来源、边界与验证原则。
- [AI 治理](MCM_AI_Governance.md)：人类决策与 AI 自主范围。
- [个人建模手册](shared/templates/personal-modeling-playbook.md)：建模、实验、写作与交付方法。
- [论文样式配置](shared/templates/personal-paper-profile.yaml)：中文数学建模论文的可复用格式参数。
- [共享工具与测试](shared/)：通用实现和最小回归测试。
- [工作流入门](docs/getting-started.md)：项目结构、执行顺序与主要产物。

## 仓库结构

```text
.
├── docs/                  # 工作流入门与案例
├── projects/
│   └── 2026-cumcm/       # 2026 B/C 题示例
├── shared/
│   ├── templates/        # 建模手册与论文样式
│   └── tests/            # 共享工具回归测试
├── AGENTS.md             # Agent 工作入口
└── MCM_AI_Governance.md  # AI 建模治理
```

## 项目集合

| 项目集合 | 内容 |
| --- | --- |
| [2026 CUMCM](projects/2026-cumcm/README.md) | B/C 题论文、PDF/Word/Markdown、核心代码与图表 |

示例以 PDF、Word 和 Markdown 论文为主入口，核心代码、图表和冻结结果用于解释论文结论的来源。项目 README 同时说明公开复算范围。

## 方法来源

竞赛路由方法参考 [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill)，建模执行方法参考 [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill)。本仓库发布自有治理文档、模板和项目示例，并以来源链接标注参考的上游 Skills。

## 版权与使用

仓库原创内容采用 [CC BY 4.0](LICENSE.md)，支持署名使用、复制、修改和再分发。外部链接内容适用其来源条款。

## 引用

引用信息见 [`CITATION.cff`](CITATION.cff)，GitHub 仓库页面也可直接生成引用格式。
