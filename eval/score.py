#!/usr/bin/env python3
"""Score one code review against an eval case.

    python3 eval/score.py <case-id> <review-file> [--json]

Defect cases: a planted defect counts as FOUND when one finding (a table row, bullet, paragraph or JSON finding)
names one of its files and one of its keywords. Clean cases: every blocker/major finding is a FALSE ALARM.
Decoys: flagged when a blocker/major finding names the decoy's file and keyword.
Keyword matching is deliberately simple; read the review too, and correct the score by hand when it is wrong.
"""
import json, os, re, sys

EVAL = os.path.dirname(os.path.abspath(__file__))
SEV = re.compile(r"\b(blocker|major|minor)\b", re.I)


def units(text):
    """Finding-sized pieces: table rows, list items, paragraphs, JSON findings."""
    out = []
    try:  # a judge JSON reply anywhere in the text
        for m in re.finditer(r"\{[^{}]*\"severity\"[^{}]*\}", text, re.S):
            out.append(m.group(0))
    except re.error:
        pass
    para = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 3:
            out.append(s)
            continue
        if re.match(r"^([-*]|\d+\.)\s", s):
            if para:
                out.append(" ".join(para))
            para = [s]
            continue
        if not s:
            if para:
                out.append(" ".join(para))
            para = []
        else:
            para.append(s)
    if para:
        out.append(" ".join(para))
    return out


def severity(u):
    """The severity a finding is labelled with — only where a finding states it, not any mention of the word."""
    m = re.search(r'"severity"\s*:\s*"(blocker|major|minor)"', u, re.I)
    if m:
        return m.group(1).lower()
    if u.startswith("|"):
        cells = [c.strip().strip("*`[]").lower() for c in u.strip("|").split("|")]
        for c in cells[:2]:
            if c in ("blocker", "major", "minor"):
                return c
        return None
    m = re.match(r"^(?:[-*]|\d+\.)?\s*(?:\*\*|\[|`)?\s*(blocker|major|minor)\b", u, re.I)
    return m.group(1).lower() if m else None


def mentions(u, files, keywords):
    """True when the finding names one of the files (with or without the extension) and one keyword."""
    low = u.lower()
    names = {f.lower() for f in files} | {f.lower().rsplit(".", 1)[0] for f in files}
    return any(n in low for n in names) and any(k.lower() in low for k in keywords)


def verdict(text):
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    for v in ("FAIL", "PASS", "STOPPED", "UNVERIFIED"):
        if v in first.upper():
            return v
    m = re.search(r"\b(PASS|FAIL)\b", text)
    return m.group(1) if m else "?"


def score(case_id, text):
    case = json.load(open(os.path.join(EVAL, "cases", case_id, "case.json")))
    us = units(text)
    serious = [u for u in us if severity(u) in ("blocker", "major")]
    result = {"case": case_id, "kind": case["kind"], "verdict": verdict(text),
              "findings_blocker_major": len(serious),
              "findings_minor": len([u for u in us if severity(u) == "minor"])}
    if case["kind"] == "defects":
        ans = json.load(open(os.path.join(EVAL, "cases", case_id, "answer.json")))
        found = []
        for d in ans["defects"]:
            hit = next((u for u in us if mentions(u, d["files"], d["keywords"])), None)
            found.append({"id": d["id"], "found": hit is not None, "desc": d["desc"]})
        result["defects"] = found
        result["found"] = sum(f["found"] for f in found)
        result["planted"] = len(found)
        result["decoys_flagged"] = sum(
            1 for dc in ans.get("decoys", []) if any(mentions(u, dc["files"], dc["keywords"]) for u in serious))
    else:
        result["false_alarms"] = len(serious)
    return result


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    r = score(sys.argv[1], open(sys.argv[2], encoding="utf-8", errors="replace").read())
    if "--json" in sys.argv:
        print(json.dumps(r))
        return
    print(f"case {r['case']} ({r['kind']}) — verdict {r['verdict']}")
    if r["kind"] == "defects":
        for f in r["defects"]:
            print(f"  {'FOUND ' if f['found'] else 'MISSED'} {f['id']}: {f['desc']}")
        print(f"  {r['found']}/{r['planted']} planted defects found; decoys flagged: {r['decoys_flagged']};"
              f" blocker/major findings: {r['findings_blocker_major']}")
    else:
        print(f"  false alarms (blocker/major on a clean change): {r['false_alarms']};"
              f" minor findings: {r['findings_minor']}; expected verdict PASS")


if __name__ == "__main__":
    main()
