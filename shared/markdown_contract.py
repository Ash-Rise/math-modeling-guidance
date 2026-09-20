"""Check Markdown math delimiters from the paper profile, without rewriting sources.

This is a delimiter check, not a Markdown/TeX parser or a general linter. Code,
comments, link destinations and numeric superscript citations are literal text.
Only complete math spans are checked; ambiguous/unmatched punctuation is left
alone. Repository enforcement targets the canonical editable paper sources,
including new, non-ignored papers, rather than every Markdown document.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

import yaml


PROFILE_PATH = Path(__file__).parent / "templates" / "personal-paper-profile.yaml"
# Recognized source syntax, not the permitted formatting: that comes from YAML.
MATH_PAIRS = {
    "inline": (("$", "$"), (r"\(", r"\)")),
    "display": (("$$", "$$"), (r"\[", r"\]")),
}
FENCE = re.compile(r"^[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})(.*)$")
QUOTE = re.compile(r"^(?: {0,3}>[ \t]?)+")
REFERENCE = re.compile(r"^ {0,3}\[(?!\^)[^]\n]+\]:[ \t]*\S+")
CITATION = re.compile(r"\^\\\[\d+(?:[ ,，;；–—-]+\d+)*\\\]\^")
RAW_CODE = re.compile(r"<(pre|code)\b[^>]*>.*?</\1\s*>", re.I | re.S)


@dataclass(frozen=True)
class Violation:
    line: int
    column: int
    found: str
    expected: str

    def __str__(self) -> str:
        return f"{self.line}:{self.column}: math delimiter {self.found!r}; profile requires {self.expected!r}"


def _blank(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def _escaped(text: str, index: int) -> bool:
    start = index
    while start > 0 and text[start - 1] == "\\":
        start -= 1
    return (index - start) % 2 == 1


def _prose(text: str) -> str:
    """Mask literal regions while preserving offsets for file/line diagnostics."""
    lines = []
    fence = None
    fence_quotes = 0
    indented = False
    previous_blank = True
    for line in text.splitlines(keepends=True):
        quote = QUOTE.match(line)
        quote_count = quote[0].count(">") if quote else 0
        if fence and quote_count < fence_quotes:
            fence = None  # An unclosed fence ends with its containing blockquote.
        content = QUOTE.sub("", line)
        match = FENCE.match(content.rstrip("\r\n"))
        literal = False
        if fence:
            literal = True
            inner = re.sub(r"^(?: {0,3}>[ \t]?){" + str(fence_quotes) + "}", "", line)
            closer = r"[ \t]*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*"
            if re.fullmatch(closer, inner.rstrip("\r\n")):
                fence = None
        elif match and not (match[1][0] == "`" and "`" in match[2]):
            fence = match[1]
            fence_quotes = quote_count
            literal = True
        elif REFERENCE.match(content):
            literal = True
        elif content.startswith(("    ", "\t")) and (previous_blank or indented):
            indented = literal = True
        elif content.strip():
            indented = False
        lines.append(_blank(line) if literal else line)
        previous_blank = not content.strip()
    text = "".join(lines)
    masked = list(text)
    index = 0
    while index < len(text):
        end = index
        if text[index] == "`" and not _escaped(text, index):
            run = re.match(r"`+", text[index:])[0]
            # An unmatched run is ordinary text, not an excuse to hide the rest.
            boundary = re.search(r"\n[ \t]*\n", text[index + len(run):])
            limit = index + len(run) + boundary.start() if boundary else len(text)
            closer = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", text[index + len(run):limit])
            if closer:
                end = index + len(run) + closer.end()
            else:
                index += len(run)
                continue
        elif text.startswith("<!--", index):
            closer = text.find("-->", index + 4)
            end = len(text) if closer < 0 else closer + 3
        elif text[index] == "<":
            raw = RAW_CODE.match(text, index)
            if raw:
                end = raw.end()
            else:
                link = re.match(r"<(?:https?://|mailto:)[^<>\n]*>", text[index:])
                if link:
                    end = index + link.end()
        elif text[index] == "^":
            citation = CITATION.match(text, index)
            if citation:
                end = citation.end()
        elif text.startswith("](", index) and not _escaped(text, index):
            # Balanced destinations, including escaped parentheses; keep labels.
            cursor, depth = index + 2, 1
            while cursor < len(text) and depth and text[cursor] != "\n":
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == "(":
                    depth += 1
                elif text[cursor] == ")":
                    depth -= 1
                cursor += 1
            if depth == 0:
                end = cursor
        if end > index:
            masked[index:end] = _blank(text[index:end])
            index = end
        else:
            index += 1
    return "".join(masked)


def check_markdown(source: str, profile: dict) -> list[Violation]:
    target = profile["markdown"]["source_target"]
    if target["dialect"] != "pandoc_markdown":
        raise ValueError("Markdown checker only supports the profile's pandoc_markdown dialect")
    allowed = {}
    for kind, pairs in MATH_PAIRS.items():
        pattern = target[f"{kind}_math_delimiter"]
        pair = tuple(pattern.split("..."))
        if pair not in pairs:
            raise ValueError(f"Unsupported {kind}_math_delimiter in profile: {pattern!r}")
        allowed[kind] = pair

    text = _prose(source)
    violations = []
    index = 0
    tokens = [(kind, pair) for kind, pairs in MATH_PAIRS.items() for pair in pairs]
    tokens.sort(key=lambda item: len(item[1][0]), reverse=True)
    while index < len(text):
        if _escaped(text, index):
            index += 1
            continue
        token = next((item for item in tokens if text.startswith(item[1][0], index)), None)
        if token is None:
            index += 1
            continue
        kind, (opener, closer) = token
        start = index + len(opener)
        end = text.find(closer, start)
        # Pandoc dollar math must not consume currency or whitespace delimiters.
        if opener == "$" and (start == len(text) or text[start].isspace()):
            index = start
            continue
        while end >= 0 and (_escaped(text, end) or (
            closer == "$" and (text[end - 1].isspace() or text[end + 1:end + 2].isdigit()
                                or text[end - 1:end] == "$" or text[end + 1:end + 2] == "$")
        )):
            end = text.find(closer, end + len(closer))
        if end < 0 or (kind == "inline" and re.search(r"\n[ \t]*\n", text[start:end])):
            index = start
            continue
        if (opener, closer) != allowed[kind]:
            violations.append(Violation(
                source.count("\n", 0, index) + 1,
                index - source.rfind("\n", 0, index),
                opener + "..." + closer,
                "...".join(allowed[kind]),
            ))
        index = end + len(closer)
    return violations


def check_repository(root: Path, *, include_untracked: bool = True) -> list[str]:
    """Check projects/<collection>/solutions/<solution>/paper/paper.md sources.

    This is the repository's publication-source interface consumed by its DOCX
    workflows. Statements, navigation and analysis/decision records do not acquire
    that role merely by using Markdown. Other consumers can call check_markdown
    explicitly when they actually adopt this profile.
    """
    arguments = ["git", "ls-files", "-z", "--cached"]
    if include_untracked:
        arguments += ["--others", "--exclude-standard"]
    output = subprocess.run(arguments, cwd=root, check=True, stdout=subprocess.PIPE).stdout
    paths = sorted(set(output.decode("utf-8").split("\0")) - {""})
    with (root / "shared/templates/personal-paper-profile.yaml").open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    errors = []
    for name in paths:
        path = root / name
        if Path(name).match("projects/*/solutions/*/paper/paper.md") and len(Path(name).parts) == 6 and path.is_file():
            errors.extend(f"{name}:{error}" for error in check_markdown(path.read_text(encoding="utf-8"), profile))
    return errors
