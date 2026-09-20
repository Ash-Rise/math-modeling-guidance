"""Run from repo root: python -m shared.examples.figure_regression.

Real-data style/layout examples. Outputs are temporary, never publication authority.
No generator entry points or their global style settings are imported.
"""
import csv
import json
from pathlib import Path
import shutil
import tempfile
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from shared.figure_style import PALETTES, category_styles, contrast_text, figure_size, paper_style, save_figure

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    print(f"source: {path.relative_to(ROOT)}")
    return path


def save(fig, out, name, original):
    # Catch clipped labels at the canvas edge, not a claim of no internal overlap.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    for text in fig.findobj(Text):
        if text.get_visible() and text.get_text() and text.get_in_layout():
            box = text.get_window_extent(renderer)
            if box.width and box.height and not text.get_clip_on():
                assert box.x0 >= -1 and box.y0 >= -1, text.get_text()
                assert box.x1 <= bounds.width + 1 and box.y1 <= bounds.height + 1, text.get_text()
    save_figure(fig, out / f"{name}-after.png")
    plt.close(fig)
    shutil.copyfile(original, out / f"{name}-before.png")
    for suffix in ("before", "after"):
        with Image.open(out / f"{name}-{suffix}.png") as im:
            ImageOps.grayscale(im).save(out / f"{name}-{suffix}-gray.png")


def sensitivity(out):
    project = ROOT / "projects/2025-cumcm/solutions/problem-b-epitaxial-thickness"
    r = json.loads(source(project / "results/frozen/results.json").read_text(encoding="utf-8"))
    labels = {"10deg": "仅10°", "15deg": "仅15°", "zero_offset": "仅乘性校准",
              "free_index": "自由介电尺度（对照）", "s_polarized": "纯s偏振",
              "p_polarized": "纯p偏振", "zero_epi_drude": "外延层Drude项置零",
              "6H_reference": "6H参考色散", "transparent_band": "透光频段（SiC）",
              "middle_band": "600—3500 cm⁻¹（Si）"}
    fig, axes = plt.subplots(1, 2, figsize=figure_size("tall"), sharey=True,
                             layout="constrained")
    count = 0
    for ax, material in zip(axes, ("SiC", "Si")):
        rows = {s["scenario"]: s for s in r["sensitivity"] if s["material"] == material}
        base = r["fits"][material + "_multi"]["d_um"]
        ax.axvline(base, color=PALETTES["highlight"]["reference"], ls="--", label="主结果")
        for y, key in enumerate(labels):
            if key not in rows:
                ax.text(.5, y, "不适用", transform=ax.get_yaxis_transform(),
                        va="center", ha="center", color=".4")
                continue
            value = rows[key]["d_um"]
            line, = ax.plot(value, y, marker="D" if key == "free_index" else "o",
                            color=PALETTES["categorical"][1 if key == "free_index" else 0])
            np.testing.assert_array_equal(line.get_xdata(), [value])
            count += 1
        ax.set(title=material, xlabel="条件性厚度 / μm")
        ax.set_yticks(range(len(labels)), labels.values())
        ax.grid(axis="x")
        ax.legend(loc="lower right")
    axes[0].set_ylim(len(labels)-.5, -.5)
    fig.suptitle("条件对照；横轴范围不同，点不是置信区间", fontsize=9)
    save(fig, out, "sensitivity", project / "figures/fig5_sensitivity.png")
    print(f"sensitivity: {count} source thicknesses unchanged; common rows; missing != zero")


def heatmap(out):
    project = ROOT / "projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch"
    results = project / "results/task-2"
    # Same recorded tuning batch and aggregation as the existing figure generator.
    frame = pd.read_csv(source(results / "tuning_coarse_W030.csv"))
    b = frame[frame.strategy == "B"].groupby("candidate")["mean_response_min"].mean().reset_index()
    parsed = b.candidate.str.extract(r"B_beta(?P<beta>[0-9.]+)_delta(?P<delta>[0-9.]+)").astype(float)
    table = pd.concat([b, parsed], axis=1).pivot(index="beta", columns="delta", values="mean_response_min").sort_index().sort_index(axis=1)
    values = table.to_numpy()
    selected = json.loads(source(results / "selected_policy.json").read_text(encoding="utf-8"))["best_b"]
    fig, ax = plt.subplots(figsize=figure_size("wide"), layout="constrained")
    im = ax.imshow(values, cmap=PALETTES["sequential"], aspect="auto",
                   interpolation="nearest", vmin=np.nanmin(values), vmax=np.nanmax(values))
    np.testing.assert_array_equal(im.get_array(), values)
    for (y, x), val in np.ndenumerate(values):
        ax.text(x, y, f"{val:.2f}", ha="center", va="center",
                color=contrast_text(im.cmap(im.norm(val))))
    y = table.index.get_loc(float(selected["beta"]))
    x = table.columns.get_loc(float(selected["delta"]))
    # Double outline survives both dark/light cells and grayscale.
    for color, lw in [("black", 3), ("white", 1.5)]:
        ax.add_patch(plt.Rectangle((x-.47, y-.47), .94, .94, fill=False, ec=color, lw=lw))
    ax.set_xticks(range(len(table.columns)), [f"{v:g}" for v in table.columns])
    ax.set_yticks(range(len(table.index)), [f"{v:g}" for v in table.index])
    ax.set(xlabel="允许绕行阈值 δ / min", ylabel="负荷权重 β / min",
           title="调参集响应；双框标记已选参数（不代表独立验证）")
    fig.colorbar(im, ax=ax).set_label("平均响应时间 / min")
    save(fig, out, "heatmap", project / "figures/process_q2_b_grid.png")
    print(f"heatmap: {values.size} aggregated cells unchanged; selected beta={selected['beta']}, delta={selected['delta']}")


def timeline(out):
    project = ROOT / "projects/2026-summer-assignment/solutions/problem-b-cold-chain-routing"
    data = json.loads(source(project / "data/problem_b_data.json").read_text(encoding="utf-8"))
    with source(project / "results/route_schedule.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["scenario"] == "normal" and r["node_type"] == "store"]
    styles = category_styles(["A", "B", "C"])
    fig, ax = plt.subplots(figsize=figure_size("wide"), layout="constrained")
    labels = []
    for y, row in enumerate(rows):
        node = data["nodes"][row["node"]]
        arrival = float(row["arrival_minute"])
        interval = ax.hlines(y, node["window_start"], node["window_end"], color=".75", lw=6)
        # A single event needs a visible time mark; choose it here, not in the palette.
        line, = ax.plot(arrival, y, **styles[row["vehicle"]],
                        marker="|", markersize=9, linestyle="None")
        np.testing.assert_array_equal(line.get_xdata(), [arrival])
        np.testing.assert_array_equal(interval.get_segments()[0][:, 0], [node["window_start"], node["window_end"]])
        clock = row["arrival_clock"]
        ax.annotate(clock, (arrival, y), xytext=(6, 5), textcoords="offset points", fontsize=8)
        labels.append(f"车辆 {row['vehicle']} · {node['name']}")
    ticks = list(range(270, 361, 15))
    ax.set_xticks(ticks, [f"{t//60:02}:{t%60:02}" for t in ticks])
    ax.set_yticks(range(len(rows)), labels)
    ax.set(xlim=(267, 363), ylim=(len(rows)-.5, -.65), xlabel="时刻",
           title="正常场景：时间窗（灰段）与方案到达时刻（符号）")
    ax.grid(axis="x")
    save(fig, out, "timeline", project / "figures/fig3_time_windows.png")
    print(f"timeline: {len(rows)} arrivals and window endpoint pairs unchanged")


def main():
    out = Path(tempfile.mkdtemp(prefix="mcm-figure-regression-"))
    warnings.filterwarnings("error", message="Glyph .* missing from font")
    with paper_style():
        sensitivity(out)
        heatmap(out)
        timeline(out)
    print(f"Temporary visual review: {out}")


if __name__ == "__main__":
    main()
