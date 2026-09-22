"""Self-contained teaching example. Uses synthetic, equally weighted scenarios."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def optimize(demands, capacity, waste_cost, shortage_cost):
    """Enumerate every feasible integer quantity; retain all minimizers."""
    if not demands or any(not isinstance(d, int) or d < 0 for d in demands):
        raise ValueError("Demand scenarios must be nonempty nonnegative integers.")
    if capacity < 0 or waste_cost <= 0 or shortage_cost <= 0:
        raise ValueError("Capacity must be nonnegative and costs must be positive.")
    rows = []
    for quantity in range(capacity + 1):
        waste = sum(max(quantity - d, 0) for d in demands)
        shortage = sum(max(d - quantity, 0) for d in demands)
        total = waste_cost * waste + shortage_cost * shortage
        rows.append((quantity, total, waste, shortage))
    best_loss = min(row[1] for row in rows)
    optimal = [row[0] for row in rows if row[1] == best_loss]
    return rows, optimal


def read_demands():
    with (PROJECT / "input/demand.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["day", "demand"]:
            raise ValueError("Expected CSV columns: day,demand")
        return [int(row["demand"]) for row in reader]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortage-cost", type=int, default=9)
    parser.add_argument("--waste-cost", type=int, default=3)
    parser.add_argument("--capacity", type=int, default=140)
    parser.add_argument("--label", default="baseline", help="Output folder name")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.label):
        parser.error("Use a simple output label containing letters, digits, _ or -.")
    parameters = (args.capacity, args.waste_cost, args.shortage_cost)
    if args.label == "baseline" and parameters != (140, 3, 9):
        parser.error("Changed parameters need a separate --label to preserve baseline.")
    try:
        demands = read_demands()
        rows, optimal = optimize(demands, *parameters)
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))

    quantity = optimal[0]
    _, total, waste, shortage = rows[quantity]
    count = len(demands)
    summary = {
        "scope": "Synthetic equal-weight scenarios; not out-of-sample validation",
        "input": "input/demand.csv",
        "demands": demands,
        "scenario_count": count,
        "capacity": args.capacity,
        "waste_cost_yuan": args.waste_cost,
        "shortage_cost_yuan": args.shortage_cost,
        "recommended_quantity": quantity,
        "optimal_quantities": optimal,
        "total_loss_yuan": total,
        "mean_loss_yuan": total / count,
        "mean_waste": waste / count,
        "mean_shortage": shortage / count,
    }
    output = PROJECT / "results" / args.label
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["quantity", "total_loss_yuan", "total_waste", "total_shortage"])
        writer.writerows(rows)

    comparisons = sorted({0, quantity, args.capacity, min(args.capacity, 100)})
    table = "\n".join(
        f"| {q} | {rows[q][1] / count:.2f} | {rows[q][2] / count:.2f} | {rows[q][3] / count:.2f} |"
        for q in comparisons
    )
    report = f"""# 食堂备餐情景分析：{args.label}

本例使用 {count} 个等权合成需求情景。剩餐损失为每份 {args.waste_cost} 元，缺餐损失为每份 {args.shortage_cost} 元，容量为 {args.capacity} 份。

推荐备餐 **{quantity} 份**，情景平均损失 **{total / count:.2f} 元**。全部最优备餐量：{', '.join(map(str, optimal))} 份；并列时推荐较小者。

## 模型和求解

决策是开餐前确定的整数备餐量 q。每个需求情景 d 的损失为 {args.waste_cost} × max(q-d, 0) + {args.shortage_cost} × max(d-q, 0)。将各情景损失相加再除以 {count}，在 0 到 {args.capacity} 的全部 {args.capacity + 1} 个整数候选中取最小值。有限可行域已完整枚举，因此这里的最优性仅针对这组情景和给定损失定义成立。

| 备餐量（份） | 平均损失（元） | 平均剩餐（份） | 平均缺餐（份） |
|---|---|---|---|
{table}

推荐方案的平均剩餐为 {waste / count:.2f} 份，平均缺餐为 {shortage / count:.2f} 份。多备一份会在需求已经满足的情景增加剩餐损失，并在仍然缺餐的情景减少缺餐损失；因此最优量由两种代价与需求分布共同决定，而不是直接取平均需求。完整候选表见 [candidates.csv](candidates.csv)，输入与参数快照见 [summary.json](summary.json)。

## 证据边界

数据来自合成教学场景，等权假设由教学题面明确给定。这里没有独立测试集，情景平均损失不能当成真实食堂未来表现，也不是样本外验证。实际应用还需要真实需求、成本与容量依据，并用独立时段评价。
"""
    (output / "report.md").write_text(report, encoding="utf-8")
    print(f"Recommended quantity: {quantity}; mean scenario loss: {total / count:.2f} yuan")
    print(f"Report: {output / 'report.md'}")


if __name__ == "__main__":
    main()
