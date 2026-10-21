#!/usr/bin/env python3
"""One-off migration: merge the drifted Claude Code (.md) and Copilot (.prompt.md) agent files
into a single canonical spec per agent.

Hunk policy:
  - frontmatter / Target line / Copilot Runtime Conventions / Copilot setup  -> copilot-only block
  - "Tokens consumed" line, Claude settings.local.json setup                 -> claude-only block
  - attribution lines (Co-Authored-By / AI-Assisted)                          -> {{ai_attribution}}
  - everything else that differs (stale command names, hardcoded JAVA_HOME,
    missing write guards/templates)                                          -> take the Copilot side (shared)
Unclassified hunks are reported for manual review.
"""
import difflib
import re
import sys
from pathlib import Path

CLAUDE_ONLY_MARK = ("Tokens consumed",)
ATTR_RE = re.compile(r"^(\s*)(Co-Authored-By: Claude.*|AI-Assisted: GitHub Copilot \(Plumbline ([a-z-]+)\).*?)(\"?\)?\"?)$")


def classify(a_lines, b_lines):
    a, b = "".join(a_lines), "".join(b_lines)
    if not a.strip() and (b.startswith("---\nmode:") or "Copilot Runtime Conventions" in b or b.strip().startswith("Target: ${input")
                          or "- **Mode:** run in Copilot" in b):
        return "copilot"
    if not b.strip() and any(m in a for m in CLAUDE_ONLY_MARK):
        return "claude"
    if ("Co-Authored-By" in a and "AI-Assisted" in b):
        return "attribution"
    if "settings.local.json" in a or "Copilot asks for approval" in b or "Setup — Copilot" in b:
        return "setup"
    if "JAVA_HOME=" in a or re.search(r"/(ba|pm|qa|devops|architect|dev|sm)-agent\b", a) or not a.strip():
        return "shared-copilot"
    return "review"


def merge(claude: Path, copilot: Path):
    A = claude.read_text().splitlines(True)
    B = copilot.read_text().splitlines(True)
    out, review = [], []
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a, b = A[i1:i2], B[j1:j2]
        if tag == "equal":
            out += a
            continue
        kind = classify(a, b)
        if kind == "copilot":
            out += ["<!-- @copilot -->\n"] + b + ["<!-- @end -->\n"]
        elif kind == "claude":
            out += ["<!-- @claude -->\n"] + a + ["<!-- @end -->\n"]
        elif kind == "attribution":
            line = b[0]
            out.append(re.sub(r"AI-Assisted: GitHub Copilot \(Plumbline [a-z-]+\)", "{{ai_attribution}}", line))
            out += b[1:]
        elif kind == "setup":
            out += ["<!-- @claude -->\n"] + a + ["<!-- @end -->\n", "<!-- @copilot -->\n"] + b + ["<!-- @end -->\n"]
        elif kind == "shared-copilot":
            out += b
        else:
            review.append((claude.name, "".join(a)[:400], "".join(b)[:400]))
            out += b  # default to the more complete Copilot side, but report it
    text = "".join(out)
    text = re.sub(r"AI-Assisted: GitHub Copilot \(Plumbline [a-z-]+\)", "{{ai_attribution}}", text)
    return text, review


if __name__ == "__main__":
    cc, cp, dst = map(Path, sys.argv[1:4])
    dst.mkdir(parents=True, exist_ok=True)
    allrev = []
    for c in sorted(cp.glob("*.prompt.md")):
        name = c.name.replace(".prompt.md", "")
        cl = cc / f"{name}.md"
        if cl.exists():
            text, rev = merge(cl, c)
        else:
            text, rev = c.read_text(), []
        (dst / f"{name}.md").write_text(text)
        allrev += rev
    for name, a, b in allrev:
        print(f"=== REVIEW {name}\n--- claude:\n{a}\n--- copilot:\n{b}\n")
    print(f"{len(allrev)} hunks need review")
