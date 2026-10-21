"""Onboard benchmark — a unit's CLAUDE.md (onboard-eval-loop Step C) checked claim-by-claim against the code: a backend
service (OB-*) or a frontend (OBF-*: sections, API surface both ways, unmatched calls marked, token storage recorded).
Two directions: COVERAGE (everything in the code is documented) and NO INVENTED FACTS (everything documented exists).
Judge keeps: usefulness, business-rule accuracy, terminology, Confluence/CLAUDE.md consistency."""
import re

from common import UsageError, ep_match, read, section

SECTIONS = {"purpose": ("service purpose", "purpose"), "port": ("port",), "schema": ("database schema", "schema"),
            "produced": ("topics produced", "produced"), "consumed": ("topics consumed", "consumed"),
            "redis": ("redis",), "exposed": ("endpoints exposed", "rest endpoints exposed"),
            "called": ("endpoints called", "downstream"), "entities": ("entities",), "never": ("must never",),
            "rules": ("business rules", "design rules", "key rules", "domain rules")}
EP = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\b[\s|`]+(/[\w\-/{}.*]+)")   # "GET /x", "| GET | `/x` |"


FE_SECTIONS = {"purpose": ("app purpose", "purpose"), "stack": ("tech stack",), "port": ("port", "dev url"),
               "routes": ("page / route", "route catalog", "routes"), "api": ("api surface", "backend calls"),
               "state": ("state management",), "env": ("environment variables",), "never": ("must never",),
               "rules": ("ux", "business rules"), "debt": ("known tech debt", "tech debt"), "compliance": ("compliance",)}
NORM = lambda p: re.sub(r"\$\{[^}]*\}|\{[^}]*\}|:\w+", "{x}", p.split("?")[0].rstrip("/`"))


def run_frontend(r, ctx, u):
    t, repo, name = ctx.text, ctx.repo, ctx.service
    body = {k: section(t, *v) for k, v in FE_SECTIONS.items()}
    miss = [k for k, v in body.items() if not v.strip()]
    r.add("OBF-1", "All 11 frontend CLAUDE.md sections present", not miss, f"missing: {miss}" if miss else "11/11")
    code = {NORM(c["path"]) for c in u["calls"]}
    doc_paths = {NORM(m) for m in re.findall(r"(/api/[\w\-/{}$.:]+)", body["api"])}
    match = lambda a, b: ep_match(a, b) or ep_match(a.replace("{x}", "{*}"), b.replace("{x}", "{*}"))
    undoc = sorted(p for p in code if not any(match(p, d) for d in doc_paths))
    inv = sorted(d for d in doc_paths if not any(match(d, p) for p in code))
    r.add("OBF-2", "Every backend path the code calls is in the API Surface", not undoc,
          f"{len(code)} distinct paths called, {len(undoc)} undocumented", undoc)
    r.add("OBF-3", "No documented API path that the code never calls", not inv, f"{len(inv)} invented", inv)
    unmatched = sorted({NORM(e["path"]) for e in repo.dm["rest_edges"] if e["from"] == name and not e.get("to")})
    marked = [p for p in unmatched if re.search(re.escape(p.split("{x}")[0].rstrip("/")) + r".*(no matching|unmatched|not served|no endpoint|stale)",
                                                    body["api"] + body["debt"], re.I)]
    missing = [p for p in unmatched if p not in marked]
    r.add("OBF-4", "Calls that no backend endpoint serves are marked as such (no invented behaviour)", not missing,
          f"{len(unmatched)} unmatched calls, {len(missing)} not marked", missing, warn=True)
    src = [f for f in repo.dir(name).rglob("src/**/*.ts") if "node_modules" not in f.parts and ".spec." not in f.name]
    ls = [f"{f.relative_to(repo.path)}:{i}" for f in src for i, l in enumerate(read(f).splitlines(), 1)
          if re.search(r"LocalStorage\b|localStorage\.setItem\([^)]*(token|auth|jwt)", l, re.I)]
    if ls:
        ok = re.search(r"localStorage|LocalStorage", body["compliance"]) is not None
        r.add("OBF-5", "Token storage in localStorage is recorded under Compliance Notes", ok, f"{len(ls)} site(s)", ls[:10])
    else:
        r.add("OBF-5", "Token storage in localStorage is recorded under Compliance Notes", True, "none in code")


def run(r, ctx):
    t, repo, svc = ctx.text, ctx.repo, ctx.service
    if repo.path and svc and (repo.unit(svc) or {}).get("kind") == "frontend":
        return run_frontend(r, ctx, repo.unit(svc))
    body = {k: section(t, *v) for k, v in SECTIONS.items()}
    miss = [k for k, v in body.items() if not v.strip()]
    r.add("OB-1", "All 11 service CLAUDE.md sections present", not miss, f"missing: {miss}" if miss else "11/11")
    if not (repo.path and svc):
        raise UsageError("pass --repo and --service")
    u = repo.services().get(svc)
    if not u:
        raise UsageError(f"service '{svc}' not found in {repo.path}")
    pm = re.search(r"\b(\d{4,5})\b", body["port"])
    r.add("OB-2", "Port matches server.port", bool(pm) and int(pm.group(1)) == int(u["port"] or 0),
          f"doc {pm and pm.group(1)}, code {u['port']}")
    if u.get("schema"):
        r.add("OB-3", "Schema matches the service's schema", u["schema"] in body["schema"], f"code {u['schema']}")

    src = list(repo.dir(svc).glob("src/main/java/**/*.java"))
    code_txt = "\n".join(read(f) for f in src)
    framework = lambda p: p.startswith("/actuator")       # Spring framework endpoints are not part of the contract
    code_eps = {(p["verb"], re.sub(r"\{[^}]*\}", "{x}", p["path"])) for p in u["provides"] if not framework(p["path"])}
    doc_eps = {(m.group(1), re.sub(r"\{[^}]*\}", "{x}", m.group(2).rstrip("`"))) for m in EP.finditer(body["exposed"])
               if not framework(m.group(2))}
    undoc = sorted(f"{v} {p}" for v, p in code_eps if not any(v == dv and ep_match(p, dp) for dv, dp in doc_eps))
    # "invented" = no controller serves it. Excused only when a filter serves it: the path has no variables and the
    # whole path is a string literal in the service's code (e.g. an SSE proxy filter's "/api/v1/notifications/stream")
    served_by_filter = lambda p: "{" not in p and f'"{p}"' in code_txt
    invented = sorted(f"{v} {p}" for v, p in doc_eps if not any(v == cv and ep_match(p, cp) for cv, cp in code_eps)
                      and not served_by_filter(p))
    r.add("OB-4", "Every endpoint in the code is documented", not undoc, f"{len(code_eps)} in code, {len(undoc)} undocumented", undoc)
    r.add("OB-5", "No documented endpoint that the code does not have", not invented, f"{len(invented)} invented", invented)

    prod = {k["topic"] for k in u["kafka"] if k["role"] == "producer"}
    cons = {k["topic"] for k in u["kafka"] if k["role"] == "consumer"}
    def tok(sec):
        """Topic CLAIMS: first cell of a table row, a bullet's first token, or a `backticked` name — not prose."""
        out = set()
        for l in sec.splitlines():
            cells = [c.strip(" `") for c in l.strip().strip("|").split("|")] if l.strip().startswith("|") else []
            cand = cells[:1] + re.findall(r"`([^`]+)`", l)
            m = re.match(r"\s*[-*]\s+`?([a-z][\w.\-]+)", l)
            if m:
                cand.append(m.group(1))
            out |= {x for x in cand if re.fullmatch(r"[a-z][a-z0-9]*(?:\.[a-z0-9\-]+)+", x)
                    and not x.endswith(("-group", ".yml", ".yaml", ".java", ".md"))}
        return out
    dp, dc = tok(body["produced"]), tok(body["consumed"])
    alltopics = repo.topics()
    for cid, name, code, doc in (("OB-6", "produced", prod, dp), ("OB-7", "consumed", cons, dc)):
        und = sorted(code - doc)
        inv = sorted(doc - code)
        r.add(cid, f"Kafka topics {name}: code == doc", not und and not inv,
              f"code {sorted(code)}" + (f"; undocumented {und}" if und else "") + (f"; not in code {inv}" if inv else ""), und + inv)

    edges = [c for c in repo.dm["rest_edges"] if c["from"] == svc and c["kind"] == "rest" and c.get("to")]
    calls = sorted({c["to"] for c in edges})
    und = [d for d in calls if d not in body["called"]]
    r.add("OB-8", "Every downstream service called (REST) is documented", not und, f"code calls {calls}", und)
    # every documented downstream call (a row naming <service> and METHOD /path) must be a call the code makes
    known = repo.services()
    claimed, invented_calls = [], []
    for l in body["called"].splitlines():
        tgt = next((n for n in known if re.search(r"\b" + re.escape(n) + r"\b", l)), None)
        m = EP.search(l)
        if tgt and m:
            claimed.append((tgt, m.group(1), m.group(2).rstrip("`")))
    for tgt, verb, path in claimed:
        made = any(c["to"] == tgt and ep_match(path, c["path"].replace("{*}", "{x}"), loose=True) for c in edges)
        served = any(e["verb"] in (verb, "ANY") and ep_match(path, e["path"]) for e in repo.endpoints(tgt))
        if not (made and served):
            invented_calls.append(f"{tgt} {verb} {path}: " + ("not served by " + tgt if not served else "never called by this service"))
    named_svcs = sorted(n for n in known if n != svc and re.search(r"\b" + re.escape(n) + r"\b", body["called"]))
    invented_calls += [f"{n}: documented as called, the code never calls it" for n in named_svcs if n not in calls
                       and n not in {e["to"] for e in repo.dm["url_edges"] if e["unit"] == svc}]
    r.add("OB-8c", "Documented downstream calls exist (served by the target and made by this service)", not invented_calls,
          f"{len(claimed)} documented calls checked", invented_calls)
    cfg = sorted({e["to"] for e in repo.dm["url_edges"] if e["unit"] == svc and e.get("to") and e["to"] != svc} - set(calls))
    und = [d for d in cfg if d not in t]
    r.add("OB-8b", "Other services referenced in config (host:port, e.g. health checks) are mentioned", not und,
          f"config refs {cfg}", und, warn=True)
    entities = sorted({f.stem for f in src if re.search(r"^\s*@Entity\b", read(f), re.M)})
    und = [e for e in entities if not re.search(r"\b" + e + r"\b", body["entities"])]
    r.add("OB-9", "Every @Entity is documented (in the entities section)", not und, f"entities {entities}", und)
    claimed_ent = set(re.findall(r"^\s*\**`?([A-Z][A-Za-z0-9]+)`?\**\s*:", body["entities"], re.M)) | \
        {c.strip(" `*") for l in body["entities"].splitlines() if l.strip().startswith("|")
         for c in l.strip().strip("|").split("|")[:1] if re.fullmatch(r"\s*`?[A-Z][A-Za-z0-9]+`?\s*", c)}
    inv = sorted(e for e in claimed_ent - set(entities) if e not in ("Entity", "Name", "Field", "Class", "None"))
    r.add("OB-9b", "No documented entity that the code does not have", not inv, f"{len(inv)} invented", inv)

    tables = sorted(repo.tables(svc))
    und = [x for x in tables if not re.search(r"\b" + re.escape(x) + r"\b", (body["schema"] + body["entities"]).lower())]
    r.add("OB-10", "Every table created by migrations is documented (schema/entities sections)", not und, f"{len(tables)} tables", und)
    claimed_tab = set(re.findall(r"`([a-z][a-z0-9_]+)`", body["schema"])) | set(re.findall(r"\btable\s+`([a-z][a-z0-9_]+)`", body["schema"], re.I))
    all_tables = repo.known_tables()
    inv = sorted(x for x in claimed_tab if "_" in x or x.endswith("s")) 
    inv = [x for x in inv if x not in all_tables and x != (u.get("schema") or "")]
    r.add("OB-10b", "No documented table that the repository does not define (migrations, SQL scripts, @Table)", not inv,
          f"{len(inv)} invented", inv)

    keys = set()
    for f in src:
        txt = read(f)
        if re.search(r"Redis|Cache", txt):
            keys |= {":".join(m.group(1).split(":")[:2]) for m in re.finditer(r'"([a-z][\w\-]*:[\w\-:]*)"', txt)
                     if not m.group(1).startswith(("http:", "https:", "jdbc:", "classpath:"))}
    und = sorted(k for k in keys if k.rstrip(":") not in body["redis"])
    r.add("OB-11", "Redis key prefixes used in code are documented", not und, f"code prefixes {sorted(keys)}", und)
    claimed_keys = {":".join(m.group(1).split(":")[:2]).rstrip(":") for m in
                    re.finditer(r"`?([a-z][\w\-]*:[\w\-{}:]+)`?", body["redis"]) if not m.group(1).startswith(("http", "jdbc"))}
    code_txt_all = code_txt
    inv = sorted(k for k in claimed_keys if k.split(":{")[0].rstrip(":") not in {c.rstrip(":") for c in keys}
                 and f'"{k.split("{")[0]}' not in code_txt_all)
    r.add("OB-11b", "No documented Redis key that the code does not use", not inv, f"{len(inv)} invented", inv)

    if len(repo.services()) == 1:     # the only backend: frontend calls nobody serves are its gap to record
        fe = sorted({e["path"] for e in repo.dm["rest_edges"] if not e.get("to")
                     and (repo.unit(e["from"]) or {}).get("kind") == "frontend"})
        noted = [p for p in fe if p.split("{")[0].rstrip("/") in t]
        r.add("OB-13", "Frontend calls that no endpoint serves are listed (tech debt), not added to the catalog",
              len(noted) == len(fe), f"{len(fe)} unmatched frontend calls, {len(fe) - len(noted)} not listed",
              [p for p in fe if p not in noted], warn=True)
    debt = sum(len(re.findall(r"\b(TODO|FIXME|HACK)\b", read(f))) for f in src)
    sec12 = section(t, "tech debt")
    r.add("OB-12", "TODO/FIXME/HACK markers acknowledged in a tech-debt section", debt == 0 or bool(sec12.strip()),
          f"{debt} markers in code; tech-debt section {'present' if sec12.strip() else 'absent'}", warn=True)
