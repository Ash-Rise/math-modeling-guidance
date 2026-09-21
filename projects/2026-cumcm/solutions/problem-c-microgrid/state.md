# 当前状态

- 阶段：公开成品示例。
- 正式论文：`paper/paper.md`、`paper/paper.docx`、`paper/paper.pdf`。
- 当前实现：`src/` 保存确定性优化、误差修正、滚动调单和波动电价调度。
- 正式摘要：`results/paper-summary.json` 汇集论文采用的四问核心费用与比较值。
- 核验入口：`python scripts/verify_public_evidence.py`。
- 回归检查：`python -m pytest tests -q`。

当前公开版本以论文展示为主，结果摘要与合成合同测试连接论文主张和核心实现。
