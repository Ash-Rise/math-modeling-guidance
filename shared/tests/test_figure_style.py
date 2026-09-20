"""Check style isolation and semantic encoding failure surfaces."""
import matplotlib as mpl
import pytest
import yaml
from matplotlib.figure import Figure
from PIL import Image

from shared.figure_style import PALETTES, PROFILE, category_styles, contrast_text, figure_size, paper_style, save_figure


def test_style_restores_after_exception():
    old = mpl.rcParams.copy()
    with pytest.raises(RuntimeError):
        with paper_style(fonts=["DejaVu Sans"], overrides={"font.size": 23}):
            assert mpl.rcParams["font.size"] == 23
            raise RuntimeError("failed plot")
    assert mpl.rcParams["font.size"] == old["font.size"]
    assert mpl.rcParams["font.family"] == old["font.family"]


def test_width_follows_profile_not_hardcoded(tmp_path):
    p = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    p["page"]["margins_twips"]["left"] += 1440
    changed = tmp_path / "profile.yaml"
    changed.write_text(yaml.safe_dump(p), encoding="utf-8")
    assert figure_size(profile_path=changed)[0] == pytest.approx(figure_size()[0] - 1)
    assert figure_size("compact")[0] == pytest.approx(figure_size()[0] / 2)


def test_categories_do_not_silently_repeat_or_drop():
    with pytest.raises(ValueError):
        category_styles(range(len(PALETTES["categorical"]) + 1))
    with pytest.raises(ValueError):
        category_styles(["A", "A"])
    mapping = category_styles(["A", "B", "C"])
    assert len({s["color"] for s in mapping.values()}) == 3
    with paper_style(fonts=["DejaVu Sans"]):
        ax = Figure().subplots()
        for style in mapping.values():
            line, = ax.plot([0, 1], [0, 1], **style)
            assert line.get_marker() == "None"
            assert line.get_linestyle() == "-"


def test_missing_font_is_explicit():
    with pytest.raises(ValueError):
        with paper_style(fonts=["MCM-nonexistent-font"]):
            pass


def test_ordinary_plot_cycle_uses_repository_palette_and_restores():
    old = mpl.rcParams["axes.prop_cycle"]
    with paper_style(fonts=["DejaVu Sans"]):
        cycle = mpl.rcParams["axes.prop_cycle"].by_key()
        assert cycle["color"] == list(PALETTES["categorical"])
        ax = Figure().subplots()
        for _ in range(len(PALETTES["categorical"])):
            line, = ax.plot([0, 1], [0, 1], color="black")
            assert line.get_linestyle() == "-"  # Explicit color must not advance an implicit dash cycle.
            assert line.get_marker() == "None"
        explicit, = ax.plot([0, 1], [1, 0], linestyle="--", marker="|")
        assert explicit.get_linestyle() == "--"
        assert explicit.get_marker() == "|"
    assert mpl.rcParams["axes.prop_cycle"] == old


def test_heatmap_labels_follow_color_not_value_direction():
    cmap = mpl.colormaps[PALETTES["sequential"]]
    assert contrast_text(cmap(0.0)) == "black"
    assert contrast_text(cmap(1.0)) == "white"
    reverse = cmap.reversed()
    assert contrast_text(reverse(0.0)) == "white"
    assert contrast_text(reverse(1.0)) == "black"


def test_export_dpi_reads_profile_despite_global_savefig_defaults(tmp_path):
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    profile["figures"]["raster_dpi_min"] += 50
    config = tmp_path / "profile.yaml"
    config.write_text(yaml.safe_dump(profile), encoding="utf-8")
    output = tmp_path / "figure.png"
    with mpl.rc_context({"savefig.dpi": 72}):
        save_figure(Figure(figsize=(1, 1)), output, profile_path=config)
    with Image.open(output) as image:
        assert image.format == "PNG"
        expected = profile["figures"]["raster_dpi_min"]
        assert image.info["dpi"] == pytest.approx((expected, expected), abs=.02)
        assert image.size == (expected, expected)


@pytest.mark.parametrize("dpi", [0, 72, float("nan"), float("inf")])
def test_bad_export_dpi_cannot_overwrite_an_existing_figure(tmp_path, dpi):
    output = tmp_path / "figure.png"
    output.write_bytes(b"existing approved figure")
    with pytest.raises(ValueError, match="raster_dpi_min"):
        save_figure(Figure(), output, dpi=dpi)
    assert output.read_bytes() == b"existing approved figure"


def test_export_format_contract_and_explicit_format_cannot_be_bypassed(tmp_path):
    with pytest.raises(ValueError, match="JPEG"):
        save_figure(Figure(), tmp_path / "figure.jpg")
    with pytest.raises(ValueError, match="suffix"):
        save_figure(Figure(), tmp_path / "figure.png", format="jpeg")
    output = tmp_path / "figure.pdf"
    save_figure(Figure(), output)
    assert output.read_bytes().startswith(b"%PDF")
    assert not output.with_suffix(".png").exists()  # No unsolicited companion formats.
    with pytest.raises(ValueError, match="Unsupported figure export format"):
        save_figure(Figure(), tmp_path / "figure.unknown")
    output = tmp_path / "figure.svg"
    save_figure(Figure(), output)
    assert "<svg" in output.read_text(encoding="utf-8")
