"""SM benchmark — recomputes every flag in the standup report from the sprint data, so the report cannot drift
from the facts. Replaces the in-agent "report completeness" self-check.

Input: --facts .plumbline/run/review/sprint-facts.json, the RAW JIRA data saved by the SM originator in Phase 0:
  {"today": "YYYY-MM-DD", "previous_done": 7, "issues": {"SCRUM-1": {"status": "In Progress", "assignee": "x"|null,
   "updated": "YYYY-MM-DD", "points": 3, "has_ac": true, "blocked_by": ["SCRUM-0"], "pr": 42}}}
Artifact: the standup report markdown. Checks marked `supplied` depend on that JIRA export.
Judge keeps: is the narrative honest and useful, are risks prioritised sensibly."""
import json
import re
from datetime import date

from common import UsageError, gh, read, section

SECTIONS = ["Done", "In Review", "In Progress", "Blocked", "At Risk", "Velocity"]


def keys_in(text):
    return set(re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", text))


def subjects(text):
    """Tickets a section LISTS: every key on a bullet line before the first ' — ' / ' - ' / '(' explanation,
    so 'SCRUM-43 — blocked by SCRUM-42' lists SCRUM-43 only."""
    out = set()
    for l in text.splitlines():
        if re.match(r"\s*(?:[-*+]|\d+[.)])\s+", l):
            head = re.split(r"\s[—–-]\s|\(|:", re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", l), 1)[0]
            out |= keys_in(head)
    return out


def run(r, ctx):
    t = ctx.text
    miss = [s for s in SECTIONS if not section(t, s).strip()]
    r.add("SM-1", "Report has all 6 sections", not miss, f"missing: {miss}" if miss else "6/6")
    if not ctx.facts:
        raise UsageError("pass --facts with the raw JIRA export from Phase 0")
    f = ctx.facts
    iss = f.get("issues")
    if not isinstance(iss, dict) or any(not isinstance(v, dict) or "status" not in v for v in iss.values()):
        raise UsageError("facts file needs issues: {KEY: {status, ...}} for every ticket")
    today = date.fromisoformat(f.get("today", date.today().isoformat()))
    age = lambda k: (today - date.fromisoformat(iss[k]["updated"][:10])).days if iss[k].get("updated") else 0
    exp = {
        "At Risk": {k for k, v in iss.items() if v["status"] == "In Progress" and age(k) > 2},
        "Blocked": {k for k, v in iss.items() if any(iss.get(b, {}).get("status") != "Done" for b in v.get("blocked_by", []))},
        "Done": {k for k, v in iss.items() if v["status"] == "Done"},
        "In Review": {k for k, v in iss.items() if v["status"] == "In Review"},
    }
    unassigned = {k for k, v in iss.items() if v["status"] == "To Do" and not v.get("assignee")}
    no_ac = {k for k, v in iss.items() if not v.get("has_ac", True)}
    review_stuck = {k for k, v in iss.items() if v["status"] == "In Review" and age(k) > 1}
    allowed_extra = {"At Risk": unassigned | no_ac | review_stuck}
    for i, (sec, want) in enumerate(exp.items(), 2):
        got = subjects(section(t, sec))
        extra = got - want - allowed_extra.get(sec, set())
        r.add(f"SM-{i}", f"'{sec}' lists exactly the tickets the data implies", want <= got and not extra,
              f"expected {sorted(want)}, report {sorted(got)}", [f"missing {k}" for k in sorted(want - got)]
              + [f"extra {k}" for k in sorted(extra)], source="supplied")
    rep_all = keys_in(t)
    r.add("SM-6", "Unassigned To-Do and no-AC tickets are flagged", (unassigned | no_ac) <= rep_all,
          f"not mentioned: {sorted((unassigned | no_ac) - rep_all)}", source="supplied")
    done_pts = sum(v.get("points") or 0 for v in iss.values() if v["status"] == "Done")
    vel = section(t, "Velocity")
    nums = [int(x) for x in re.findall(r"\b\d+\b", vel)]
    ok = len(exp["Done"]) in nums and (not done_pts or done_pts in nums) and (f.get("previous_done") is None or f["previous_done"] in nums)
    r.add("SM-7", "Velocity numbers match the data", ok,
          f"expected done={len(exp['Done'])} tickets / {done_pts} pts, previous={f.get('previous_done')}; report numbers {nums[:8]}",
          source="supplied")
    # DoD for In Review tickets: computed from GitHub, not from JIRA or the report
    dod_bad, checked = [], 0
    for k in sorted(exp["In Review"]):
        pr = iss[k].get("pr")
        if not pr:
            dod_bad.append(f"{k}: no PR linked")
            continue
        info = gh("pr", "view", str(pr), "--json", "reviewDecision,headRefOid,mergedAt")
        if info is None:
            continue
        checked += 1
        st = gh("api", f"repos/{{owner}}/{{repo}}/commits/{info['headRefOid']}/status", "--jq",
                '[.statuses[]|select(.context=="plumbline/code-review")|.state][0] // "missing"')
        if info.get("reviewDecision") != "APPROVED" or st not in ("success",):
            dod_bad.append(f"{k} (PR #{pr}): reviewDecision={info.get('reviewDecision')}, plumbline/code-review={st}")
    if exp["In Review"] and not checked:
        r.skip("SM-8", "DoD for In Review tickets (human approval + plumbline/code-review on head)", "gh unavailable")
    else:
        lines = t.splitlines()
        on_line = lambda k: any(k in l and re.search(r"\bDoD\b|Definition of Done", l, re.I) for l in lines)
        unflagged = [b for b in dod_bad if not on_line(b.split()[0])]
        r.add("SM-8", "DoD failures are reported for In Review tickets", not unflagged,
              f"{checked} checked on GitHub, {len(dod_bad)} not done", dod_bad)
