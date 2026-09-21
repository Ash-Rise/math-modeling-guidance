# B 题：外延层厚度

[返回项目集合](../../README.md)

## 成品论文

[PDF](paper/paper.pdf) · [Word](paper/paper.docx) · [Markdown 源稿](paper/paper.md)

论文展示双光束与多光束厚度反演、SiC/Si 的机制差异、模型比较、敏感性分析和条件性结论。

## 支撑材料

- [光学模型与求解脚本](scripts/) · [正文图表](figures/) · [公开冻结结果](results/frozen/)
- [依赖](requirements.txt)

完整复算需要竞赛提供的四份双角度光谱工作簿，因此公开快照以论文、冻结结果和核心实现供阅读审查。持有原始附件时，可从项目目录运行：

```powershell
python -m pip install -r requirements.txt
python scripts/solve.py --output results/reproduced
python scripts/validate.py --folder results/reproduced
```

冻结结果中的主厚度、敏感性范围和验证摘要与当前论文同步。
