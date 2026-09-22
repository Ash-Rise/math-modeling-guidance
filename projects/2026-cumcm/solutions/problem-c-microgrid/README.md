# C：微网购电及储能调度

[返回项目集合](../../README.md)

## 成品论文

[PDF](paper/paper.pdf) · [Word](paper/paper.docx) · [Markdown](paper/paper.md)

论文展示确定性购电与储能配置、预测误差下的风险修正、日内预报滚动更新，以及波动电价下的预测与调度。

## 支撑材料

- [任务概要](problem-statement.md) · [关键决策](decisions.md)
- [核心实现](src/) · [结果摘要](results/paper-summary.json) · [核验脚本](scripts/verify_public_evidence.py) · [测试](tests/) · [论文图表](paper/figures/)

论文源稿、图表和核心实现采用同一项目版本，共同呈现费用、预测模型和策略比较。

## 快速检查

```powershell
python -m pip install -r requirements.txt
python scripts/verify_public_evidence.py
python -m pytest tests -q
```
