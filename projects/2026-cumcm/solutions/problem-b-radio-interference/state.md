# 当前状态

- 阶段：公开成品示例。
- 正式论文：`paper/paper.md`、`paper/paper.docx`、`paper/paper.pdf`。
- 当前实现：`src/` 保存几何、第二观测点、搜索策略、任务控制、离线模拟器和接口客户端。
- 结果证据：`results/` 保存问题一/二、局部推进及问题三/四的三份 JSON。
- 复算入口：`scripts/run_q12_experiments.py`、`scripts/run_local_refinement.py`、`scripts/run_offline_missions.py`。
- 接口入口：`scripts/run_robot.py`。
- 回归检查：`python -m pytest tests -q`。

当前论文、结果 JSON、图表、实现和测试构成同一公开版本。
