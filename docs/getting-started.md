# 工作流入门

本仓库的项目采用完整工作流，让题意、决策、实现、结果和论文分别拥有稳定入口。

## 项目结构

```text
project/
├─ problem-statement.*     # 原题与附件
├─ decisions.md            # 已接受的重大语义决定
├─ state.md                # 当前执行前沿与下一步
├─ src/                    # 模型与实现
├─ scripts/                # 求解、复算、绘图和交付入口
├─ results/                # 论文引用的正式结果
├─ figures/                # 正文图表
├─ tests/                  # 模型合同与回归检查
└─ paper/
   ├─ paper.md             # 论文内容
   ├─ paper.docx           # Word 成稿
   └─ paper.pdf            # PDF 成稿
```

`state.md` 服务持续推进与跨会话恢复，项目进入稳定交付后可压缩为简短的当前状态。`decisions.md` 聚焦已经接受且会影响模型含义的决定。

## 执行顺序

1. 从原题提取任务、数据、单位、硬约束和交付要求。
2. 使用 authority 消歧；实质选择通过 Decision Proposal 形成 Accepted Decision。
3. 建立模型与实现，用最小可信实验解决当前最关键的不确定性。
4. 将论文采用的数值、图表和核验结果固定到正式结果入口。
5. 论文按“主张—推理—证据—边界”组织，并同步 Markdown、Word 与 PDF。
6. 在阶段边界更新 `state.md`，交付时核对结果、图表和论文的一致性。

## 阅读公开示例

建议使用 Python 3.11—3.13：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python projects/2025-cumcm/solutions/problem-a-smoke-screen/scripts/reproduce.py
```

最后一条命令复算 A 题问题 1，并将关键数值与公开冻结结果比较。各项目 README 提供论文、图表、核心实现和相应复现入口。

[AGENTS.md](../AGENTS.md) 汇总仓库入口与 authority，[AI 治理](../MCM_AI_Governance.md) 说明决策、自主执行、状态恢复和集成规则，[个人建模手册](../shared/templates/personal-modeling-playbook.md) 提供建模、实验、写作与交付方法。
