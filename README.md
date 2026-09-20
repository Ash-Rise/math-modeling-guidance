# Mathematical Modeling Guidance

面向 AI 辅助数学建模的公开方法与项目示例。仓库关注题意权威、模型决策、真实计算、证据链、论文同步和交付验证，而不是提供一次性生成论文的提示词。

这是从私有工作仓库导出的脱敏快照，只包含当前公开接口，不继承原仓库的提交、分支、PR、Actions 或协作历史。

## 方法入口

- [Agent 入口](AGENTS.md)：仓库内工作的权威来源、边界与验证原则。
- [AI 治理](MCM_AI_Governance.md)：人类决策与 AI 自主范围。
- [个人建模手册](shared/templates/personal-modeling-playbook.md)：建模、实验、写作与交付方法。
- [论文样式配置](shared/templates/personal-paper-profile.yaml)：中文数学建模论文的可复用格式参数。
- [共享工具与测试](shared/)：通用实现和最小回归测试。

## 公开项目示例

| 项目集合 | 内容 |
| --- | --- |
| [2025 CUMCM](projects/2025-cumcm/README.md) | A/B 题论文、核心代码、图表与适合公开的结果 |
| [2026 Summer Assignment](projects/2026-summer-assignment/README.md) | A/B/C 题论文、实现与实验产物 |

示例保留论文 Markdown、核心代码、图表及适合公开的结果。原始题面、官方附件和部分输入数据不随仓库再分发；缺少公开输入的项目用于展示方法和产物组织，不声称克隆后能够完整重算。

## Skill 来源边界

本仓库不分发本地安装的 Skills。竞赛路由参考 [handsomeZR/mathmodel-skill](https://github.com/handsomeZR/mathmodel-skill)，建模执行方法参考 [XiaoMa-Lab/MathModelAgent](https://github.com/XiaoMa-Lab/MathModelAgent)。使用上游内容时应分别遵守其当前许可证；本仓库也不包含本地工具目录中的专有组件。

## 公开范围

本快照排除了 2026 CUMCM 项目、Git 与 PR 历史、内部决策及复核材料、个人路径与运行日志、不可再分发的题面附件、未公开数据，以及带有文档元数据的 DOCX/PDF/XLSX 等二进制交付物。详见 [公开范围说明](PUBLICATION_SCOPE.md)。

除文件另有声明外，本仓库当前未授予额外的复制、修改或再分发许可。
