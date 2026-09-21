# B：无线电干扰源定位与清除

[返回项目集合](../../README.md)

## 成品论文

[PDF](paper/paper.pdf) · [Word](paper/paper.docx) · [Markdown](paper/paper.md)

论文展示示向误差集合建模、解析定位边界、第二观测点选择、定向源覆盖搜索和完整任务策略。

## 支撑材料

- [任务概要](problem-statement.md) · [关键决策](decisions.md) · [当前状态](state.md)
- [核心实现](src/) · [运行脚本](scripts/) · [结果证据](results/) · [测试](tests/) · [论文图表](paper/figures/)

论文覆盖 Q1—Q4 的几何判据、局部推进和端到端任务案例。核心实现的运行环境与依赖见 [requirements.txt](requirements.txt)。

## 快速检查

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q
python scripts/run_q12_experiments.py --output results/q12_evidence.json
python scripts/run_local_refinement.py --output results/local_refinement_evidence.json
python scripts/run_offline_missions.py --output results/q34_offline_evidence.json
```

三份 JSON 分别支撑问题一/二几何、局部推进与问题三/四离线任务结果；[`run_robot.py`](scripts/run_robot.py) 连接已启动的竞赛模拟器测试。
