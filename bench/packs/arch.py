"""Arch benchmark — the technical design (arch-eval-loop Step B) checked against the CODE, not against itself.
Judge keeps: design quality, trade-offs, NFRs, identity/UUID domains, RBAC correctness."""
import re

from common import STATUS, ep_match, placeholders, section

SECTIONS = ["ENDPOINT DESIGN", "SCHEMA CHANGES", "ENTITY CHANGES", "SERVICE LOGIC", "EXTERNAL CALLS", "KAFKA",
            "REDIS", "TEST PLAN", "OPENAPI DELTA"]


def run(r, ctx):
    t, repo = ctx.text, ctx.repo
    present = {s: bool(re.search(r"^\s*`*" + s + r"\b", t, re.M)) for s in SECTIONS}
    miss = [s for s, ok in present.items() if not ok]
    r.add("AR-1", "All 9 design blocks present (NONE allowed where not applicable)", not miss, f"missing: {miss}" if miss else "9/9")

    ed = section(t, "ENDPOINT DESIGN")
    method = re.search(r"Method\s*:\s*(GET|POST|PUT|PATCH|DELETE)\b", ed)
    path = re.search(r"Path\s*:\s*(/api/v1/[\w\-/{}?]+)", ed)
    svc = re.search(r"Service\s*:\s*([\w\-]+)\s+port\s+(\d+)", ed)
    r.add("AR-2", "Endpoint method, path and service+port stated", bool(method and path and svc),
          f"method={method and method.group(1)} path={path and path.group(1)} service={svc and svc.group(1)}")
    p = path.group(1).replace("?", "") if path else None
    s = svc.group(1) if svc else None

    if repo.path and s:
        known = repo.services()
        r.add("AR-3", "Service exists", s in known, f"'{s}'")
        if s in known:
            r.add("AR-4", "Port matches server.port", str(repo.port(s)) == svc.group(2), f"design {svc.group(2)}, code {repo.port(s)}")
            exp = repo.schema(s)
            sm = re.search(r"Service schema\s*:\s*(\w+)", section(t, "SCHEMA CHANGES"))
            if sm and exp:
                r.add("AR-5", "Schema is the service's own schema", sm.group(1) == exp, f"design {sm.group(1)}, owner schema {exp}")
            routes = repo.gateway_routes()
            owner = next((sv for pre, sv in sorted(routes, key=lambda x: -len(x[0])) if p and p.startswith(pre)), None)
            r.add("AR-6", "Path is routed by the gateway to this service", owner == s,
                  f"{p} -> {owner or 'no gateway route'}", warn=owner is None)
            clash = [f"{e['verb']} {e['path']}" for e in repo.endpoints(s) if p and method and ep_match(p, e["path"]) and e["verb"] == method.group(1)]
            r.add("AR-7", "Endpoint does not already exist (or is declared a change)", not clash or "existing" in ed.lower(),
                  f"already in code: {clash}" if clash else "new", warn=True)
            mig = re.search(r"Migration file\s*:\s*V(\d+)__", section(t, "SCHEMA CHANGES"))
            if mig:
                vs = [int(m.group(1)) for f in repo.dir(s).glob("src/main/resources/db/migration/V*__*.sql")
                      for m in [re.match(r"V(\d+)__", f.name)] if m]
                nxt = max(vs) + 1 if vs else 1
                r.add("AR-8", "Migration version is the next free one", int(mig.group(1)) == nxt, f"design V{mig.group(1)}, next free V{nxt}")
        # every downstream call names an existing endpoint of an existing service
        ext = section(t, "EXTERNAL CALLS")
        bad = []
        for m in re.finditer(r"([\w\-]+-service)\s*\((\d+)\)\s*:\s*(GET|POST|PUT|PATCH|DELETE)\s+(/[\w\-/{}]+)", ext):
            tgt, _, verb, ep = m.groups()
            if tgt not in known:
                bad.append(f"{tgt}: no such service")
            elif not any(ep_match(ep, e["path"]) and e["verb"] in (verb, "ANY") for e in repo.endpoints(tgt)):
                bad.append(f"{tgt} has no {verb} {ep}")
        r.add("AR-9", "External calls target endpoints that exist", not bad, "; ".join(bad) or "ok", bad)
        kaf = section(t, "KAFKA")
        topics = repo.topics()
        cons = [m.group(1) for m in re.finditer(r"Consumes\s*:\s*([\w.\-]+)", kaf)]
        prods = [m.group(1) for m in re.finditer(r"Produces\s*:\s*([\w.\-]+)", kaf)]
        ghost = [c for c in cons if c not in topics]
        r.add("AR-10", "Consumed topics are produced somewhere", not ghost, f"no producer for: {ghost}" if ghost else "ok")
        reuse = [x for x in prods if x in topics]
        if reuse:
            prod_by = {x: [k["service"] for k in repo.dm["topics"][x]["producers"]] for x in reuse}
            r.add("AR-11", "Produced topics: existing ones flagged for impact", False,
                  f"existing topics (consumers must stay compatible): {prod_by}", warn=True)
    else:
        r.skip("AR-3..11", "repo-backed checks", "no --repo given or no service in the design")

    errs = section(t, "ERROR RESPONSES")
    err_codes = {m.group(1) for m in re.finditer(r"\b([45]\d\d)\s*:", errs)}
    if ctx.story_text:
        story_status = {s for s in STATUS.findall(section(ctx.story_text, "acceptance criteria")) if s[0] in "45"}
        miss = sorted(story_status - err_codes)
        r.add("AR-12", "Every error status in the story ACs has an error code in the design", not miss,
              f"story errors {sorted(story_status)}, design {sorted(err_codes)}" + (f", missing {miss}" if miss else ""))
    else:
        r.skip("AR-12", "AC error statuses covered", "no --story given")

    tp = section(t, "TEST PLAN")
    svc_tests = len(re.findall(r"^\s*-\s+\S", section(tp, "ServiceTest") or tp.split("ControllerTest")[0], re.M))
    ctl = tp.split("ControllerTest", 1)[1] if "ControllerTest" in tp else ""
    ctl_tests = len(re.findall(r"^\s*-\s+\S", ctl, re.M))
    r.add("AR-13", ">= 3 unit tests per layer (service + controller)", svc_tests >= 3 and ctl_tests >= 3,
          f"service {svc_tests}, controller {ctl_tests}")
    rbac = re.search(r"\b(TRADER|OPERATIONS|ADMIN)\b", ed + section(t, "RBAC"))
    r.add("AR-14", "RBAC: roles named for the endpoint", bool(rbac), "role named" if rbac else "no TRADER/OPERATIONS/ADMIN in endpoint/RBAC")
    hdr = re.search(r"\bX-[A-Z][\w-]+", t)
    r.add("AR-15", "Gateway-forwarded headers named (e.g. X-User-Id)", bool(hdr), hdr.group(0) if hdr else "none", warn=True)
    ph = placeholders(t)
    r.add("AR-16", "No placeholders left", not ph, f"{len(ph)} found", ph)
