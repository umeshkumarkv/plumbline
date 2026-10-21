"""Doc benchmark — openapi.yaml + service CLAUDE.md after a code change (doc-eval-loop Steps B–D).
Endpoints/topics changed by the diff must be documented (FAIL); older gaps are reported as debt (WARN).
Judge keeps: clarity, correctness of descriptions, examples, field semantics."""
import re
import subprocess

import yaml

from common import UsageError, endpoints_at, ep_match, git_ok_ref, read


def run(r, ctx):
    repo, svc = ctx.repo.path, ctx.service
    if not (repo and svc):
        raise UsageError("pass --repo and --service")
    u = ctx.repo.services().get(svc)
    if not u:
        raise UsageError(f"service '{svc}' not found in {repo}")
    if not (ctx.base and git_ok_ref(repo, ctx.base)):
        raise UsageError(f"--base '{ctx.base}' is not a commit: pass the merged PR's parent, e.g. <merge-sha>^1")
    oa_path = ctx.repo.dir(svc) / "openapi.yaml"
    try:
        oa = yaml.safe_load(read(oa_path)) or {}
        r.add("DOC-1", "openapi.yaml parses", True, str(oa_path.relative_to(repo)))
    except yaml.YAMLError as e:
        r.add("DOC-1", "openapi.yaml parses", False, str(e).splitlines()[0])
        oa = {}
    paths = oa.get("paths") or {}
    docd = {(m.upper(), p) for p, ops in paths.items() if isinstance(ops, dict) for m in ops if m.lower() in
            ("get", "post", "put", "patch", "delete")}
    bases = {""} | {re.sub(r"^https?://[^/]+", "", str(x.get("url", ""))).rstrip("/") for x in oa.get("servers") or []}
    base_eps = endpoints_at(repo, ctx.base, svc)
    new_gap, old_gap = [], []
    for e in u["provides"]:
        if not any(v == e["verb"] and ep_match(e["path"], b + p) for v, p in docd for b in bases):
            key = (e["verb"], re.sub(r"\{[^}]*\}", "{*}", e["path"]))
            touched = key not in base_eps or base_eps[key] != e.get("fp")
            (new_gap if touched else old_gap).append(f"{e['verb']} {e['path']}")
    r.add("DOC-2", "Endpoints touched by this change are in openapi.yaml", not new_gap, f"{len(new_gap)} missing", new_gap)
    r.add("DOC-3", "All endpoints in openapi.yaml (pre-existing gaps)", not old_gap, f"{len(old_gap)} undocumented", old_gap, warn=True)

    money = set()
    for f in ctx.repo.dir(svc).glob("src/main/java/**/dto/**/*.java"):
        money |= set(re.findall(r"BigDecimal\s+(\w+)\s*[;,)=]", read(f)))
    wrong = []

    def walk(o, where):
        if isinstance(o, dict):
            props = o.get("properties")
            if isinstance(props, dict):
                for k, v in props.items():
                    if k in money and isinstance(v, dict) and v.get("type") in ("number", "integer"):
                        wrong.append(f"{where}.{k}: type {v.get('type')}")
            for k, v in o.items():
                walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
    walk(oa.get("components") or {}, "components")
    r.add("DOC-4", "Monetary (BigDecimal) fields are type string in openapi.yaml", not wrong, f"{len(wrong)} numeric", wrong)

    md = read(ctx.repo.claude_md(svc))
    topics = sorted({k["topic"] for k in u["kafka"]})
    und = [x for x in topics if x not in md]
    r.add("DOC-5", "Every Kafka topic of the service is in its CLAUDE.md", not und, f"topics {topics}", und)
    envs = set()
    for f in ctx.repo.dir(svc).glob("src/main/resources/application*.y*ml"):
        envs |= set(re.findall(r"\$\{([A-Z][A-Z0-9_]+)(?::[^}]*)?\}", read(f)))
    und = sorted(e for e in envs if e not in md)
    r.add("DOC-6", "Every environment variable in application.yml is in CLAUDE.md", not und, f"{len(envs)} env vars", und, warn=True)
    pom_diff = subprocess.run(["git", "diff", f"{ctx.base}...HEAD", "--", f"{ctx.repo.rel(svc)}pom.xml"], cwd=repo,
                              capture_output=True, text=True).stdout
    added = re.findall(r"^\+\s*<artifactId>([^<]+)</artifactId>", pom_diff, re.M)
    und = [a for a in added if a not in md]
    r.add("DOC-7", "New Maven dependencies are in CLAUDE.md", not und, f"added {added or 'none'}", und)
    broken = []
    for f in [ctx.repo.claude_md(svc), repo / "CLAUDE.md"]:
        for m in re.finditer(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", read(f)):
            tgt = m.group(1)
            if not re.match(r"[a-z]+:", tgt) and not (f.parent / tgt).exists():
                broken.append(f"{f.relative_to(repo)} -> {tgt}")
    r.add("DOC-8", "Relative links in CLAUDE.md files resolve", not broken, f"{len(broken)} broken", broken)
