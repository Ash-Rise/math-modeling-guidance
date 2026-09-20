"""Run from repo root: python -m shared.examples.figure_regression.

Real-data style/layout examples. Outputs are temporary, never publication authority.
No generator entry points or their global style settings are imported.
"""
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
from PIL import Image, ImageOps

from shared.figure_style import PALETTES, figure_size, paper_style, save_figure

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


def main():
    out = Path(tempfile.mkdtemp(prefix="mcm-figure-regression-"))
    warnings.filterwarnings("error", message="Glyph .* missing from font")
    with paper_style():
        sensitivity(out)
    print(f"Temporary visual review: {out}")


if __name__ == "__main__":
    main()
