"""Create the two evidence figures consumed by paper/paper.md."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(REPOSITORY))

from search_strategy import q3_search_points, q4_search_points
from shared.figure_style import PALETTES, figure_size, paper_style, save_figure

OUTPUT = ROOT / "paper/figures"


def coverage_figure() -> None:
    green, magenta, gray = PALETTES["categorical"][2], PALETTES["categorical"][5], "#777777"
    with paper_style():
        fig, axes = plt.subplots(1, 2, figsize=figure_size("wide", height=3.15))
        for ax in axes:
            ax.add_patch(Circle((0, 0), 1800, fill=False, color="#222222", linewidth=1.2))
            ax.set_aspect("equal")
            ax.set_xlabel("$x$ / m")
            ax.set_ylabel("$y$ / m")
            ax.set_xlim(-3100, 3100)
            ax.set_ylim(-3100, 3100)
            ax.grid(True, alpha=0.55)
        q3 = np.asarray(q3_search_points())
        for p in q3:
            axes[0].add_patch(Circle(p, 900, facecolor=green, edgecolor="none", alpha=0.10))
        axes[0].scatter(q3[:, 0], q3[:, 1], s=25, color=green, zorder=3)
        axes[0].set_title("(a) Q3：7点的900 m覆盖")

        q4 = np.asarray(q4_search_points())
        axes[1].scatter(q4[:, 0], q4[:, 1], s=10, color=gray, alpha=0.75)
        source = np.array([1800.0, 0.0])
        axes[1].add_patch(Wedge(source, 1000, -90, 90, facecolor=magenta,
                                edgecolor=magenta, alpha=0.15, linewidth=1.0))
        axes[1].scatter(*source, s=30, color=magenta, zorder=4)
        axes[1].annotate("边界定向源", source, xytext=(-48, 12), textcoords="offset points",
                         arrowprops={"arrowstyle": "-", "color": magenta}, color=magenta)
        axes[1].set_title("(b) Q4：69点命中任意定向半圆盘")
        fig.tight_layout(w_pad=1.2)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        save_figure(fig, OUTPUT / "coverage_constructions.png", bbox_inches="tight")
        plt.close(fig)


def cost_figure() -> None:
    evidence = json.loads((ROOT / "results/q34_offline_evidence.json").read_text(encoding="utf-8"))
    colors = {"q3": PALETTES["categorical"][2], "q4": PALETTES["categorical"][5]}
    with paper_style():
        fig, axes = plt.subplots(1, 2, figsize=figure_size("wide", height=2.75))
        for ax, mode in zip(axes, ("q3", "q4")):
            rows = [row for row in evidence["cases"] if row["mode"] == mode]
            for count in (10, 13, 16):
                values = np.array([row["virtual_time_s"] for row in rows if row["source_count"] == count])
                offsets = np.linspace(-0.12, 0.12, len(values))
                ax.scatter(count + offsets, values, s=24, color=colors[mode], alpha=0.75)
                median = float(np.median(values))
                ax.plot([count - 0.22, count + 0.22], [median, median], color="#222222", linewidth=1.4)
            ax.set_xticks((10, 13, 16))
            ax.set_xlabel("干扰源数量")
            ax.set_ylabel("虚拟总时间 / s")
            ax.set_title(f"({'a' if mode == 'q3' else 'b'}) {mode.upper()}")
            ax.grid(axis="y", alpha=0.6)
            ax.set_ylim(bottom=0)
        fig.tight_layout(w_pad=1.5)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        save_figure(fig, OUTPUT / "offline_virtual_time.png", bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    coverage_figure()
    cost_figure()
    print(OUTPUT)


if __name__ == "__main__":
    main()
