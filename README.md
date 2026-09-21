# Mathematical Modeling Guidance

本仓库汇集一套面向 AI 辅助数学建模的公开方法与项目示例，覆盖题意权威、模型决策、真实计算、证据链、论文同步和交付验证，便于阅读方法、理解工作流并查看完整项目产物。

## 从这里开始

1. 先看下方两篇成品论文，了解最终呈现效果。
2. 阅读 [15 分钟入门](docs/getting-started.md)，按竞赛轻量版建立最小项目。
3. 阅读 [从决策到论文主张的案例](docs/decision-to-claim-case-study.md)，观察方法如何支撑论文中的一个关键主张。

首次使用只需维护原题、必要的 `decisions.md`、一个复算入口、正式结果和论文。长项目或多代理协作再启用 `state.md`、更完整的冻结层级与集成边界。

## 成品论文

| 示例 | 成稿 | 展示重点 |
|---|---|---|
| A：烟幕干扰 | [PDF](projects/2025-cumcm/solutions/problem-a-smoke-screen/paper/paper.pdf) · [Word](projects/2025-cumcm/solutions/problem-a-smoke-screen/paper/paper.docx) · [Markdown](projects/2025-cumcm/solutions/problem-a-smoke-screen/paper/paper.md) | 几何判据、优化结果、联合遮蔽机制与证据边界 |
| B：外延层厚度 | [PDF](projects/2025-cumcm/solutions/problem-b-epitaxial-thickness/paper/paper.pdf) · [Word](projects/2025-cumcm/solutions/problem-b-epitaxial-thickness/paper/paper.docx) · [Markdown](projects/2025-cumcm/solutions/problem-b-epitaxial-thickness/paper/paper.md) | 光学反演、多光束模型、敏感性与条件性结论 |

## 方法入口

- [Agent 入口](AGENTS.md)：仓库内工作的权威来源、边界与验证原则。
- [AI 治理](MCM_AI_Governance.md)：人类决策与 AI 自主范围。
- [个人建模手册](shared/templates/personal-modeling-playbook.md)：建模、实验、写作与交付方法。
- [论文样式配置](shared/templates/personal-paper-profile.yaml)：中文数学建模论文的可复用格式参数。
- [共享工具与测试](shared/)：通用实现和最小回归测试。
- [轻量与完整工作流](docs/getting-started.md)：最小目录、执行顺序与升级条件。

## 公开项目示例

| 项目集合 | 内容 |
| --- | --- |
| [2025 CUMCM](projects/2025-cumcm/README.md) | A/B 题论文、Word/PDF 成稿、核心代码、图表与结果 |

示例以论文 Markdown、Word/PDF 成稿为主入口，核心代码、图表和冻结结果用于解释论文结论的来源。项目 README 同时说明公开复算范围。

## 方法来源

竞赛路由方法参考 [handsomeZR-netizen/mathmodel-skill](https://github.com/handsomeZR-netizen/mathmodel-skill)，建模执行方法参考 [XiaoMaColtAI/math-modeling-skill](https://github.com/XiaoMaColtAI/math-modeling-skill)。本仓库发布自有治理文档、模板和项目示例，并以来源链接标注参考的上游 Skills。

## 版权与使用

仓库内容当前采用保留权利的 [版权说明](LICENSE.md)，可公开阅读与评价；复制、修改和再分发需要著作权人另行许可。外部链接内容适用其来源条款。
