# 15 分钟入门

这套工作流有两个使用档位。第一次使用从竞赛轻量版开始，只有实际协作复杂度出现后再升级。

## 竞赛轻量版

适合三人团队和 72 小时竞赛，最小目录如下：

```text
project/
├─ problem-statement.*     # 原题与附件，题目事实权威
├─ decisions.md            # 只记录已接受的重大语义决定；没有则不创建
├─ src/                    # 模型与实现
├─ reproduce.py            # 一条命令重算或核验主要结果
├─ results/                # 论文实际引用的正式结果
└─ paper/paper.md          # 当前论文内容
```

推荐顺序：

1. 从原题提取任务、数据、单位、硬约束和交付要求。
2. 对会改变目标、约束或结论含义的歧义，先查原题和附件；仍有多个实质解释时再提交 Decision Proposal。
3. 将接受的解释写入简短 `decisions.md`，随后实现模型。
4. 用最小可信实验验证当前最关键的不确定性，把论文使用的数值写入 `results/`。
5. 论文按“主张—推理—证据—边界”同步；`reproduce.py` 核验论文引用的核心结果。

`README.md` 只需写清环境、第一条命令、预计产物和一致性判据。

## 长项目或多代理版

出现以下情况时，再启用完整治理：

- 工作跨多个会话，需要 `state.md` 保存当前执行前沿；
- 多个实现分支可能改变正式结果，需要 accepted/frozen 分层；
- 高风险集成需要独立分支和人工 PR 审阅；
- 多个代理并行工作，需要更明确的 authority 与恢复边界。

[AGENTS.md](../AGENTS.md) 和 [AI 治理](../MCM_AI_Governance.md) 描述完整版本。它们提供升级规则，不要求每个短项目创建全部文件。

## 运行公开示例

建议使用 Python 3.11—3.13：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python projects/2025-cumcm/solutions/problem-a-smoke-screen/scripts/reproduce.py
```

最后一条命令复算 A 题问题 1，并将关键数值与公开冻结结果比较。项目级 README 给出耗时、产物和更完整的复现范围。
