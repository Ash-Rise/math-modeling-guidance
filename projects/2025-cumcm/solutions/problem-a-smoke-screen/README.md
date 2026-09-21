# A 题：烟幕干扰

[返回项目集合](../../README.md)

## 成品论文

[PDF](paper/paper.pdf) · [Word](paper/paper.docx) · [Markdown 源稿](paper/paper.md)

论文集中展示完整圆柱视线遮蔽模型、问题 1—5 的方案与结果、联合遮蔽机制，以及有限搜索和离散验证对应的证据边界。

## 支撑材料

- [核心几何模型](src/) · [正文图表](figures/) · [公开冻结结果](results/frozen/)
- [从决策到论文主张的案例](../../../../docs/decision-to-claim-case-study.md)

## 最小复算

建议使用 Python 3.11—3.13，并从仓库根目录运行：

```powershell
python -m pip install -r requirements.txt
python projects/2025-cumcm/solutions/problem-a-smoke-screen/scripts/reproduce.py
```

默认复算问题 1，通常在一分钟内完成；输出 `status: matched` 及约 `1.391642669 s` 的有效遮蔽时间，即与公开冻结结果一致。`--scope q2` 可复算问题 2，耗时更长。

公开代码提供前两问的运行入口；问题 3—5 以成品论文和图表展示，不作为公开快照中的完整重跑接口。
