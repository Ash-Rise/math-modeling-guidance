"""Small, opt-in Matplotlib defaults; no data transforms or global import effects.

See templates/scientific-figure-guidance.md. Project semantics and approved layouts win.
"""
from contextlib import contextmanager
import math
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
import yaml

PROFILE = Path(__file__).parent / "templates/personal-paper-profile.yaml"

# Paul Tol Bright, original order and hex values (SciencePlots bright.mplstyle).
# https://github.com/garrettj403/SciencePlots/blob/master/src/scienceplots/styles/color/bright.mplstyle
# Categorical only; redundant encoding and actual-figure QA remain necessary.
PALETTES = {
    "categorical": ("#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"),
    "sequential": "Greens",
    "diverging": "PRGn",
    "highlight": {"focus": "#4477AA", "reference": "#707070"},
}


def contrast_text(background):
    """Choose black/white text by rendered opaque background relative luminance.

    For alpha fills pass the composited color, not the uncomposited RGBA.
    """
    rgb = mpl.colors.to_rgb(background)
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    luminance = sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))
    return "black" if (luminance + .05) / .05 >= 1.05 / (luminance + .05) else "white"


def _profile(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def figure_size(preset="wide", *, height=None, profile_path=PROFILE):
    """Inches, derived from current profile text width; optional height in inches."""
    p = _profile(profile_path)
    page = p["page"]
    width = (page["width_twips"] - page["margins_twips"]["left"]
             - page["margins_twips"]["right"]) / 1440
    fraction, ratio = p["figures"]["matplotlib"]["size_presets"][preset]
    width *= fraction
    if height is not None and height <= 0:
        raise ValueError("height must be positive")
    return width, width * ratio if height is None else height


def save_figure(fig, path, *, dpi=None, profile_path=PROFILE, **kwargs):
    """Export a profile-owned figure, checking format and resolution before writing.

    This checks export resolution, not effective DPI after placement in Word.
    Existing project layouts continue to own figure size and chart design.
    The explicit suffix is the consumer's format choice (PDF is valid too).
    """
    rules = _profile(profile_path)["figures"]
    path = Path(path)
    output_format = path.suffix.lstrip(".").lower()
    requested_format = kwargs.pop("format", output_format).lower()
    if requested_format != output_format:
        raise ValueError("Figure format must match the output suffix")
    if rules["no_jpeg_for_quantitative_charts"] and output_format in {"jpg", "jpeg"}:
        raise ValueError("Profile forbids JPEG for quantitative charts")
    if output_format not in fig.canvas.get_supported_filetypes():
        raise ValueError(f"Unsupported figure export format: {output_format!r}")
    dpi = float(rules["raster_dpi_min"] if dpi is None else dpi)
    if not math.isfinite(dpi) or dpi < rules["raster_dpi_min"]:
        raise ValueError(f"Figure dpi must be at least profile raster_dpi_min={rules['raster_dpi_min']}")
    # Passing format and dpi explicitly prevents rcParams or kwargs from bypassing
    # the profile. DPI also controls any rasterized artists in a vector export.
    fig.savefig(path, format=output_format, dpi=dpi, **kwargs)


def category_styles(keys):
    """Assign colors once in semantic order, reuse across panels and subsets.

    Labels, panel position and explicitly chosen line styles distinguish roles.
    Do not add markers or textures merely because there are multiple categories.
    More than seven groups needs an explicit design, not silent color cycling.
    """
    keys = list(keys)
    if len(set(keys)) != len(keys) or len(keys) > len(PALETTES["categorical"]):
        raise ValueError("Use distinct keys, at most seven; otherwise design grouping explicitly")
    return {key: {"color": PALETTES["categorical"][i]}
            for i, key in enumerate(keys)}


@contextmanager
def paper_style(*, fonts=None, overrides=None, profile_path=PROFILE):
    """Scoped style; report missing configured fonts rather than silently use tofu.

    `fonts` explicitly overrides the profile for another installed font family.
    This verifies font availability, not full glyph coverage: render QA remains.
    """
    p = _profile(profile_path)
    if fonts is None:
        typography = p["typography"]
        fonts = [typography["latin_font"], typography["body"]["east_asia_font"]]
        # Matplotlib exposes the installed Song family by its English name.
        fonts = ["SimSun" if name == "宋体" else name for name in fonts]
    for name in fonts:
        font_manager.findfont(font_manager.FontProperties(family=name),
                              fallback_to_default=False)
    rc = dict(p["figures"]["matplotlib"]["rc"])
    rc.update({"axes.prop_cycle": mpl.cycler(color=PALETTES["categorical"]),
               "font.family": list(fonts),
               "savefig.dpi": p["figures"]["raster_dpi_min"]})
    rc.update(overrides or {})
    with mpl.rc_context(rc):
        yield
