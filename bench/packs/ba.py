"""BA benchmark — one story (ba-eval-loop Step B). Judge keeps: is the story the right slice, are the ACs the RIGHT ones."""
import re

from common import HTTP_LINE, JIRA_KEY, STATUS, bullets, ep_match, placeholders, section, section18_hits

ROLES = ("trader", "operations", "admin")


def run(r, ctx):
    t, repo = ctx.text, ctx.repo
    first = next((l.strip("# ").strip() for l in t.splitlines() if l.strip()), "")
    summ = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/api/v1/[\w\-/{}]+)\s+[—-]\s+\S", t)
    r.add("BA-1", "Summary: '{Verb} {METHOD} /api/v1/{resource} — {outcome}'", bool(summ),
          f"first line: '{first[:90]}'" if not summ else f"{summ.group(1)} {summ.group(2)}")

    us = re.search(r"As an?\s+(\w+).*?\n.*?I want\s+\S.*?\n.*?So that\s+\S", t, re.I | re.S)
    role_ok = bool(us) and us.group(1).lower() in ROLES
    r.add("BA-2", "User story 'As a <role> / I want / So that'", role_ok,
          f"role '{us.group(1)}' (allowed {', '.join(ROLES)})" if us else "not found")

    acs = bullets(section(t, "acceptance criteria"))
    bad, kinds = [], set()
    for a in acs:
        m, st = HTTP_LINE.search(a), STATUS.findall(a)
        if not (m and st):
            bad.append(a[:120])
        for s in st:
            kinds.add("2xx" if s.startswith("2") else ("404" if s == "404" else ("400/422" if s in ("400", "422") else s)))
    r.add("BA-3", "Every AC is curl-verifiable (METHOD + /api path + status code)", bool(acs) and not bad,
          f"{len(acs)} ACs, {len(bad)} without method+path+status", bad)
    need = {"2xx", "404", "400/422"} - kinds
    r.add("BA-4", "ACs cover happy path, 404 and 400/422", not need, f"missing: {sorted(need)}" if need else "covered", warn=True)

    pts = re.search(r"Story Points.*?(?:Estimate\s*:)?\s*\**(\d+)\**", t, re.I | re.S)
    val = int(pts.group(1)) if pts else None
    r.add("BA-5", "Story points one of 1/2/3/5/8", val in (1, 2, 3, 5, 8), f"found: {val}")

    tc = section(t, "tech constraints")
    req = {"service + port": r"Service\s*:\s*[\w\-]+.*port\s*\d+", "branch ai/SCRUM-{n}-{slug}": r"ai/[A-Z][A-Z0-9_]*-\d+-[\w\-]+",
           "PR target develop": r"PR target\s*:\s*develop", "CLAUDE.md read instruction": r"Read CLAUDE\.md",
           "blocked-by line": r"Blocked by\s*:\s*(?:[A-Z][A-Z0-9_]*-\d+|None)"}
    miss = [k for k, p in req.items() if not re.search(p, tc, re.I)]
    r.add("BA-6", "Tech constraints complete", not miss, f"missing: {miss}" if miss else "5/5")

    svc_m = re.search(r"Service\s*:\s*([\w\-]+)", tc)
    svc = svc_m.group(1) if svc_m else None
    if repo.path:
        known = repo.services()
        r.add("BA-7", "Named service exists in the repo", svc in known, f"'{svc}' — known: {', '.join(sorted(known))}")
        named = sorted(n for n in known if n != "api-gateway" and re.search(r"\b" + re.escape(n) + r"\b", t))
        r.add("BA-8", "Single service boundary (one service named)", len(named) <= 1, f"named: {named}")
        port_m = re.search(r"port\s*(\d+)", tc)
        real = repo.port(svc) if svc in known else None
        if port_m and real:
            r.add("BA-9", "Port matches the service's server.port", int(port_m.group(1)) == int(real),
                  f"story {port_m.group(1)}, code {real}")
        paths = {m.group(2) for a in acs for m in [HTTP_LINE.search(a)] if m}
        routes = repo.gateway_routes()
        wrong = []
        for p in paths:
            owner = next((s for pre, s in sorted(routes, key=lambda x: -len(x[0])) if p.startswith(pre)), None)
            if owner and svc and owner != svc:
                wrong.append(f"{p} routes to {owner}, story says {svc}")
        r.add("BA-10", "AC paths route (via the gateway) to the named service", not wrong, "; ".join(wrong) or "ok", wrong)
        existing = [f"{m.group(1)} {m.group(2)}" for a in acs for m in [HTTP_LINE.search(a)] if m
                    and any(ep_match(m.group(2), e["path"], loose=True) and e["verb"] in (m.group(1), "ANY") for e in repo.endpoints(svc))]
        r.add("BA-11", "Endpoint is new (not already implemented)", not existing,
              f"already exists in code: {sorted(set(existing))}" if existing else "new", warn=True)
        ai = section(t, "ai context")
        tables = repo.tables(svc) if svc else set()
        named_tables = {w.lower() for w in re.findall(r"\b([a-z_]{3,})\b", ai)} & tables
        r.add("BA-12", "Seed data names a real table of the service", bool(named_tables) or "synthetic" in ai.lower(),
              f"tables named: {sorted(named_tables) or 'none'}; service tables: {sorted(tables)[:10]}")
        hits = section18_hits(t, repo.out_of_scope())
        r.add("BA-13", "No CLAUDE.md §18 item in the story", not hits, f"found: {hits}" if hits else "none")
    else:
        for cid in ("BA-7", "BA-8", "BA-9", "BA-10", "BA-11", "BA-12", "BA-13"):
            r.skip(cid, "repo-backed check", "no --repo given")

    ai = section(t, "ai context")
    ai_req = {"service and port": r"port", "call path": r"Frontend\s*→|API Gateway", "response field sources": r"column|source|field"}
    miss = [k for k, p in ai_req.items() if not re.search(p, ai, re.I)]
    r.add("BA-14", "AI Context has service/port, call path, field sources", not miss, f"missing: {miss}" if miss else "ok")

    blocked = re.findall(r"Blocked by\s*:\s*([^\n]+)", t)
    keys = sorted({k for b in blocked for k in JIRA_KEY.findall(b)})
    if keys and ctx.facts:
        open_ = [k for k in keys if (ctx.facts.get("issues", {}).get(k, {}).get("status", "").lower() not in ("done", "closed"))]
        r.add("BA-15", "Blocked-by tickets are Done", not open_, f"open: {open_}" if open_ else f"{keys} done", source="supplied")
    elif keys:
        r.skip("BA-15", "Blocked-by tickets are Done", f"{keys} named; pass --facts with their JIRA status")

    ph = placeholders(t)
    r.add("BA-16", "No placeholders / TBD left", not ph, f"{len(ph)} found", ph)
