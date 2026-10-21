"""PM benchmark — the PRD (pm-eval-loop Step B). Judge keeps: problem/gap specificity, business value, domain fit."""
import re

from common import JIRA_KEY, bullets, placeholders, section, section18_hits

ROLES = {"trader", "ops", "operations", "admin", "system"}


def run(r, ctx):
    t = ctx.text
    secs = {"PROBLEM": ("problem statement", "PROBLEM"), "SOLUTION SUMMARY": ("proposed solution", "SOLUTION SUMMARY"),
            "SUCCESS CRITERIA": ("SUCCESS CRITERIA",), "OUT OF SCOPE": ("OUT OF SCOPE",),
            "DEPENDENCIES": ("DEPENDENCIES",), "BACKLOG ORDER": ("backlog prioritization", "BACKLOG ORDER")}
    body = {k: section(t, *v) for k, v in secs.items()}
    missing = [k for k, v in body.items() if not v.strip()]
    r.add("PM-1", "All 6 PRD sections present", not missing, f"missing: {', '.join(missing)}" if missing else "6/6")

    m = re.search(r"Who has this problem\s*:\s*(.+)", t, re.I)
    owner = (m.group(1).strip().lower() if m else "")
    r.add("PM-2", "Problem owner is a named role", any(x in re.findall(r"[a-z]+", owner) for x in ROLES),
          f"owner: '{owner or '(not found)'}' — allowed: {', '.join(sorted(ROLES))}")
    for label, cid in (("What they cannot do today", "PM-3"), ("Business impact if unsolved", "PM-4")):
        m = re.search(label + r"\s*:\s*(.+)", t, re.I)
        val = m.group(1).strip() if m else ""
        r.add(cid, f"'{label}' stated", len(val.split()) >= 4, f"'{val[:80]}'" if val else "not found")

    crit = bullets(body["SUCCESS CRITERIA"])
    verifiable = [c for c in crit if re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\b|/api/|\b[1-5]\d\d\b|\d|visible|display|shows?|renders?", c, re.I)]
    r.add("PM-5", ">= 2 success criteria, each verifiable", len(crit) >= 2 and len(verifiable) == len(crit),
          f"{len(crit)} criteria, {len(verifiable)} with a verifiable marker (HTTP call, status, number, visible UI)",
          [c for c in crit if c not in verifiable])

    dep = body["DEPENDENCIES"]
    has_b = re.search(r"Blocked by\s*:\s*(\S.*)", dep, re.I)
    has_e = re.search(r"Enables\s*:\s*(\S.*)", dep, re.I)
    bad = [v.group(1) for v in (has_b, has_e) if v and not (JIRA_KEY.search(v.group(1)) or re.search(r"\bnone\b", v.group(1), re.I))]
    r.add("PM-6", "Dependencies: Blocked by + Enables, each a ticket key or None", bool(has_b and has_e) and not bad,
          "missing line" if not (has_b and has_e) else (f"not a key/None: {bad}" if bad else "ok"))

    back = body["BACKLOG ORDER"]
    prio = "\n".join(l for l in back.splitlines() if re.match(r"\s*P[123]\b", l.strip()))
    hits = section18_hits(prio, ctx.repo.out_of_scope()) if ctx.repo.path else []
    if ctx.repo.path:
        r.add("PM-7", "No CLAUDE.md §18 (out of scope) item in P1/P2/P3", not hits, f"found: {hits}" if hits else "none")
    else:
        r.skip("PM-7", "No CLAUDE.md §18 item in P1/P2/P3", "no --repo given")
    p1 = "\n".join(l for l in back.splitlines() if l.strip().startswith("P1"))
    pts = [int(x) for x in re.findall(r"(\d+)\s*(?:pts?|points?|sp)\b", p1, re.I)]
    if pts:
        r.add("PM-8", "P1 story points <= 20", sum(pts) <= 20, f"P1 total {sum(pts)} (from {pts})")
    else:
        r.add("PM-8", "P1 story points <= 20", False, "no point estimates on the P1 line (write e.g. '(3 pts)')", warn=True)

    ph = placeholders(t)
    r.add("PM-9", "No template placeholders / TBD / TODO left", not ph, f"{len(ph)} found", ph)

    svcs = sorted(n for n in ctx.repo.services() if re.search(r"\b" + re.escape(n) + r"\b", body["SOLUTION SUMMARY"]))
    if ctx.repo.path:
        r.add("PM-10", "Solution names at most one owning service", len(svcs) <= 1,
              f"services named in the solution: {svcs or 'none'}", warn=True)
