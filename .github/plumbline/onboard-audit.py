#!/usr/bin/env python3
"""Plumbline onboarding audit — deterministic, no model. Run from the repository root after /pl-onboard writes:
    python3 .github/plumbline/onboard-audit.py          exit 0 = PASS, 1 = FAIL lines printed
Every unit is a folder with a CLAUDE.md (besides the root). Checks, for every unit at once:
 1 endpoints declared in code (Spring mappings) appear in the unit's docs      2 tables created in migrations appear
 3 Kafka topics used as literals appear                                        4 [code: …] tags name files that exist
 5 X-User-* headers with a silent defaultValue are in the root's Decisions needed 6 a missing role header that
   passes the filter is in the root's Decisions needed                                                        7 CORS open to any origin is documented
 8 a port published in docker-compose matches "Reachable without that check"   9 the test recipe actually ran
10 every "Security risk:" in a unit file is named in the root's Decisions needed.
PLUMBLINE_AUDIT_SKIP=recipe,… skips checks by name (recipe, endpoints, tables, topics, tags, security, reach, root)."""
import glob, os, re, subprocess, sys
skip = set(filter(None, os.environ.get("PLUMBLINE_AUDIT_SKIP", "").split(",")))
def rd(p):
    try: return open(p, errors="ignore").read()
    except OSError: return ""
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.splitlines()
root = rd("CLAUDE.md"); needed = root.split("## Decisions needed")[-1].split("\n## ")[0]
compose = "".join(rd(p) for p in tracked if re.match(r"(.*/)?docker-compose[^/]*\.ya?ml$", p))
units = sorted({os.path.dirname(p) for p in tracked if p.endswith("/CLAUDE.md")})
fails = []
def fail(check, unit, what):
    line = f"FAIL {unit} [{check}]: {what}"
    if check not in skip and line not in fails: fails.append(line)
for u in units:
    n = os.path.basename(u.rstrip("/")) if u not in ("src",) else "(root app)"
    core = rd(f"{u}/CLAUDE.md"); docs = core + rd(f"{u}/CLAUDE.reference.md")
    ndocs = re.sub(r"\{[^}/]*\}", "{}", docs)
    base_dir = os.path.dirname(u) if u.endswith("/src") or u == "src" else u
    code = [p for p in tracked if p.startswith((base_dir + "/") if base_dir else "") and re.search(r"\.(java|kt|ts|tsx|js)$", p)
            and "/test/" not in p and "/e2e/" not in p and "node_modules" not in p]
    src = "\n".join(rd(p) for p in code)
    for p in code:                                                                  # 1 endpoints
        t = rd(p)
        if "@RestController" not in t and "@Controller" not in t: continue
        b = re.search(r'@RequestMapping\(\s*(?:value\s*=\s*|path\s*=\s*)?"([^"]*)"', t); base = b.group(1) if b else ""
        for m in re.finditer(r'@(Get|Post|Put|Patch|Delete)Mapping(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?"([^"]*)")?', t):
            path = (base + (m.group(2) or "")).rstrip("/") or "/"
            norm = re.sub(r"\{[^}/]*\}", "{}", path)
            if norm != "/" and norm not in ndocs: fail("endpoints", n, f"{m.group(1).upper()} {path} is not in the docs")
    for p in [x for x in tracked if x.startswith(base_dir + "/") and "/db/migration/" in x and x.endswith(".sql")]:   # 2
        for t in re.findall(r"CREATE TABLE(?: IF NOT EXISTS)?\s+([\w.]+)", rd(p), re.I):
            if t.split(".")[-1] not in docs: fail("tables", n, f"table {t} ({os.path.basename(p)}) is not in the docs")
    for t in set(re.findall(r'(?:topics\s*=\s*\{?\s*|\.send\(\s*)"([a-z][\w.-]+\.[\w.-]+)"', src)):           # 3
        if t not in docs: fail("topics", n, f"Kafka topic {t} is not in the docs")
    for tag in re.findall(r"\[code: ([^\]]+)\]", core):                                                       # 4
        for part in re.split(r"[,;]", tag):
            f = part.strip().strip("`").split(":")[0].split("#")[0]
            name = os.path.basename(f)
            if not name or "*" in name or " " in name or "." not in name: continue
            if not any(x.endswith("/" + name) or x == name for x in tracked): fail("tags", n, f"[code: {part.strip()}] names a file that does not exist")
    for m in re.finditer(r'@RequestHeader\([^)]*"(X-User-[\w-]+)"[^)]*defaultValue\s*=\s*"([^"]+)"', src):     # 5
        if m.group(2) not in needed:
            fail("security", n, f'{m.group(1)} silently defaults to "{m.group(2)}" when missing — not in the root\'s Decisions needed')
    flat = re.sub(r"\s+", " ", src)                                                                            # 6
    if re.search(r"if \(\s*role\s*==\s*null\s*\|\|\s*role\.isBlank\(\)\s*\)\s*\{\s*chain\.doFilter", flat) \
       and not re.search(r"(?i)" + re.escape(n) + r"[^\n]*((no|missing|without)[^.\n]{0,60}pass|pass[^.\n]{0,60}(no|missing|without))", needed):
        fail("security", n, "requests without a role header pass the filter — not in the root's Decisions needed")
    if re.search(r'allowedOrigin(Pattern)?s\("\*"\)|@CrossOrigin(\(\s*\)|\("\*"\))', src) and "CORS" not in docs.upper():  # 7
        fail("security", n, "CORS allows any origin — not documented")
    sm = re.search(r"\n  " + re.escape(n) + r":\n(.*?)(?=\n  [a-z][\w-]*:\n|\Z)", compose, re.S)               # 8
    rf = re.search(r"Reachable without that check:(.*)", core)
    if sm and "ports:" in sm.group(1) and (not rf or not re.search(r"(?i)\byes\b|published", rf.group(1))):
        fail("reach", n, "docker-compose publishes a port, but 'Reachable without that check' does not say so")
    tr = re.search(r"Test recipe[^\n]*", core)                                                                 # 9
    if not tr: fail("recipe", n, "no Test recipe line")
    elif re.search(r"(?i)\bnot run\b|\bnot executed\b", tr.group(0)): fail("recipe", n, "the test recipe was not run: " + tr.group(0)[:100])
    for risk in re.findall(r"Security risk:([^\n]*)", core):                                                   # 10
        if n not in needed: fail("root", n, "names a Security risk the root's Decisions needed does not: " + risk.strip()[:80])
print("\n".join(fails) if fails else f"PASS: {len(units)} units audited")
sys.exit(1 if fails else 0)
