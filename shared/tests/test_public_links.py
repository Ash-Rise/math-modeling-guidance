from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")

def test_local_markdown_links_resolve() -> None:
    broken = []
    for document in ROOT.rglob("*.md"):
        if any(part.startswith(".") for part in document.relative_to(ROOT).parts):
            continue
        for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (document.parent / target).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not broken, "Broken local Markdown links:\n" + "\n".join(broken)
