import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def test_paper_reports_frozen_q34_evidence():
    paper = (PROJECT / "paper/paper.md").read_text(encoding="utf-8")
    evidence = json.loads((PROJECT / "results/q34_offline_evidence.json").read_text(encoding="utf-8"))

    assert len(evidence["cases"]) == 24
    assert all(case["cleared_ratio"] == 1.0 for case in evidence["cases"])
    for mode in ("q3", "q4"):
        summary = evidence["summary"][mode]["virtual_time_s"]
        assert f'{summary["median"]:.2f}' in paper
        assert f'{summary["max"]:.2f}' in paper


def test_paper_keeps_official_results_distinct_from_offline_results():
    paper = (PROJECT / "paper/paper.md").read_text(encoding="utf-8")

    assert "不是官方成功率" in paper
    assert "未执行：已过官方截止时间" in paper
    assert "加密日志" in paper


def test_paper_figures_and_delivery_document_exist():
    for relative in (
        "paper/figures/coverage_constructions.png",
        "paper/figures/offline_virtual_time.png",
        "paper/paper.docx",
    ):
        path = PROJECT / relative
        assert path.is_file() and path.stat().st_size > 0
