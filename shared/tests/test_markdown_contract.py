"""Delimiter regressions plus the source check run by the existing shared suite."""

from pathlib import Path
import subprocess

import pytest
import yaml

from shared.markdown_contract import PROFILE_PATH, check_markdown, check_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def profile():
    return yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))


def test_radio_interference_report_regression(profile):
    # Actual failing notation from the 2026 B analysis, including a multiline block.
    source = r"""记 \(u_-=u(\theta-\varepsilon)\)。一次示向观测给出

\[
\operatorname{cross}(u_-,g-s)\ge0,\qquad
\operatorname{cross}(u_+,g-s)\le0.
\]
"""
    errors = check_markdown(source, profile)
    assert [(e.line, e.column, e.found, e.expected) for e in errors] == [
        (1, 3, r"\(...\)", "$...$"),
        (3, 1, r"\[...\]", "$$...$$"),
    ]
    fixed = source.replace(r"\(", "$").replace(r"\)", "$").replace(r"\[", "$$").replace(r"\]", "$$")
    assert check_markdown(fixed, profile) == []


@pytest.mark.parametrize("source", [
    r"正文 \(x\)，以及 \[y\]。",
    "> 正文 \\(x\\)\n>\n> \\[\n> y\n> \\]",
    "- 正文 \\(x\\)\n\n  \\[y\\]",
])
def test_prose_in_paragraphs_quotes_and_lists_is_checked(source, profile):
    assert len(check_markdown(source, profile)) == 2


@pytest.mark.parametrize("literal", [
    r"`\(x\)` 和 `\[y\]`",
    r"``示例 ` \(x\) 和 \[y\]``",
    "`多行代码\n\\(x\\)`",
    "```tex\n\\(x\\)\n\\[y\\]\n```",
    "~~~~latex\n\\(x\\)\n~~~\n\\[y\\]\n~~~~",
    "````markdown\n```tex\n\\(x\\)\n```\n\\[y\\]\n````",
    "```markdown\n- ```\n\\(x\\)\n> ```\n\\[y\\]\n```",
    "> ```tex\n> \\(x\\)\n> \\[y\\]\n> ```",
    "- ```tex\n  \\(x\\)\n  \\[y\\]\n  ```",
    "示例：\n\n    \\(x\\)\n    \\[y\\]",
    "\t\\(x\\)\n\t\\[y\\]",
    r"<!-- 草稿 \(x\)，\[y\] -->",
    r"<pre>\(x\) 和 \[y\]</pre>",
    r"<code>\(x\) 和 \[y\]</code>",
    r"[资料](figures/\(x\).svg) ![](figures/\[y\].svg)",
    r"[资料]: figures/\(x\).svg",
    r"<https://example.org/\(x\)>",
    r"参考文献^\[1\]^ 和 ^\[2,3–5\]^。",
    r"显式转义 \\(x\\) 和 \\[y\\]。",
])
def test_literal_regions_do_not_hide_following_prose(literal, profile):
    assert check_markdown(literal, profile) == []
    source = literal + "\n\n正文 \\(z\\)。"
    errors = check_markdown(source, profile)
    assert len(errors) == 1
    assert errors[0].line == source.count("\n") + 1


def test_unmatched_backticks_do_not_hide_math(profile):
    assert len(check_markdown(r"未闭合 ` 代码标记，公式 \(x\)。", profile)) == 1
    assert len(check_markdown("`第一段\n\n第二段 \\(x\\)。`", profile)) == 1
    assert len(check_markdown(r"转义 \` 不是代码标记，公式 \(x\)。", profile)) == 1


def test_link_labels_remain_visible(profile):
    assert len(check_markdown(r"[可见 \(x\)](figures/\(literal\).svg)", profile)) == 1
    assert len(check_markdown(r"[^1]: 脚注公式 \(x\)。", profile)) == 1


def test_unclosed_quoted_fence_does_not_hide_next_paragraph(profile):
    source = "> ```tex\n> \\(literal\\)\n\n正文 \\(x\\)。"
    errors = check_markdown(source, profile)
    assert len(errors) == 1
    assert errors[0].line == 4


def test_allowed_math_and_ordinary_punctuation(profile):
    assert check_markdown(r"$x_{i}+\alpha$，$$D(P)=\max_{a,b}\|v_a-v_b\|.$$", profile) == []
    assert check_markdown(r"价格 \$20 和 $30；括号 \( 没有配对。", profile) == []


def test_delimiters_are_taken_from_profile(profile):
    target = profile["markdown"]["source_target"]
    target["inline_math_delimiter"] = r"\(...\)"
    target["display_math_delimiter"] = r"\[...\]"
    assert check_markdown(r"\(x\) 和 \[y\]", profile) == []
    errors = check_markdown("$x$\n\n$$\ny\n$$", profile)
    assert [(e.found, e.expected) for e in errors] == [
        ("$...$", r"\(...\)"), ("$$...$$", r"\[...\]"),
    ]
    assert check_markdown("价格 $20 和 $30。", profile) == []


@pytest.mark.parametrize("key,value", [
    ("inline_math_delimiter", "unknown"),
    ("display_math_delimiter", "unknown"),
    ("dialect", "unknown"),
])
def test_unsupported_profile_contract_is_not_silently_ignored(key, value, profile):
    profile["markdown"]["source_target"][key] = value
    with pytest.raises(ValueError):
        check_markdown("正文", profile)


def test_repository_check_reads_changed_and_new_files_without_rewriting(tmp_path, profile):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    config = tmp_path / "shared/templates/personal-paper-profile.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(yaml.safe_dump(profile), encoding="utf-8")
    tracked = tmp_path / "projects/contest/solutions/problem-a/paper/paper.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("$x$", encoding="utf-8")
    # These sources have other owners; even statement formula notation is literal
    # evidence to preserve, not an implicit adoption of the paper profile.
    excluded = ["README.md", "AGENTS.md", "projects/contest/problem-statements/题面.md",
                "projects/contest/solutions/problem-a/decisions.md",
                "projects/contest/solutions/problem-a/analysis/problem-analysis.md",
                "projects/contest/solutions/problem-a/paper/README.md"]
    for name in excluded:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r"\(original notation\)", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    tracked.write_text(r"\(x\)", encoding="utf-8")
    new = tmp_path / "projects/contest/solutions/problem-b/paper/paper.md"
    new.parent.mkdir(parents=True)
    new.write_text(r"\[y\]", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("projects/ignored/\n", encoding="utf-8")
    ignored = tmp_path / "projects/ignored/solutions/problem-c/paper/paper.md"
    ignored.parent.mkdir(parents=True)
    ignored.write_text(r"\(ignored\)", encoding="utf-8")
    (tmp_path / "new-notes.md").write_text(r"\(untracked notes\)", encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.md")}

    errors = check_repository(tmp_path)
    assert {e.split(":", 1)[0] for e in errors} == {
        tracked.relative_to(tmp_path).as_posix(), new.relative_to(tmp_path).as_posix(),
    }
    assert len(check_repository(tmp_path, include_untracked=False)) == 1
    assert {p: p.read_bytes() for p in before} == before

    tracked.unlink()
    assert check_repository(tmp_path, include_untracked=False) == []


def test_repository_markdown_contract():
    errors = check_repository(REPOSITORY_ROOT)
    assert not errors, "Markdown source contract violations:\n" + "\n".join(errors)
