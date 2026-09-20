"""Apply and validate the repository-wide paper formatting profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.oxml import parse_xml, serialize_part_xml
from docx.shared import Pt, RGBColor, Twips
from docx.table import _Cell
from docx.text.run import Run


PROFILE_PATH = Path(__file__).resolve().parent / "templates" / "personal-paper-profile.yaml"
_ALIGNMENTS = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def load_profile(path: Path = PROFILE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    if not isinstance(profile, dict):
        raise ValueError(f"Paper profile must be a mapping: {path}")
    return profile


def _remove_numbering(element) -> None:
    properties = element.get_or_add_pPr()
    numbering = properties.find(qn("w:numPr"))
    if numbering is not None:
        properties.remove(numbering)


def _set_run_format(run, typography: dict[str, Any], *, bold: bool | None = None) -> None:
    latin_font = typography["latin_font"]
    run.font.name = latin_font
    run.font.size = Pt(typography["size_pt"])
    run.font.color.rgb = RGBColor.from_string(typography["font_color_hex"])
    if bold is None:
        bold = typography.get("bold")
    if bold is not None:
        run.bold = bool(bold)
    italic = typography.get("italic")
    if italic is not None:
        run.italic = bool(italic)
    fonts = run._r.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:ascii"), latin_font)
    fonts.set(qn("w:hAnsi"), latin_font)
    fonts.set(qn("w:eastAsia"), typography["east_asia_font"])


def _apply_paragraph_format(paragraph, typography: dict[str, Any]) -> None:
    paragraph.alignment = _ALIGNMENTS[typography["alignment"]]
    paragraph.paragraph_format.line_spacing = typography["line_spacing_multiple"]
    paragraph.paragraph_format.space_before = Pt(typography.get("space_before_pt", 0))
    paragraph.paragraph_format.space_after = Pt(typography.get("space_after_pt", 0))
    if "snap_to_grid" in typography:
        _set_paragraph_snap_to_grid(paragraph, typography["snap_to_grid"])
    if "first_line_indent_pt" in typography:
        paragraph.paragraph_format.first_line_indent = Pt(typography["first_line_indent_pt"])
    _set_character_indent(paragraph._p.get_or_add_pPr(), typography)
    for run in _text_runs(paragraph):
        _set_run_format(run, typography)


def _text_runs(paragraph):
    """Include hyperlink text, which Paragraph.runs does not expose."""
    return [Run(node, paragraph) for node in paragraph._p.findall('.//' + qn('w:r'))]


_CAPTION_LABEL = re.compile(r"^([图表])\s*((?:[A-Z][.-])?\d+(?:[.-]\d+)*)(\s+)(?=\S)")
_CAPTION_STYLES = {"Table Caption": "表", "Image Caption": "图"}


def _neighbor_block(paragraph, *, before: bool):
    node = paragraph._p.getprevious() if before else paragraph._p.getnext()
    while node is not None and node.tag == qn("w:p"):
        # Ignore empty spacer paragraphs, but never cross a section/page break.
        if (node.findall('.//' + qn('w:t')) or node.findall('.//' + qn('w:drawing'))
                or node.findall('.//' + qn('m:oMath'))
                or node.findall('.//' + qn('w:sectPr'))
                or node.findall('.//' + qn('w:br'))):
            break
        node = node.getprevious() if before else node.getnext()
    return node


def _is_caption_object(node, kind: str) -> bool:
    if node is None:
        return False
    if kind == "表":
        return node.tag == qn("w:tbl")
    return node.tag == qn("w:p") and bool(node.findall('.//' + qn('w:drawing')))


def _caption_kind(paragraph, *, infer_body_text: bool = False) -> str | None:
    """Explicit styles win; infer unstyled captions only next to an object.

    The known Markdown builder may opt into inference for Pandoc Body Text.
    General DOCX processing preserves an explicitly assigned body style.
    """
    style = paragraph.style.name if paragraph.style else ""
    if style in _CAPTION_STYLES:
        return _CAPTION_STYLES[style]
    match = _CAPTION_LABEL.match(paragraph.text.strip())
    if match is None:
        return None
    if style == "Caption":
        return match[1]
    allowed_styles = {"Normal", ""}
    if infer_body_text:
        allowed_styles.update({"Body Text", "First Paragraph"})
    if style not in allowed_styles:
        return None
    if infer_body_text:
        # The Markdown builder puts table captions above their table and figure
        # captions below their image, so infer only from that position: a sentence
        # that merely mentions 表5-6 next to a table stays body text.
        before = match[1] == "图"
        if _is_caption_object(_neighbor_block(paragraph, before=before), match[1]):
            return match[1]
        return None
    if any(_is_caption_object(_neighbor_block(paragraph, before=before), match[1])
           for before in (False, True)):
        return match[1]
    return None


def mark_pandoc_captions(document) -> None:
    """Mark standalone object-adjacent labels in the known Pandoc conversion."""
    for paragraph in document.paragraphs:
        kind = _caption_kind(paragraph, infer_body_text=True)
        if kind:
            name = "Table Caption" if kind == "表" else "Image Caption"
            if name not in document.styles:
                document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            paragraph.style = document.styles[name]


def _style_chain(style):
    while style is not None:
        yield style
        style = style.base_style


def _paragraph_value(paragraph, attribute):
    for item in [paragraph, *_style_chain(paragraph.style)]:
        value = getattr(item.paragraph_format, attribute)
        if value is not None:
            return value
    return None


def _run_value(run, paragraph, attribute):
    for item in [run, *_style_chain(run.style), *_style_chain(paragraph.style)]:
        value = getattr(item.font, attribute)
        if value is not None:
            return value
    return None


def _validate_typography(paragraph, typography, common, label, *, check_indent=True):
    """Check the effective formatting, including style-inherited values."""
    errors = []
    expected = {
        "alignment": _ALIGNMENTS[typography["alignment"]],
        "line_spacing": typography["line_spacing_multiple"],
        "space_before": Pt(typography.get("space_before_pt", 0)),
        "space_after": Pt(typography.get("space_after_pt", 0)),
    }
    if check_indent:
        expected["first_line_indent"] = Pt(typography.get("first_line_indent_pt", 0))
    for attribute, value in expected.items():
        if _paragraph_value(paragraph, attribute) != value:
            errors.append(f"{label} {attribute} 不符合 profile")
    if check_indent:
        chars = None
        for item in [paragraph._p, *(s.element for s in _style_chain(paragraph.style))]:
            ind = item.find('./' + qn('w:pPr') + '/' + qn('w:ind'))
            if ind is not None and ind.get(qn('w:firstLineChars')) is not None:
                chars = ind.get(qn('w:firstLineChars'))
                break
        if (chars or "0") != str(round(100 * typography.get("first_line_indent_chars", 0))):
            errors.append(f"{label} first_line_indent_chars 不符合 profile")
    for index, run in enumerate(_text_runs(paragraph), start=1):
        if not run.text.strip():
            continue
        prefix = f"{label} run {index}"
        if _run_value(run, paragraph, "size") != Pt(typography["size_pt"]):
            errors.append(f"{prefix} size_pt 不符合 profile")
        if "bold" in typography and bool(_run_value(run, paragraph, "bold")) != typography["bold"]:
            errors.append(f"{prefix} bold 不符合 profile")
        for attribute, value in (("ascii", common["latin_font"]),
                                 ("hAnsi", common["latin_font"]),
                                 ("eastAsia", typography["east_asia_font"])):
            actual = None
            for item in [run._r, *(s.element for s in _style_chain(run.style)),
                         *(s.element for s in _style_chain(paragraph.style))]:
                fonts = item.find('./' + qn('w:rPr') + '/' + qn('w:rFonts'))
                if fonts is not None and fonts.get(qn('w:' + attribute)) is not None:
                    actual = fonts.get(qn('w:' + attribute))
                    break
            if actual != value:
                errors.append(f"{prefix} font.{attribute} 不符合 profile")
    return errors


def validate_docx_captions(document, profile: dict[str, Any] | None = None) -> list[str]:
    """Check caption identity, adjacency and table-above/figure-below order."""
    profile = profile or load_profile()
    errors = []
    seen = set()
    for index, paragraph in enumerate(document.paragraphs, start=1):
        kind = _caption_kind(paragraph)
        if kind is None:
            if paragraph.style.name == "Caption":
                errors.append(f"第 {index} 段题注缺少可识别的图表编号与名称间隔")
            continue
        label = f"第 {index} 段{kind}题"
        match = _CAPTION_LABEL.match(paragraph.text.strip())
        if match is None or match[1] != kind:
            errors.append(f"{label} 编号或题注样式不匹配")
        else:
            identity = (kind, tuple(int(part) if part.isdigit() else part.upper()
                                    for part in re.split(r"[.-]", match[2])))
            if identity in seen:
                errors.append(f"{label} 编号重复: {kind}{match[2]}")
            seen.add(identity)
            if match[3] != profile["typography"]["caption"]["label_separator"]:
                errors.append(f"{label} label_separator 不符合 profile")
        if not _is_caption_object(_neighbor_block(paragraph, before=(kind == "图")), kind):
            errors.append(f"{label} 须紧邻对应对象并位于{'表格上方' if kind == '表' else '图片下方'}")
    return errors


def _set_character_indent(properties, typography: dict[str, Any]) -> None:
    indent = properties.find(qn("w:ind"))
    if "first_line_indent_chars" in typography:
        if indent is None:
            indent = OxmlElement("w:ind")
            properties.insert_element_before(indent, "w:contextualSpacing", "w:jc", "w:outlineLvl")
        indent.set(qn("w:firstLineChars"), str(round(100 * typography["first_line_indent_chars"])))
    elif indent is not None:
        # An explicit zero is needed to override Normal's character-based indent.
        indent.set(qn("w:firstLineChars"), "0")


def _normalize_caption_separator(paragraph, separator: str) -> None:
    match = re.match(r"^([图表]\s*(?:[A-Z][.-])?\d+(?:[.-]\d+)*)\s+", paragraph.text)
    if match is None:
        return
    start, end = match.end(1), match.end()
    offset = 0
    inserted = False
    for node in paragraph._p.findall(".//" + qn("w:t")):
        value = node.text or ""
        next_offset = offset + len(value)
        if offset < end and next_offset > start:
            left, right = max(0, start - offset), min(len(value), end - offset)
            node.text = value[:left] + ("" if inserted else separator) + value[right:]
            node.set(qn("xml:space"), "preserve")
            inserted = True
        offset = next_offset
        if offset >= end:
            break


def _set_paragraph_snap_to_grid(paragraph, enabled: bool) -> None:
    properties = paragraph._p.get_or_add_pPr()
    snap = properties.find(qn("w:snapToGrid"))
    if snap is None:
        snap = OxmlElement("w:snapToGrid")
        properties.insert_element_before(
            snap,
            "w:spacing",
            "w:ind",
            "w:contextualSpacing",
            "w:mirrorIndents",
            "w:suppressOverlap",
            "w:jc",
            "w:textDirection",
            "w:textAlignment",
            "w:textboxTightWrap",
            "w:outlineLvl",
            "w:divId",
            "w:cnfStyle",
            "w:rPr",
            "w:sectPr",
            "w:pPrChange",
        )
    snap.set(qn("w:val"), "1" if enabled else "0")


def _set_document_grid(section, grid_profile: dict[str, Any]) -> None:
    grid = section._sectPr.find(qn("w:docGrid"))
    if grid is None:
        grid = OxmlElement("w:docGrid")
        section._sectPr.append(grid)
    grid.set(qn("w:type"), str(grid_profile["type"]))
    grid.set(qn("w:linePitch"), str(grid_profile["line_pitch_twips"]))
    grid.set(qn("w:charSpace"), str(grid_profile["char_space_twips"]))


def _set_page_gutter(section) -> None:
    margins = section._sectPr.find(qn("w:pgMar"))
    if margins is None:
        raise ValueError("Section page margins were not created")
    margins.set(qn("w:gutter"), "0")


def _set_page_field(footer, typography: dict[str, Any]) -> None:
    element = footer._element
    for child in list(element):
        element.remove(child)
    paragraph = footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def add_formatted_run():
        run = paragraph.add_run()
        _set_run_format(run, typography)
        return run._r

    for field_type, instruction in (
        ("begin", None),
        (None, " PAGE "),
        ("separate", None),
    ):
        run = add_formatted_run()
        if field_type is not None:
            field = OxmlElement("w:fldChar")
            field.set(qn("w:fldCharType"), field_type)
            run.append(field)
        else:
            text = OxmlElement("w:instrText")
            text.set(qn("xml:space"), "preserve")
            text.text = instruction
            run.append(text)
    result_run = add_formatted_run()
    result = OxmlElement("w:t")
    result.text = "1"
    result_run.append(result)
    end_run = add_formatted_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run.append(end)


def _set_math_font(document, font_name: str) -> None:
    settings = document.settings._element
    math_properties = settings.find(qn("m:mathPr"))
    if math_properties is None:
        math_properties = OxmlElement("m:mathPr")
        theme_language = settings.find(qn("w:themeFontLang"))
        if theme_language is None:
            settings.append(math_properties)
        else:
            settings.insert(settings.index(theme_language), math_properties)
    math_font = math_properties.find(qn("m:mathFont"))
    if math_font is None:
        math_font = OxmlElement("m:mathFont")
        math_properties.insert(0, math_font)
    math_font.set(qn("m:val"), font_name)


def _set_math_run_font(document, font_name: str) -> None:
    """Prevent WPS from substituting Segoe Print inside native equations."""
    for math_run in document.element.findall(".//" + qn("m:r")):
        run_properties = math_run.find(qn("w:rPr"))
        if run_properties is None:
            run_properties = OxmlElement("w:rPr")
            insertion_index = 1 if math_run.find(qn("m:rPr")) is not None else 0
            math_run.insert(insertion_index, run_properties)
        fonts = run_properties.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            run_properties.insert(0, fonts)
        for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn(f"w:{attribute}"), font_name)


def _find_package_part(document, partname: str):
    return next(
        (part for part in document.part.package.parts if str(part.partname) == partname),
        None,
    )


def _sync_theme_fonts(document, *, latin_font: str, east_asia_font: str) -> set[str]:
    """Replace generator-default theme fonts with profile-owned fallbacks."""
    part = _find_package_part(document, "/word/theme/theme1.xml")
    if part is None:
        return set()
    root = parse_xml(part.blob)
    replaced_fonts: set[str] = set()
    for family_name in ("majorFont", "minorFont"):
        family = root.find(".//" + qn(f"a:{family_name}"))
        if family is None:
            continue
        for element_name, font_name in (
            ("latin", latin_font),
            ("ea", east_asia_font),
            ("cs", latin_font),
        ):
            element = family.find(qn(f"a:{element_name}"))
            if element is None:
                continue
            previous = element.get("typeface")
            if previous and previous != font_name:
                replaced_fonts.add(previous)
            element.set("typeface", font_name)
    part._blob = serialize_part_xml(root)
    return replaced_fonts


def _set_explicit_rfonts(element, *, latin_font: str, east_asia_font: str) -> None:
    rfonts = element.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        element.insert(0, rfonts)
    for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "csTheme"):
        rfonts.attrib.pop(qn(f"w:{attribute}"), None)
    for attribute, font_name in (
        ("ascii", latin_font),
        ("hAnsi", latin_font),
        ("eastAsia", east_asia_font),
        ("cs", latin_font),
    ):
        rfonts.set(qn(f"w:{attribute}"), font_name)


def _set_literal_text_color(element, color_hex: str) -> None:
    color = element.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        element.append(color)
    for attribute in ("themeColor", "themeShade", "themeTint"):
        color.attrib.pop(qn(f"w:{attribute}"), None)
    color.set(qn("w:val"), color_hex)


def _sync_style_resources(document, profile: dict[str, Any]) -> None:
    """Make inherited text styles use profile-owned fonts and literal colors."""
    typography = profile["typography"]
    common = {
        "latin_font": typography["latin_font"],
        "font_color_hex": typography["font_color_hex"],
    }
    style_profiles = {
        "Normal": dict(typography["body"], **common),
        "Body Text": dict(typography["body"], **common),
        "Title": dict(typography["title"], **common),
        "Heading 1": dict(typography["heading_level_1"], **common),
        "Heading 2": dict(typography["heading_level_2_and_3"], **common),
        "Heading 3": dict(typography["heading_level_2_and_3"], **common),
        "Heading 4": dict(typography["heading_level_2_and_3"], **common),
        "Caption": dict(typography["caption"], **common),
        "Image Caption": dict(typography["caption"], **common),
        "Table Caption": dict(typography["caption"], **common),
        "Table Text": dict(typography["table_text"], **common),
    }
    for style_name, style_profile in style_profiles.items():
        try:
            style = document.styles[style_name]
        except KeyError:
            style = document.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
            style.base_style = document.styles["Normal"]
        style_element = style.element
        rpr = style_element.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            style_element.append(rpr)
        _set_explicit_rfonts(
            rpr,
            latin_font=style_profile["latin_font"],
            east_asia_font=style_profile["east_asia_font"],
        )
        _set_literal_text_color(rpr, style_profile["font_color_hex"])
        style.font.size = Pt(style_profile["size_pt"])
        style.font.bold = style_profile.get("bold", False)
        style.paragraph_format.alignment = _ALIGNMENTS[style_profile["alignment"]]
        style.paragraph_format.line_spacing = style_profile["line_spacing_multiple"]
        style.paragraph_format.space_before = Pt(style_profile.get("space_before_pt", 0))
        style.paragraph_format.space_after = Pt(style_profile.get("space_after_pt", 0))
        if "first_line_indent_pt" in style_profile:
            style.paragraph_format.first_line_indent = Pt(
                style_profile["first_line_indent_pt"]
            )
        else:
            style.paragraph_format.first_line_indent = Pt(0)
        _set_character_indent(style.element.get_or_add_pPr(), style_profile)


def normalize_pandoc_heading_hierarchy(document) -> None:
    """Convert the known Pandoc title/H2 hierarchy to Title/H1 explicitly."""
    if not document.paragraphs:
        raise ValueError("The Pandoc-generated document has no paragraphs")
    first = document.paragraphs[0]
    first_style = first.style.name if first.style else ""
    if first_style not in {"Title", "Heading 1"}:
        raise ValueError(
            "Unexpected Pandoc title style: "
            f"{first_style!r}; expected 'Title' or 'Heading 1'"
        )
    if not any(
        paragraph.style is not None and paragraph.style.name == "Heading 2"
        for paragraph in document.paragraphs[1:]
    ):
        raise ValueError("Pandoc heading normalization requires body Heading 2 paragraphs")
    first.style = document.styles["Title"]
    for paragraph in document.paragraphs[1:]:
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name == "Heading 2":
            paragraph.style = document.styles["Heading 1"]
        elif style_name == "Heading 3":
            paragraph.style = document.styles["Heading 2"]
        elif style_name == "Heading 4":
            paragraph.style = document.styles["Heading 3"]


def _sync_doc_defaults(document, profile: dict[str, Any]) -> None:
    """Remove theme-font inheritance from the document default run style."""
    typography = profile["typography"]
    settings = document.styles.element
    defaults = settings.find(qn("w:docDefaults"))
    if defaults is None:
        defaults = OxmlElement("w:docDefaults")
        settings.insert(0, defaults)
    rpr_default = defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        rpr_default = OxmlElement("w:rPrDefault")
        defaults.insert(0, rpr_default)
    rpr = rpr_default.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        rpr_default.append(rpr)
    _set_explicit_rfonts(
        rpr,
        latin_font=typography["latin_font"],
        east_asia_font=typography["body"]["east_asia_font"],
    )
    _set_literal_text_color(rpr, typography["font_color_hex"])


def _collect_explicit_font_names(document) -> set[str]:
    """Collect font names that remain explicitly referenced after normalization."""
    names: set[str] = set()
    for partname in (
        "/word/document.xml",
        "/word/styles.xml",
        "/word/settings.xml",
        "/word/theme/theme1.xml",
    ):
        part = _find_package_part(document, partname)
        if part is None:
            continue
        root = parse_xml(part.blob)
        for element in root.iter():
            for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
                value = element.get(qn(f"w:{attribute}"))
                if value:
                    names.add(value)
            if element.tag in {
                qn("m:mathFont"),
                qn("a:latin"),
                qn("a:ea"),
                qn("a:cs"),
            }:
                value = element.get("typeface") or element.get(qn("m:val"))
                if value:
                    names.add(value)
    return names


def _sync_font_table(
    document,
    *,
    removed_fonts: set[str],
    required_fonts: set[str],
    prune_unreferenced: bool = True,
) -> None:
    part = _find_package_part(document, "/word/fontTable.xml")
    if part is None:
        return
    root = parse_xml(part.blob)
    for font in list(root.findall(qn("w:font"))):
        if font.get(qn("w:name")) in removed_fonts or (
            prune_unreferenced and font.get(qn("w:name")) not in required_fonts
        ):
            root.remove(font)
    existing = {font.get(qn("w:name")) for font in root.findall(qn("w:font"))}
    for font_name in sorted(required_fonts - existing):
        font = OxmlElement("w:font")
        font.set(qn("w:name"), font_name)
        root.append(font)
    part._blob = serialize_part_xml(root)


def normalize_docx_resources(document, profile: dict[str, Any] | None = None) -> None:
    """Normalize theme, inherited styles, defaults, and the DOCX font table."""
    profile = profile or load_profile()
    typography = profile["typography"]
    replaced_theme_fonts = _sync_theme_fonts(
        document,
        latin_font=typography["latin_font"],
        east_asia_font=typography["body"]["east_asia_font"],
    )
    _sync_style_resources(document, profile)
    _sync_doc_defaults(document, profile)
    required_fonts = _collect_explicit_font_names(document)
    required_fonts.update(
        {
            typography["latin_font"],
            typography["body"]["east_asia_font"],
            typography["title"]["east_asia_font"],
            typography["heading_level_1"]["east_asia_font"],
            typography["heading_level_2_and_3"]["east_asia_font"],
            profile["equations"]["math_font"],
        }
    )
    _sync_font_table(
        document,
        removed_fonts=replaced_theme_fonts,
        required_fonts=required_fonts,
        prune_unreferenced=profile.get("docx", {}).get(
            "prune_unreferenced_font_table_entries", True
        ),
    )


def validate_docx_resources(document, profile: dict[str, Any] | None = None) -> list[str]:
    """Return resource/style violations that can trigger cross-editor substitutions."""
    profile = profile or load_profile()
    typography = profile["typography"]
    errors: list[str] = []
    theme_part = _find_package_part(document, "/word/theme/theme1.xml")
    if theme_part is not None:
        theme = parse_xml(theme_part.blob)
        expected = {
            "majorFont": (typography["latin_font"], typography["body"]["east_asia_font"], typography["latin_font"]),
            "minorFont": (typography["latin_font"], typography["body"]["east_asia_font"], typography["latin_font"]),
        }
        for family_name, expected_values in expected.items():
            family = theme.find(".//" + qn(f"a:{family_name}"))
            if family is None:
                errors.append(f"主题缺少 {family_name}")
                continue
            actual_values = []
            for element_name in ("latin", "ea", "cs"):
                element = family.find(qn(f"a:{element_name}"))
                actual_values.append(element.get("typeface", "") if element is not None else "")
            actual = tuple(actual_values)
            if actual != expected_values:
                errors.append(f"主题 {family_name} 字体不符合 profile: {actual}")

    styles_part = _find_package_part(document, "/word/styles.xml")
    if styles_part is not None:
        styles = parse_xml(styles_part.blob)
        expected_styles = {"Title", "Heading1", "Heading2", "Heading3", "Heading4"}
        for style in styles.findall(qn("w:style")):
            if style.get(qn("w:styleId")) not in expected_styles:
                continue
            color = style.find("./" + qn("w:rPr") + "/" + qn("w:color"))
            if color is None or color.get(qn("w:val")) != typography["font_color_hex"]:
                errors.append(f"样式 {style.get(qn('w:styleId'))} 未使用 profile 文字颜色")
            if color is not None and any(
                color.get(qn(f"w:{attribute}"))
                for attribute in ("themeColor", "themeShade", "themeTint")
            ):
                errors.append(f"样式 {style.get(qn('w:styleId'))} 仍继承主题颜色")

    font_table_part = _find_package_part(document, "/word/fontTable.xml")
    if font_table_part is not None:
        font_table = parse_xml(font_table_part.blob)
        explicit = _collect_explicit_font_names(document)
        explicit.update(
            {
                typography["latin_font"],
                typography["body"]["east_asia_font"],
                typography["title"]["east_asia_font"],
                typography["heading_level_1"]["east_asia_font"],
                typography["heading_level_2_and_3"]["east_asia_font"],
                profile["equations"]["math_font"],
            }
        )
        table_names = {
            font.get(qn("w:name"))
            for font in font_table.findall(qn("w:font"))
            if font.get(qn("w:name"))
        }
        stale = sorted(table_names - explicit)
        if stale:
            errors.append("fontTable.xml 含未被文档引用的字体: " + ", ".join(stale))
        if any(name.casefold().startswith("aptos") for name in table_names):
            errors.append("fontTable.xml 仍含 Aptos 字体")
    return errors


def validate_docx_layout(document, profile: dict[str, Any] | None = None) -> list[str]:
    """Return violations of stable page, heading, and body-layout invariants."""
    profile = profile or load_profile()
    page = profile["page"]
    typography = profile["typography"]
    errors: list[str] = []
    expected_section_values = {
        "page_width": page["width_twips"],
        "page_height": page["height_twips"],
        "top_margin": page["margins_twips"]["top"],
        "bottom_margin": page["margins_twips"]["bottom"],
        "left_margin": page["margins_twips"]["left"],
        "right_margin": page["margins_twips"]["right"],
        "header_distance": page["header_distance_twips"],
        "footer_distance": page["footer_distance_twips"],
    }
    for index, section in enumerate(document.sections, start=1):
        if section.orientation != WD_ORIENT.PORTRAIT:
            errors.append(
                f"第 {index} 节 orientation={section.orientation}，应为 portrait"
            )
        for attribute, expected in expected_section_values.items():
            value = getattr(section, attribute)
            actual = value.twips if value is not None else None
            if actual != expected:
                errors.append(
                    f"第 {index} 节 {attribute}={actual}，应为 {expected} twips"
                )
        if section.different_first_page_header_footer != page["different_first_page"]:
            errors.append(f"第 {index} 节 different_first_page 不符合 profile")
        grid = section._sectPr.find(qn("w:docGrid"))
        for attribute, key in (("type", "type"), ("linePitch", "line_pitch_twips"),
                               ("charSpace", "char_space_twips")):
            if grid is None or grid.get(qn(f"w:{attribute}")) != str(page["document_grid"][key]):
                errors.append(f"第 {index} 节 document_grid.{key} 不符合 profile")

    expected_alignments = {
        "Heading 1": _ALIGNMENTS[typography["heading_level_1"]["alignment"]],
        "Heading 2": _ALIGNMENTS[
            typography["heading_level_2_and_3"]["alignment"]
        ],
        "Heading 3": _ALIGNMENTS[
            typography["heading_level_2_and_3"]["alignment"]
        ],
        "Heading 4": _ALIGNMENTS[
            typography["heading_level_2_and_3"]["alignment"]
        ],
    }
    for style_name, expected in expected_alignments.items():
        try:
            actual = document.styles[style_name].paragraph_format.alignment
        except KeyError:
            continue
        if actual != expected:
            errors.append(f"样式 {style_name} 对齐方式不符合 profile")

    in_short_appendix = False
    expected_body_spacing = typography["body"]["line_spacing_multiple"]
    for index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.startswith("Heading"):
            if text.startswith("附录"):
                in_short_appendix = True
            expected = expected_alignments.get(style_name)
            if expected is not None and paragraph.alignment != expected:
                errors.append(f"第 {index} 段 {style_name} 对齐方式不符合 profile")
            continue
        if (
            not text
            or index == 1
            or in_short_appendix
            or _caption_kind(paragraph) is not None
            or re.match(r"^\[\d+\]", text)
            or paragraph._p.findall(".//" + qn("w:drawing"))
        ):
            continue
        actual_spacing = paragraph.paragraph_format.line_spacing
        if not isinstance(actual_spacing, (int, float)) or not abs(
            actual_spacing - expected_body_spacing
        ) < 1e-9:
            errors.append(
                f"第 {index} 段正文行距不符合 profile: {actual_spacing!r}"
            )
    in_short_appendix = False
    for index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()
        style = paragraph.style.name if paragraph.style else ""
        if style.startswith("Heading") and text.startswith("附录"):
            in_short_appendix = True
        if not text or paragraph._p.findall('.//' + qn('w:drawing')):
            continue
        if style == "Title":
            key = "title"
        elif style.startswith("Heading"):
            key = "heading_level_1" if style == "Heading 1" else "heading_level_2_and_3"
        elif _caption_kind(paragraph):
            key = "caption"
        elif (in_short_appendix or re.match(r"^\[\d+\]", text)
              or paragraph._p.findall(qn('m:oMathPara'))
              or any("SEQ Equation" in (n.text or "") for n in
                     paragraph._p.findall('.//' + qn('w:instrText')))):
            continue
        else:
            key = "body"
        rules = dict(typography[key])
        if text.startswith("关键词"):
            rules.update(first_line_indent_pt=0, first_line_indent_chars=0)
        errors.extend(_validate_typography(
            paragraph, rules, typography, f"第 {index} 段 {key}",
            check_indent=paragraph._p.get_or_add_pPr().find(qn('w:numPr')) is None,
        ))
    errors.extend(validate_docx_captions(document, profile))
    return errors


def _physical_cells(table, row) -> list[_Cell]:
    """Return one cell per physical ``w:tc`` in ``row``.

    python-docx resolves a vertically merged cell to the merge *origin* ``w:tc`` for
    every continuation row, so ``row.cells`` maps several rows onto one element.
    Formatting and validating through it therefore writes a row's borders into another
    row's cell and then reports the mismatch on the merged group. Working on the
    physical cells keeps each ``w:tc`` self-consistent.
    """
    return [_Cell(tc, table) for tc in row._tr.findall(qn("w:tc"))]


def validate_docx_tables(document, profile: dict[str, Any] | None = None) -> list[str]:
    """Check shared table defaults before a project's approved layout overrides.

    Deliberately separate from validate_docx_layout: accepted project layouts can
    own cell margins and compact-table typography after the shared formatting step.
    """
    profile = profile or load_profile()
    rules = profile["tables"]
    errors = []
    for table_index, table in enumerate(document.tables, start=1):
        for row_index, row in enumerate(table.rows):
            label = f"表 {table_index} 行 {row_index + 1}"
            for tag, expected in (("cantSplit", rules["prevent_row_split"]),
                                  ("tblHeader", row_index == 0 and rules["repeat_header_row"])):
                flag = row._tr.find("./" + qn("w:trPr") + "/" + qn(f"w:{tag}"))
                actual = flag is not None and flag.get(qn("w:val"), "1") not in {"0", "false", "off"}
                if actual != expected:
                    errors.append(f"{label} {tag} 不符合 profile")
            if rules["remove_row_tblPrEx_borders"] and row._tr.findall(
                "./" + qn("w:tblPrEx") + "/" + qn("w:tblBorders")
            ):
                errors.append(f"{label} 残留 tblPrEx/tblBorders")
            for column, cell in enumerate(_physical_cells(table, row), start=1):
                cell_label = f"{label} 列 {column}"
                text_rules = dict(profile["typography"]["table_text"], bold=(row_index == 0))
                if cell.vertical_alignment != getattr(WD_CELL_VERTICAL_ALIGNMENT, text_rules["vertical_alignment"].upper()):
                    errors.append(f"{cell_label} vertical_alignment 不符合 profile")
                for paragraph in cell.paragraphs:
                    errors.extend(_validate_typography(paragraph, text_rules, profile["typography"], cell_label))
                properties = cell._tc.find(qn("w:tcPr"))
                if properties is None:
                    errors.append(f"{cell_label} 缺少 tcPr")
                    continue
                for side, expected in rules["cell_margins_twips"].items():
                    margin = properties.find("./" + qn("w:tcMar") + "/" + qn(f"w:{side}"))
                    if margin is None or margin.get(qn("w:w")) != str(expected) or margin.get(qn("w:type")) != "dxa":
                        errors.append(f"{cell_label} margin.{side} 不符合 profile")
                edges = {
                    "start": (rules["left_border"], None), "end": (rules["right_border"], None),
                    "insideH": (rules["inside_horizontal"], None), "insideV": (rules["inside_vertical"], None),
                    "top": (rules["inside_horizontal"], None), "bottom": (rules["inside_horizontal"], None),
                }
                if row_index == 0:
                    edges["top"] = ("single", rules["top_border_ooxml_size"])
                    edges["bottom"] = ("single", rules["header_bottom_border_ooxml_size"])
                if row_index == len(table.rows) - 1:
                    edges["bottom"] = ("single", rules["bottom_border_ooxml_size"])
                for side, (value, size) in edges.items():
                    edge = properties.find("./" + qn("w:tcBorders") + "/" + qn(f"w:{side}"))
                    if edge is None or edge.get(qn("w:val")) != value or (
                        size is not None and edge.get(qn("w:sz")) != str(size)
                    ):
                        errors.append(f"{cell_label} border.{side} 不符合 profile")
    return errors


def validate_docx_math(document, profile: dict[str, Any] | None = None) -> list[str]:
    """Check native equation font and display alignment at the shared format step."""
    profile = profile or load_profile()
    equations = profile["equations"]
    errors = []
    font = document.settings._element.find("./" + qn("m:mathPr") + "/" + qn("m:mathFont"))
    if font is None or font.get(qn("m:val")) != equations["math_font"]:
        errors.append("equations.math_font 不符合 profile")
    for index, run in enumerate(document.element.findall(".//" + qn("m:r")), start=1):
        fonts = run.find("./" + qn("w:rPr") + "/" + qn("w:rFonts"))
        if fonts is None or any(fonts.get(qn(f"w:{key}")) != equations["math_font"]
                                for key in ("ascii", "hAnsi", "eastAsia", "cs")):
            errors.append(f"公式 run {index} 字体不符合 profile")
    for index, block in enumerate(document.element.findall(".//" + qn("m:oMathPara")), start=1):
        alignment = block.find("./" + qn("m:oMathParaPr") + "/" + qn("m:jc"))
        if alignment is None or alignment.get(qn("m:val")) != equations["display_alignment"]:
            errors.append(f"展示公式 {index} display_alignment 不符合 profile")
    return errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_docx_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    manifest_path: str | Path | None = None,
    overwrite: bool = False,
    normalize_pandoc_headings: bool = False,
) -> Path:
    """Normalize one DOCX and optionally update its conversion manifest hash."""
    source = Path(input_path).resolve()
    target = Path(output_path).resolve() if output_path else source
    if not source.is_file() or source.suffix.casefold() != ".docx":
        raise FileNotFoundError(f"输入 DOCX 不存在: {source}")
    if target.exists() and target != source and not overwrite:
        raise FileExistsError(f"输出已存在: {target}")
    document = Document(str(source))
    profile = load_profile()
    apply_profile(
        document,
        profile,
        normalize_pandoc_headings=normalize_pandoc_headings,
    )
    normalize_docx_resources(document, profile)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".docx", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        document.save(str(temporary))
        saved = Document(temporary)
        errors = (validate_docx_resources(saved, profile) + validate_docx_layout(saved, profile)
                  + validate_docx_tables(saved, profile) + validate_docx_math(saved, profile))
        if errors:
            raise ValueError("DOCX 格式验证失败: " + "; ".join(errors))
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    if manifest_path is not None:
        manifest_file = Path(manifest_path).resolve()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["output_sha256"] = _sha256(target)
        record = {
            "tool": "shared.paper_format.normalize_docx_resources",
            "profile": str(PROFILE_PATH),
        }
        postprocessing = manifest.setdefault("postprocessing", [])
        if record not in postprocessing:
            postprocessing.append(record)
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize repository paper DOCX resources")
    parser.add_argument("input", help="input DOCX")
    parser.add_argument("--output", help="output DOCX; omit to normalize in place")
    parser.add_argument("--manifest", help="optional conversion manifest to update")
    parser.add_argument("--overwrite", action="store_true", help="allow replacing a different output file")
    parser.add_argument(
        "--normalize-pandoc-headings",
        action="store_true",
        help="normalize the known Pandoc title/heading hierarchy explicitly",
    )
    args = parser.parse_args(argv)
    target = normalize_docx_file(
        args.input,
        args.output,
        manifest_path=args.manifest,
        overwrite=args.overwrite,
        normalize_pandoc_headings=args.normalize_pandoc_headings,
    )
    print(target)
    return 0


def _set_cell_margins(cell, margins: dict[str, int]) -> None:
    properties = cell._tc.get_or_add_tcPr()
    container = properties.find(qn("w:tcMar"))
    if container is None:
        container = OxmlElement("w:tcMar")
        following_tags = {
            qn("w:textDirection"),
            qn("w:tcFitText"),
            qn("w:vAlign"),
            qn("w:hideMark"),
            qn("w:headers"),
            qn("w:cellIns"),
            qn("w:cellDel"),
            qn("w:cellMerge"),
            qn("w:tcPrChange"),
        }
        insertion_index = next(
            (index for index, child in enumerate(properties) if child.tag in following_tags),
            len(properties),
        )
        properties.insert(insertion_index, container)
    for name in ("top", "start", "bottom", "end"):
        node = container.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            container.append(node)
        node.set(qn("w:w"), str(margins[name]))
        node.set(qn("w:type"), "dxa")


def _set_cell_edge(cell, name: str, *, value: str, size: int = 0) -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        following_tags = {
            qn("w:shd"),
            qn("w:noWrap"),
            qn("w:tcMar"),
            qn("w:textDirection"),
            qn("w:tcFitText"),
            qn("w:vAlign"),
            qn("w:hideMark"),
            qn("w:headers"),
            qn("w:cellIns"),
            qn("w:cellDel"),
            qn("w:cellMerge"),
            qn("w:tcPrChange"),
        }
        insertion_index = next(
            (index for index, child in enumerate(properties) if child.tag in following_tags),
            len(properties),
        )
        properties.insert(insertion_index, borders)
    edge = borders.find(qn(f"w:{name}"))
    if edge is None:
        edge = OxmlElement(f"w:{name}")
        borders.append(edge)
    edge.set(qn("w:val"), value)
    if value == "single":
        edge.set(qn("w:sz"), str(size))
        edge.set(qn("w:color"), "000000")


def _format_tables(document, profile: dict[str, Any]) -> None:
    table_profile = profile["tables"]
    text_profile = dict(profile["typography"]["table_text"])
    text_profile["latin_font"] = profile["typography"]["latin_font"]
    text_profile["font_color_hex"] = profile["typography"]["font_color_hex"]
    text_profile["snap_to_grid"] = profile["paragraphs"]["snap_to_document_grid"]
    for table in document.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for row_index, row in enumerate(table.rows):
            if table_profile["remove_row_tblPrEx_borders"]:
                for borders in row._tr.findall("./" + qn("w:tblPrEx") + "/" + qn("w:tblBorders")):
                    borders.getparent().remove(borders)
            row_properties = row._tr.get_or_add_trPr()
            for tag, enabled in (("cantSplit", table_profile["prevent_row_split"]),
                                 ("tblHeader", row_index == 0 and table_profile["repeat_header_row"])):
                flag = row_properties.find(qn(f"w:{tag}"))
                if flag is None:
                    flag = OxmlElement(f"w:{tag}")
                    row_properties.append(flag)
                flag.set(qn("w:val"), "1" if enabled else "0")
            for cell in _physical_cells(table, row):
                cell.vertical_alignment = getattr(WD_CELL_VERTICAL_ALIGNMENT, text_profile["vertical_alignment"].upper())
                _set_cell_margins(cell, table_profile["cell_margins_twips"])
                for edge_name, key in (("top", "inside_horizontal"), ("bottom", "inside_horizontal"),
                                       ("start", "left_border"), ("end", "right_border"),
                                       ("insideH", "inside_horizontal"), ("insideV", "inside_vertical")):
                    _set_cell_edge(cell, edge_name, value=table_profile[key])
                if row_index == 0:
                    _set_cell_edge(
                        cell,
                        "top",
                        value="single",
                        size=table_profile["top_border_ooxml_size"],
                    )
                    _set_cell_edge(
                        cell,
                        "bottom",
                        value="single",
                        size=table_profile["header_bottom_border_ooxml_size"],
                    )
                if row_index == len(table.rows) - 1:
                    _set_cell_edge(
                        cell,
                        "bottom",
                        value="single",
                        size=table_profile["bottom_border_ooxml_size"],
                    )
                for paragraph in cell.paragraphs:
                    paragraph.style = document.styles["Table Text"]
                    _remove_numbering(paragraph._p)
                    paragraph.paragraph_format.first_line_indent = Pt(0)
                    _apply_paragraph_format(paragraph, text_profile)
                    for run in _text_runs(paragraph):
                        _set_run_format(run, text_profile, bold=(row_index == 0))


def apply_profile(
    document,
    profile: dict[str, Any] | None = None,
    *,
    normalize_pandoc_headings: bool = False,
) -> None:
    """Apply generic profile rules in place; project-specific layout comes later."""
    profile = profile or load_profile()
    if normalize_pandoc_headings:
        normalize_pandoc_heading_hierarchy(document)
    page = profile["page"]
    typography = profile["typography"]
    math_font = profile["equations"]["math_font"]
    replaced_theme_fonts = _sync_theme_fonts(
        document,
        latin_font=typography["latin_font"],
        east_asia_font=typography["body"]["east_asia_font"],
    )
    _sync_font_table(
        document,
        removed_fonts=replaced_theme_fonts,
        required_fonts={
            typography["latin_font"],
            typography["body"]["east_asia_font"],
            typography["heading_level_1"]["east_asia_font"],
            math_font,
        },
    )
    _sync_style_resources(document, profile)
    _sync_doc_defaults(document, profile)
    page_number_typography = dict(
        typography["page_number"],
        latin_font=typography["latin_font"],
        font_color_hex=typography["font_color_hex"],
    )
    for section in document.sections:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Twips(page["width_twips"])
        section.page_height = Twips(page["height_twips"])
        section.top_margin = Twips(page["margins_twips"]["top"])
        section.bottom_margin = Twips(page["margins_twips"]["bottom"])
        section.left_margin = Twips(page["margins_twips"]["left"])
        section.right_margin = Twips(page["margins_twips"]["right"])
        section.header_distance = Twips(page["header_distance_twips"])
        section.footer_distance = Twips(page["footer_distance_twips"])
        section.different_first_page_header_footer = page["different_first_page"]
        _set_page_gutter(section)
        _set_document_grid(section, page["document_grid"])
        _set_page_field(section.footer, page_number_typography)
        if page["different_first_page"]:
            _set_page_field(section.first_page_footer, page_number_typography)

    _set_math_font(document, math_font)
    _set_math_run_font(document, math_font)
    for block in document.element.findall(".//" + qn("m:oMathPara")):
        properties = block.find(qn("m:oMathParaPr"))
        if properties is None:
            properties = OxmlElement("m:oMathParaPr")
            block.insert(0, properties)
        alignment = properties.find(qn("m:jc"))
        if alignment is None:
            alignment = OxmlElement("m:jc")
            properties.append(alignment)
        alignment.set(qn("m:val"), profile["equations"]["display_alignment"])
    common_typography = {
        "latin_font": typography["latin_font"],
        "font_color_hex": typography["font_color_hex"],
        "snap_to_grid": profile["paragraphs"]["snap_to_document_grid"],
    }
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            _remove_numbering(document.styles[style_name].element)
        except KeyError:
            pass

    in_short_appendix = False
    abstract_heading_seen = False
    first_body_heading_started = False
    body_profile = dict(typography["body"], **common_typography)
    for index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        if index == 0 and style_name == "Title":
            _remove_numbering(paragraph._p)
            paragraph.paragraph_format.first_line_indent = Pt(0)
            title_profile = dict(typography["title"], **common_typography)
            _apply_paragraph_format(paragraph, title_profile)
            continue
        if style_name.startswith("Heading"):
            _remove_numbering(paragraph._p)
            paragraph.paragraph_format.first_line_indent = Pt(0)
            key = (
                "heading_level_1"
                if style_name == "Heading 1"
                else "heading_level_2_and_3"
            )
            heading_profile = dict(typography[key], **common_typography)
            _apply_paragraph_format(paragraph, heading_profile)
            compact_text = re.sub(r"\s+", "", text)
            if compact_text == "摘要":
                abstract_heading_seen = True
            elif (
                abstract_heading_seen
                and not first_body_heading_started
                and key == "heading_level_1"
            ):
                paragraph.paragraph_format.page_break_before = bool(
                    profile["pagination"]["first_body_heading_starts_new_page"]
                )
                first_body_heading_started = True
            if text.startswith("附录"):
                in_short_appendix = True
            continue
        if paragraph._p.findall(".//" + qn("w:drawing")):
            _set_paragraph_snap_to_grid(
                paragraph,
                profile["paragraphs"]["snap_to_document_grid"],
            )
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _set_character_indent(paragraph._p.get_or_add_pPr(), {})
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.keep_with_next = True
            continue
        caption_kind = _caption_kind(paragraph)
        if caption_kind:
            caption_profile = dict(typography["caption"], **common_typography)
            paragraph.style = document.styles["Table Caption" if caption_kind == "表" else "Image Caption"]
            if "label_separator" in caption_profile:
                _normalize_caption_separator(paragraph, caption_profile["label_separator"])
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.keep_with_next = caption_kind == "表"
            paragraph.paragraph_format.keep_together = True
            _apply_paragraph_format(paragraph, caption_profile)
            continue
        if re.match(r"^\[\d+\]", text):
            reference_profile = dict(
                typography["reference_and_short_appendix"],
                **common_typography,
            )
            paragraph.paragraph_format.left_indent = Pt(reference_profile["hanging_indent_pt"])
            paragraph.paragraph_format.first_line_indent = Pt(-reference_profile["hanging_indent_pt"])
            _apply_paragraph_format(paragraph, reference_profile)
            continue
        if not text and paragraph._p.findall(".//" + qn("m:oMath")):
            _apply_paragraph_format(paragraph, body_profile)
            paragraph.alignment = _ALIGNMENTS[profile["equations"]["display_alignment"]]
            paragraph.paragraph_format.first_line_indent = Pt(0)
            continue
        if in_short_appendix:
            appendix_profile = dict(
                typography["reference_and_short_appendix"],
                **common_typography,
            )
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _apply_paragraph_format(paragraph, appendix_profile)
            continue
        _apply_paragraph_format(paragraph, body_profile)
        if paragraph._p.get_or_add_pPr().find(qn("w:numPr")) is not None:
            paragraph.paragraph_format.first_line_indent = None
        if text.startswith("关键词"):
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _set_character_indent(paragraph._p.get_or_add_pPr(), {"first_line_indent_chars": 0})

    _format_tables(document, profile)
    errors = (validate_docx_layout(document, profile) + validate_docx_tables(document, profile)
              + validate_docx_math(document, profile))
    if errors:
        raise ValueError("DOCX profile application failed: " + "; ".join(errors))


if __name__ == "__main__":
    raise SystemExit(main())
