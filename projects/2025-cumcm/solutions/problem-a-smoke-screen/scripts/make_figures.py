from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse, Patch, Rectangle
from scipy.spatial import ConvexHull


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN = (PROJECT_ROOT / "results" / "frozen").resolve()
AUDITS = (PROJECT_ROOT / "results" / "audits").resolve()
OUTPUT = PROJECT_ROOT / "figures"
sys.path.insert(0, str(PROJECT_ROOT.parents[3]))
from shared.figure_style import PALETTES, contrast_text

MISSILES = {
    "M1": np.array([20000.0, 0.0, 2000.0]),
    "M2": np.array([19000.0, 600.0, 2100.0]),
    "M3": np.array([18000.0, -600.0, 1900.0]),
}
DRONES = {
    "FY1": np.array([17800.0, 0.0, 1800.0]),
    "FY2": np.array([12000.0, 1400.0, 1400.0]),
    "FY3": np.array([6000.0, -3000.0, 700.0]),
    "FY4": np.array([11000.0, 2000.0, 1800.0]),
    "FY5": np.array([13000.0, -2000.0, 1300.0]),
}

# Original Paul Tol Bright values; names express roles, not cycle positions.
BRIGHT = PALETTES["categorical"]
COLORS = dict(zip(("blue", "red", "green", "yellow", "sky", "purple", "light"), BRIGHT))
COLORS["gray"] = "#555555"  # neutral structure and reference intervals
DRONE_COLORS = {
    "FY1": COLORS["blue"],
    "FY2": COLORS["yellow"],
    "FY3": COLORS["green"],
    "FY4": COLORS["red"],
    "FY5": COLORS["purple"],
}


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans SC", "Microsoft YaHei", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "lines.linewidth": 1.5,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def load_frozen(name: str) -> dict:
    path = (FROZEN / name).resolve()
    if path.parent != FROZEN:
        raise RuntimeError("Figure input escaped results/frozen")
    data = json.loads(path.read_text(encoding="utf-8"))
    if name in {"q3.json", "q4.json", "q5.json"} and not data.get("formal_semantics", "").startswith("DP-04"):
        raise RuntimeError("Joint figures require DP-04 frozen results")
    return data


def load_audit(name: str) -> dict:
    path = (AUDITS / name).resolve()
    if path.parent != AUDITS:
        raise RuntimeError("Figure input escaped results/audits")
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig: plt.Figure, stem: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(OUTPUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def cylinder_surface(n_theta: int = 180, n_z: int = 9) -> np.ndarray:
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    side = np.array(
        [[7.0 * np.cos(a), 200.0 + 7.0 * np.sin(a), z]
         for z in np.linspace(0.0, 10.0, n_z) for a in theta]
    )
    caps = np.array(
        [[r * np.cos(a), 200.0 + r * np.sin(a), z]
         for z in (0.0, 10.0) for r in np.linspace(0.0, 7.0, 5) for a in theta]
    )
    return np.vstack((side, caps))


def line_segment_distances(observer: np.ndarray, cloud: np.ndarray, points: np.ndarray) -> np.ndarray:
    segment = points - observer
    cloud_vector = cloud - observer
    fractions = np.sum(segment * cloud_vector, axis=1) / np.sum(segment**2, axis=1)
    fractions = np.clip(fractions, 0.0, 1.0)
    nearest = observer + fractions[:, None] * segment
    return np.linalg.norm(nearest - cloud, axis=1)


def figure_geometry() -> None:
    q1 = load_frozen("q1.json")
    left, right = q1["shielding_intervals_s"][0]
    time = 0.5 * (left + right)
    missile_initial = np.array([20000.0, 0.0, 2000.0])
    missile = missile_initial * (1.0 - 300.0 * time / np.linalg.norm(missile_initial))
    cloud = np.asarray(q1["explosion_point_m"], dtype=float)
    cloud[2] -= 3.0 * (time - q1["explosion_time_s"])
    target_center = np.array([0.0, 200.0, 5.0])

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.05), constrained_layout=True)
    ax = axes[0]
    target_outline = np.array([[0.0, 193.0, 5.0], [0.0, 207.0, 5.0]])
    for target in target_outline:
        ax.plot([missile[0] / 1000.0, target[0]], [missile[1], target[1]],
                color=COLORS["gray"], linewidth=0.8, alpha=0.75)
    ax.plot([missile[0] / 1000.0, target_center[0]], [missile[1], target_center[1]],
            color=COLORS["blue"], linestyle="--", linewidth=1.1, label="中心视线")
    ax.scatter(missile[0] / 1000.0, missile[1], s=36, marker=">", color=COLORS["red"], zorder=4)
    ax.add_patch(Ellipse((cloud[0] / 1000.0, cloud[1]), 0.020, 20.0,
                         facecolor=COLORS["sky"], edgecolor=COLORS["blue"], alpha=0.55))
    ax.scatter(target_center[0], target_center[1], s=42, marker="s", color=COLORS["green"], zorder=4)
    ax.annotate("M1", (missile[0] / 1000.0, missile[1]), xytext=(-6, 8), textcoords="offset points")
    ax.annotate("烟幕云团", (cloud[0] / 1000.0, cloud[1]), xytext=(-58, 14), textcoords="offset points")
    ax.annotate("真目标", (0.0, 200.0), xytext=(7, -4), textcoords="offset points")
    ax.set_xlabel("$x$ / km")
    ax.set_ylabel("$y$ / m")
    ax.set_title(f"(a) Q1 有效区间中点的平面位置（$t={time:.3f}$ s）", loc="left")
    ax.grid(True, color="#E8E8E8", linewidth=0.6)
    ax.margins(x=0.04, y=0.12)

    observer = missile
    axis = target_center - observer
    axis /= np.linalg.norm(axis)
    transverse_1 = np.cross(np.array([0.0, 0.0, 1.0]), axis)
    transverse_1 /= np.linalg.norm(transverse_1)
    transverse_2 = np.cross(axis, transverse_1)
    points = cylinder_surface()
    segment = points - observer
    cloud_vector = cloud - observer
    fractions = np.sum(segment * cloud_vector, axis=1) / np.sum(segment**2, axis=1)
    fractions = np.clip(fractions, 0.0, 1.0)
    nearest = observer + fractions[:, None] * segment
    offsets = nearest - cloud
    projection = np.column_stack((offsets @ transverse_1, offsets @ transverse_2))
    distances = np.linalg.norm(offsets, axis=1)

    ax = axes[1]
    hull = ConvexHull(projection)
    hull_points = projection[hull.vertices]
    ax.fill(hull_points[:, 0], hull_points[:, 1], color=COLORS["yellow"], alpha=0.45,
            label="完整圆柱视线束的最近点投影")
    ax.scatter(projection[::40, 0], projection[::40, 1], s=6, color=COLORS["yellow"], alpha=0.8)
    ax.add_patch(Circle((0.0, 0.0), 10.0, facecolor=COLORS["sky"], edgecolor=COLORS["blue"],
                        linewidth=1.4, alpha=0.25, label="有效烟幕截面（半径 10 m）"))
    ax.scatter(0.0, 0.0, s=20, color=COLORS["blue"], zorder=4)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-11.0, 11.0)
    ax.set_ylim(-11.0, 11.0)
    ax.set_xlabel("横向投影 / m")
    ax.set_ylabel("竖向投影 / m")
    ax.set_title("(b) 云团附近的完整目标视线束截面", loc="left")
    ax.text(0.03, 0.93, f"最大三维线段距离：{distances.max():.2f} m",
            transform=ax.transAxes, color=COLORS["gray"], va="top",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 1.5})
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False, ncol=1)
    ax.grid(True, color="#ECECEC", linewidth=0.6)
    save(fig, "fig1_shielding_geometry")


def figure_joint_mechanism() -> None:
    """Visualize the accepted DP-04 mechanism using the paper's historical counterexample."""
    audit = load_audit("q5_joint.json")
    records = {(record["drone"], record["bomb"]): record for record in audit["records"]}
    # This fixed pair is the counterexample already documented in paper section 4.4.
    record_a = records[("FY4", 2)]
    record_b = records[("FY5", 1)]
    time = 19.05
    observer = MISSILES["M1"] * (1.0 - 300.0 * time / np.linalg.norm(MISSILES["M1"]))
    points = cylinder_surface_points_for_mechanism()

    def cloud_and_distances(record: dict) -> tuple[np.ndarray, np.ndarray]:
        cloud = np.asarray(record["explosion_point_m"], dtype=float).copy()
        cloud[2] -= 3.0 * (time - record["explosion_time_s"])
        return cloud, line_segment_distances(observer, cloud, points)

    cloud_a, distance_a = cloud_and_distances(record_a)
    cloud_b, distance_b = cloud_and_distances(record_b)
    joint_distance = np.minimum(distance_a, distance_b)
    expected = (10.304731406, 10.237151298, 9.336983613)
    actual = (distance_a.max(), distance_b.max(), joint_distance.max())
    if not np.allclose(actual, expected, atol=5e-9, rtol=0.0):
        raise RuntimeError(f"Historical joint-mechanism values drifted: {actual}")
    if np.any(joint_distance > 10.0):
        raise RuntimeError("Historical DP-04 counterexample no longer covers every sampled ray")

    covered_a = distance_a <= 10.0
    covered_b = distance_b <= 10.0
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.75), sharex=True, sharey=True,
                             constrained_layout=True)
    projection = points[:, 1:3]
    common = dict(s=1.5, linewidths=0, rasterized=True)

    for ax, covered, title, value in (
        (axes[0], covered_a, "(a) 云团 A（FY4-2）单独作用", actual[0]),
        (axes[1], covered_b, "(b) 云团 B（FY5-1）单独作用", actual[1]),
    ):
        ax.scatter(projection[covered, 0], projection[covered, 1], color="#B9C1C7", alpha=0.23,
                   **common)
        ax.scatter(projection[~covered, 0], projection[~covered, 1], color=COLORS["red"],
                   alpha=0.72, **common)
        ax.text(0.04, 0.05, f"所需半径 {value:.3f} m > 10 m\n红色：未覆盖视线",
                transform=ax.transAxes, va="bottom", fontsize=7.4,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.5})
        ax.set_title(title, loc="left")

    ax = axes[2]
    both = covered_a & covered_b
    a_only = covered_a & ~covered_b
    b_only = covered_b & ~covered_a
    ax.scatter(projection[both, 0], projection[both, 1], color="#B9C1C7", alpha=0.20, **common)
    ax.scatter(projection[a_only, 0], projection[a_only, 1], color=COLORS["blue"], alpha=0.72,
               **common)
    ax.scatter(projection[b_only, 0], projection[b_only, 1], color=COLORS["yellow"], alpha=0.72,
               **common)
    ax.text(0.04, 0.05, f"联合所需半径 {actual[2]:.3f} m < 10 m\n未覆盖视线：0",
            transform=ax.transAxes, va="bottom", fontsize=7.4,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.5})
    ax.set_title("(c) A、B 联合作用", loc="left")

    for ax in axes:
        ax.add_patch(Rectangle((193.0, 0.0), 14.0, 10.0, fill=False, edgecolor="#222222",
                               linewidth=0.8))
        ax.set_xlim(192.5, 207.5)
        ax.set_ylim(-0.4, 10.4)
        ax.set_xlabel("目标表面 $y$ 坐标 / m")
        ax.grid(True, color="#ECECEC", linewidth=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("目标表面高度 $z$ / m")
    fig.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="none", markersize=4, color=COLORS["red"],
                   label="单团未覆盖"),
            Line2D([], [], marker="o", linestyle="none", markersize=4, color=COLORS["blue"],
                   label="仅 A 覆盖"),
            Line2D([], [], marker="o", linestyle="none", markersize=4, color=COLORS["yellow"],
                   label="仅 B 覆盖"),
            Line2D([], [], marker="o", linestyle="none", markersize=4, color="#9AA2A8",
                   label="两团均覆盖"),
        ],
        loc="outside lower center", ncol=4, frameon=False,
    )
    save(fig, "fig_joint_shielding_mechanism")


def cylinder_surface_points_for_mechanism() -> np.ndarray:
    """The 159,840-point surface grid used by the recorded t=19.05 s check."""
    theta = np.linspace(0.0, 2.0 * np.pi, 1440, endpoint=False)
    side = np.array(
        [[7.0 * np.cos(a), 200.0 + 7.0 * np.sin(a), z]
         for z in np.linspace(0.0, 10.0, 61) for a in theta],
        dtype=float,
    )
    caps = np.array(
        [[r * np.cos(a), 200.0 + r * np.sin(a), z]
         for z in (0.0, 10.0) for r in np.linspace(0.0, 7.0, 25) for a in theta],
        dtype=float,
    )
    points = np.vstack((side, caps))
    if len(points) != 159_840:
        raise RuntimeError("Joint-mechanism surface grid size drifted")
    return points


def figure_q2_response_refinement() -> None:
    q2 = load_frozen("q2.json")
    audit = load_audit("q2_optimality.json")
    speed_slice = audit["local_speed_boundary"]
    speeds = [item["speed_m_s"] for item in speed_slice]
    durations = [item["duration_s"] for item in speed_slice]
    if not np.all(np.diff(durations) > 0.0):
        raise RuntimeError("Recorded Q2 local speed slice is no longer increasing")
    if not math.isclose(durations[-1], q2["effective_shielding_duration_s"], abs_tol=1e-9):
        raise RuntimeError("Q2 speed slice endpoint does not match frozen Q2")

    seed = 1000
    coarse_pool = audit["multistart"] + audit["speed_cap_sweep"]
    coarse = next(item for item in coarse_pool if item["seed"] == seed)
    fine = next(item for item in audit["refinement_screen"]["candidates"] if item["seed"] == seed)
    endpoint = audit["strongest_independent_challenger"]
    if endpoint["seed"] != seed or not np.allclose(coarse["strategy"], endpoint["strategy"]):
        raise RuntimeError("Q2 coarse/fine/endpoint records do not describe the same candidate")
    stages = ["粗筛\n0.1 s / 168点", "较细筛选\n0.01 s / 3,780点", "端点精算"]
    stage_values = [coarse["sampled_duration_s"], fine["sampled_duration_s"], endpoint["duration_s"]]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), constrained_layout=True)
    ax = axes[0]
    ax.plot(speeds, durations, color=COLORS["blue"], marker="o", markersize=4)
    ax.scatter([speeds[-1]], [durations[-1]], marker="D", s=28, color=COLORS["red"], zorder=4)
    ax.annotate(f"冻结方案\n{durations[-1]:.6f} s", (speeds[-1], durations[-1]),
                xytext=(-8, -29), textcoords="offset points", ha="right",
                arrowprops={"arrowstyle": "-", "color": COLORS["gray"], "linewidth": 0.7})
    ax.set_xlabel("速度 $v$ / (m·s$^{-1}$)")
    ax.set_ylabel("完整遮蔽时长 / s")
    ax.set_title("(a) 固定其余变量的速度切片", loc="left")
    ax.grid(True, color="#E8E8E8", linewidth=0.6)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)

    ax = axes[1]
    x = np.arange(3)
    ax.plot(x, stage_values, color=COLORS["green"], marker="o", markersize=5,
            label="同一 seed 1000 候选")
    ax.axhline(q2["effective_shielding_duration_s"], color=COLORS["blue"], linestyle="--",
               linewidth=1.1, label=f"冻结方案 {q2['effective_shielding_duration_s']:.6f} s")
    for xi, value in zip(x, stage_values, strict=True):
        ax.text(xi, value + 0.0010, f"{value:.6f}" if xi == 2 else f"{value:.2f}",
                ha="center", va="bottom", fontsize=7.4)
    ax.set_xticks(x, stages)
    ax.set_ylabel("计算时长 / s")
    ax.set_ylim(4.577, 4.604)
    ax.set_title("(b) 同一候选的离散与精算对照", loc="left")
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.6)
    ax.legend(loc="lower left", frameon=False, fontsize=7.2)
    save(fig, "fig_q2_response_refinement")


def figure_q3_shared_trajectory() -> None:
    q3 = load_frozen("q3.json")
    records = q3["records"]
    if q3["joint_only_intervals_s"]["M1"]:
        raise RuntimeError("Q3 mechanism figure requires the frozen zero joint-only contribution")
    colors = (COLORS["blue"], COLORS["yellow"], COLORS["green"])
    heading = math.radians(q3["heading_deg"])
    velocity = np.array([q3["speed_m_s"] * math.cos(heading),
                         q3["speed_m_s"] * math.sin(heading), 0.0])
    initial = DRONES["FY1"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), constrained_layout=True,
                             gridspec_kw={"width_ratios": (1.15, 1.0)})
    ax = axes[0]
    end_time = max(record["release_time_s"] for record in records) + 0.6
    line_times = np.linspace(0.0, end_time, 100)
    trajectory = initial[None, :] + line_times[:, None] * velocity[None, :]
    ax.plot(trajectory[:, 0], trajectory[:, 2], color="#444444", linewidth=1.2,
            label="FY1 共享航迹")
    ax.annotate("飞行方向", xy=(trajectory[-1, 0], trajectory[-1, 2]),
                xytext=(trajectory[-1, 0] + 330, trajectory[-1, 2] - 18),
                arrowprops={"arrowstyle": "->", "color": "#444444", "linewidth": 0.8},
                fontsize=7.5)
    for record, color in zip(records, colors, strict=True):
        release = np.asarray(record["release_point_m"], dtype=float)
        delay = record["fuse_delay_s"]
        elapsed = np.linspace(0.0, delay, 80)
        arc = release[None, :] + elapsed[:, None] * velocity[None, :]
        arc[:, 2] = release[2] - 0.5 * 9.8 * elapsed**2
        explosion = np.asarray(record["explosion_point_m"], dtype=float)
        if not np.allclose(arc[-1], explosion, atol=1e-6):
            raise RuntimeError(f"Q3 bomb {record['bomb']} ballistic arc does not reach frozen explosion point")
        ax.plot(arc[:, 0], arc[:, 2], color=color, linewidth=1.4)
        ax.scatter(release[0], release[2], s=26, facecolor="white", edgecolor=color,
                   linewidth=1.2, zorder=4)
        ax.scatter(explosion[0], explosion[2], s=38, marker="*", color=color, zorder=4)
        ax.annotate(str(record["bomb"]), (explosion[0], explosion[2]), xytext=(4, -1),
                    textcoords="offset points", color=color, fontsize=8)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("高度 $z$ / m")
    ax.set_title("(a) 共享航迹与三弹投放—起爆构型", loc="left")
    ax.grid(True, color="#E8E8E8", linewidth=0.6)
    ax.text(0.03, 0.05, f"共享航向 {q3['heading_deg']:.3f}°，速度 {q3['speed_m_s']:.3f} m/s",
            transform=ax.transAxes, fontsize=7.4,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.5})

    ax = axes[1]
    for row, (record, color) in enumerate(zip(records, colors, strict=True)):
        tau = record["release_time_s"]
        explosion = record["explosion_time_s"]
        left, right = record["assigned_target_intervals_s"][0]
        ax.plot([tau, explosion], [row, row], color="#777777", linewidth=1.0, zorder=1)
        ax.scatter(tau, row, s=26, facecolor="white", edgecolor=color, linewidth=1.2, zorder=3)
        ax.scatter(explosion, row, s=38, marker="*", color=color, zorder=3)
        ax.broken_barh([(left, right - left)], (row - 0.20, 0.40), facecolors=color, alpha=0.48)
    ax.set_yticks(range(3), ["烟幕弹 1", "烟幕弹 2", "烟幕弹 3"])
    ax.invert_yaxis()
    ax.set_xlim(0.0, 13.0)
    ax.set_xlabel("任务时刻 / s")
    ax.set_title("(b) 投放、起爆与独立完整窗口对应", loc="left")
    ax.grid(axis="x", color="#E8E8E8", linewidth=0.6)
    fig.legend(
        handles=[
            Line2D([], [], marker="o", markerfacecolor="white", markeredgecolor="#555555",
                   linestyle="none", label="投放"),
            Line2D([], [], marker="*", color="#555555", linestyle="none", label="起爆"),
            Patch(facecolor="#999999", alpha=0.48, label="独立完整窗口"),
        ],
        loc="outside lower center", ncol=3, frameon=False, fontsize=7.3,
    )
    save(fig, "fig_q3_shared_trajectory")


def draw_intervals(ax: plt.Axes, rows: list[tuple[str, list[list[float]], str]], union: list[list[float]]) -> None:
    labels = [label for label, _, _ in rows] + ["联合遮蔽"]
    for y, (_, intervals, color) in enumerate(rows):
        for left, right in intervals:
            ax.broken_barh([(left, right - left)], (y - 0.32, 0.64), facecolors=color, alpha=0.82)
    union_y = len(rows)
    for left, right in union:
        ax.broken_barh([(left, right - left)], (union_y - 0.32, 0.64),
                       facecolors=COLORS["gray"], alpha=0.88)
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.grid(axis="x", color="#E8E8E8", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("时间 / s")


def figure_intervals() -> None:
    q1, q3, q4 = (load_frozen(name) for name in ("q1.json", "q3.json", "q4.json"))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), constrained_layout=True)
    left, right = q1["shielding_intervals_s"][0]
    axes[0].broken_barh([(left, right - left)], (-0.32, 0.64), facecolors=COLORS["blue"], alpha=0.82)
    axes[0].set_yticks([0], ["有效遮蔽"])
    axes[0].grid(axis="x", color="#E8E8E8", linewidth=0.6)
    axes[0].set_axisbelow(True)
    axes[0].set_xlabel("时间 / s")
    axes[0].set_title(f"(a) Q1：单弹 {q1['effective_shielding_duration_s']:.3f} s", loc="left")

    rows3 = [
        (f"烟幕弹 {bomb['bomb']}", bomb["shielding_intervals_s"], color)
        for bomb, color in zip(q3["bombs"], (COLORS["blue"], COLORS["yellow"], COLORS["green"]), strict=True)
    ]
    draw_intervals(axes[1], rows3, q3["union_intervals_s"])
    axes[1].set_title(f"(b) Q3：三弹联合 {q3['effective_shielding_duration_s']:.3f} s", loc="left")

    rows4 = [
        (record["drone"], record["shielding_intervals_s"], DRONE_COLORS[record["drone"]])
        for record in q4["records"]
    ]
    draw_intervals(axes[2], rows4, q4["union_intervals_s"])
    axes[2].set_title(f"(c) Q4：三机联合 {q4['effective_shielding_duration_s']:.3f} s", loc="left")
    save(fig, "fig2_q1_q3_q4_intervals")


def figure_q5() -> None:
    q5 = load_frozen("q5.json")
    records = q5["records"]
    grouped = {
        missile: [record for record in records if record["assigned_missile"] == missile]
        for missile in ("M1", "M2", "M3")
    }
    heights = [len(grouped[name]) + 1 for name in ("M1", "M2", "M3")]
    fig = plt.figure(figsize=(7.2, 6.15), constrained_layout=True)
    outer = fig.add_gridspec(2, 1, height_ratios=(1.48, 1.0))
    upper = outer[0].subgridspec(3, 2, width_ratios=(3.8, 1.25), height_ratios=heights)
    timeline_axes = [fig.add_subplot(upper[index, 0]) for index in range(3)]
    heat_ax = fig.add_subplot(upper[:, 1])

    for index, (missile_name, ax) in enumerate(zip(("M1", "M2", "M3"), timeline_axes, strict=True)):
        rows = grouped[missile_name]
        union = q5["formal_b1"]["per_missile_union_intervals_s"][missile_name]
        for left, right in union:
            ax.broken_barh([(left, right - left)], (-0.32, 0.64),
                           facecolors=COLORS["light"], edgecolors=COLORS["gray"], linewidth=0.7)
        for row_index, record in enumerate(rows, 1):
            for left, right in record["assigned_target_intervals_s"]:
                ax.broken_barh(
                    [(left, right - left)],
                    (row_index - 0.32, 0.64),
                    facecolors=DRONE_COLORS[record["drone"]],
                    alpha=0.86,
                )
        for left, right in q5["joint_only_intervals_s"][missile_name]:
            ax.broken_barh([(left, right-left)], (-0.32, 0.64),
                           facecolors=COLORS["yellow"], edgecolors=COLORS["red"],
                           hatch="////", linewidth=0.65, alpha=0.8)
        labels = ["联合遮蔽"] + [f"{record['drone']}-{record['bomb']}" for record in rows]
        ax.set_yticks(range(len(labels)), labels)
        ax.invert_yaxis()
        maximum_end = max(b for values in q5['formal_b1']['per_missile_union_intervals_s'].values() for _,b in values)
        ax.set_xlim(0.0, 5.0 * math.ceil(maximum_end / 5.0))
        ax.grid(axis="x", color="#E8E8E8", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_title(
            f"{missile_name}：$L={q5['formal_b1']['per_missile_durations_s'][missile_name]:.3f}$ s",
            loc="left",
        )
        if index < 2:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("时间 / s")

    counts = np.array(
        [[sum(record["drone"] == drone and record["assigned_missile"] == missile for record in records)
          for missile in ("M1", "M2", "M3")] for drone in DRONE_COLORS]
    )
    image = heat_ax.imshow(counts, cmap=PALETTES["sequential"],
                           vmin=0, vmax=3, aspect="auto")
    heat_ax.set_xticks(range(3), ["M1", "M2", "M3"])
    heat_ax.set_yticks(range(5), list(DRONE_COLORS))
    heat_ax.set_title(f"资源指派（枚）\nB1 总目标 {q5['formal_b1']['objective_sum_s']:.3f} s")
    for row in range(5):
        for column in range(3):
            heat_ax.text(column, row, str(counts[row, column]), ha="center", va="center",
                         color=contrast_text(image.cmap(image.norm(counts[row, column]))), fontweight="bold")
    heat_ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    heat_ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    heat_ax.grid(which="minor", color="white", linewidth=1.2)
    heat_ax.tick_params(which="minor", bottom=False, left=False)

    lower = outer[1].subgridspec(2, 2, hspace=0.18, wspace=0.18)
    zoom_specs = [
        ("M1", (18.45, 18.90), [("FY5", 1), ("FY4", 2)],
         "(a) M1：18.5–18.9 s 互补与短缺口", (18.666575921185416, 18.70335108152723)),
        ("M1", (22.03, 22.27), [("FY4", 2), ("FY2", 2)],
         "(b) M1：22.09–22.21 s 窗口补接", None),
        ("M1", (40.35, 40.82), [("FY3", 2), ("FY3", 3)],
         "(c) M1：40.4–40.8 s 晚段互补", (40.46607645820133, 40.58139061854022)),
        ("M2", (14.00, 14.72), [("FY2", 1), ("FY4", 1)],
         "(d) M2：14.0–14.7 s 两段新增", None),
    ]
    record_index = {(record["drone"], record["bomb"]): record for record in records}
    for cell, (missile, xlim, keys, title, gap) in zip(
        [lower[0, 0], lower[0, 1], lower[1, 0], lower[1, 1]], zoom_specs, strict=True
    ):
        ax = fig.add_subplot(cell)
        union = q5["formal_b1"]["per_missile_union_intervals_s"][missile]
        joint_only = q5["joint_only_intervals_s"][missile]
        for left, right in union:
            ax.broken_barh([(left, right-left)], (-0.28, 0.56),
                           facecolors=COLORS["light"], edgecolors=COLORS["gray"], linewidth=0.65)
        for left, right in joint_only:
            ax.broken_barh([(left, right-left)], (-0.28, 0.56),
                           facecolors=COLORS["yellow"], edgecolors=COLORS["red"],
                           hatch="////", linewidth=0.6, alpha=0.82)
        labels = ["整体联合"]
        for row, key in enumerate(keys, 1):
            record = record_index[key]
            for left, right in record["assigned_target_intervals_s"]:
                ax.broken_barh([(left, right-left)], (row-0.28, 0.56),
                               facecolors=DRONE_COLORS[record["drone"]], alpha=0.85)
            labels.append(f"{record['drone']}-{record['bomb']}")
        ax.set_yticks(range(3), labels)
        ax.invert_yaxis()
        ax.set_xlim(*xlim)
        ax.set_xlabel("时间 / s")
        ax.set_title(title, loc="left", fontsize=8.6)
        ax.grid(axis="x", color="#E8E8E8", linewidth=0.55)
        ax.set_axisbelow(True)
        ax.set_box_aspect(0.18)
        ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(5))
        if gap is not None:
            midpoint = 0.5 * (gap[0] + gap[1])
            ax.annotate(
                f"剩余缺口\n{gap[1]-gap[0]:.4f} s",
                xy=(midpoint, 0.0), xytext=(midpoint, 1.62), ha="center", va="center",
                fontsize=6.9, color=COLORS["gray"],
                arrowprops={"arrowstyle": "-[", "color": COLORS["gray"],
                            "linewidth": 0.75, "shrinkA": 0, "shrinkB": 0},
            )

    fig.legend(
        handles=[
            Patch(facecolor=COLORS["light"], edgecolor=COLORS["gray"], label="整体联合完整区间"),
            Patch(facecolor=COLORS["blue"], alpha=0.85, label="单弹独立完整区间（颜色按无人机）"),
            Patch(facecolor=COLORS["yellow"], edgecolor=COLORS["red"], hatch="////",
                  label="纯联合新增"),
        ],
        loc="outside lower center", ncol=3, frameon=False,
    )

    save(fig, "fig3_q5_timeline_allocation")


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description="Generate paper figures from recorded evidence")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    OUTPUT = parser.parse_args().output_dir
    setup_style()
    figure_joint_mechanism()
    figure_geometry()
    figure_q2_response_refinement()
    figure_q3_shared_trajectory()
    figure_intervals()
    figure_q5()
    print("generated paper evidence figures from frozen results and recorded audits in PNG and PDF")


if __name__ == "__main__":
    main()
