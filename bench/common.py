"""Shared pieces of the Plumbline benchmark stage: check results, report, markdown parsing, repo facts.

The benchmark is the deterministic middle stage of every eval loop:
    ORIGINATOR (agent writes the artifact) -> BENCHMARK (this, no LLM) -> JUDGE (isolated critic)
A check result is one of:
    PASS  measured and satisfied
    FAIL  measured and violated            -> the loop goes back to the originator; the judge is not called
    WARN  measured, needs a human/judge look (reported to the judge as a fact, does not fail)
    SKIP  not applicable, or an input it needs was not supplied (always says which)
Every check carries `evidence` (what was measured, where) and `source`:
    "computed"   the benchmark derived it from the repo / CI / artifact itself
    "supplied"   it depends on facts the originator supplied (e.g. JIRA data); the judge is told so
"""
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Template placeholders left from the spec ({one paragraph}, {trader | ops}, {field}) — NOT path variables (/{id}, -{id})
TEMPLATE_WORDS = {"field", "value", "n", "x", "port", "service", "service-name", "resource", "role", "feature", "slug",
                  "description", "type", "name", "code", "condition", "status", "topic", "table", "classname", "params"}
PLACEHOLDER = re.compile(r"(?<![/\w\-])\{([^{}\n]{1,80})\}|\bTBD\b|\bTODO\b|\?\?\?|<fill[^>]*>", re.I)
JIRA_KEY = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
HTTP_LINE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(?:https?://[^/\s]+)?(/api/[\w\-/{}.]*)")
STATUS = re.compile(r"\b([1-5]\d\d)\b")


class UsageError(Exception):
    """Wrong command or missing/invalid input: the originator's mistake, not a gap (exit 2)."""


@dataclass
class Check:
    id: str
    title: str
    result: str                     # PASS | FAIL | WARN | SKIP
    detail: str = ""
    evidence: list = field(default_factory=list)
    source: str = "computed"


class Report:
    def __init__(self, agent: str, artifact: str):
        self.agent, self.artifact, self.checks = agent, artifact, []

    def add(self, cid, title, ok, detail="", evidence=None, warn=False, source="computed", skip=False):
        res = "SKIP" if skip else ("PASS" if ok else ("WARN" if warn else "FAIL"))
        ev = list(evidence or [])
        if len(ev) > 100:
            ev = ev[:100] + [f"... and {len(ev) - 100} more"]
        self.checks.append(Check(cid, title, res, detail, ev, source))
        return ok

    def skip(self, cid, title, why):
        self.checks.append(Check(cid, title, "SKIP", why))

    @property
    def verdict(self):
        return "FAIL" if any(c.result == "FAIL" for c in self.checks) else "PASS"

    def to_json(self):
        return {"agent": self.agent, "artifact": self.artifact, "verdict": self.verdict,
                "counts": {r: sum(c.result == r for c in self.checks) for r in ("PASS", "FAIL", "WARN", "SKIP")},
                "checks": [asdict(c) for c in self.checks]}

    def to_md(self):
        j = self.to_json()
        md = [f"# BENCHMARK — {self.agent} — {j['verdict']}",
              f"Artifact: `{self.artifact}` · " + " · ".join(f"{k} {v}" for k, v in j["counts"].items()),
              "", "Deterministic checks (no LLM). These are FACTS for the judge: do not re-litigate a PASS/FAIL here;",
              "judge what these checks cannot measure. `source: supplied` = depends on data the originator provided.", "",
              "| id | result | check | detail |", "|---|---|---|---|"]
        for c in self.checks:
            src = " _(supplied)_" if c.source == "supplied" else ""
            md.append(f"| {c.id} | **{c.result}** | {c.title}{src} | {c.detail.replace('|', '/')[:300]} |")
        for c in self.checks:
            if c.evidence and c.result in ("FAIL", "WARN"):
                md += ["", f"**{c.id} evidence**"] + [f"- {e}" for e in c.evidence]
        return "\n".join(md) + "\n"


# ───────────── markdown ─────────────

def read(p) -> str:
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return ""


def section(text: str, *names) -> str:
    """Body of the first section whose heading (markdown `#..` or an UPPERCASE block label line) matches any name
    (case-insensitive, substring). Ends at the next heading of the same kind or a ``` fence close + heading."""
    lines = text.splitlines()
    pats = [n.lower() for n in names]
    for i, l in enumerate(lines):
        s = l.strip().strip("`").strip()
        is_md = s.startswith("#")
        is_label = bool(re.fullmatch(r"[A-Z][A-Z0-9 /&()\-]{2,60}", s.split(":")[0].strip())) and (":" not in s or s.endswith(":"))
        if (is_md or is_label) and any(p in s.lower() for p in pats):
            out = []
            for l2 in lines[i + 1:]:
                s2 = l2.strip().strip("`").strip()
                if s2.startswith("#") and is_md:
                    lvl = len(l.strip()) - len(l.strip().lstrip("#"))
                    lvl2 = len(s2) - len(s2.lstrip("#"))
                    if lvl2 <= lvl:
                        break
                if is_label and not is_md and re.fullmatch(r"[A-Z][A-Z0-9 /&()\-]{2,60}", s2) and s2 not in ("NONE",):
                    break
                if is_label and not is_md and s2.startswith("#"):
                    break
                out.append(l2)
            return "\n".join(out)
    return ""


def bullets(text: str):
    return [re.sub(r"^\s*(?:[-*+]|\d+[.)]|- \[[ x]\])\s*", "", l).strip() for l in text.splitlines()
            if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\S", l)]


def placeholders(text: str):
    out = []
    for i, l in enumerate(text.splitlines(), 1):
        for m in PLACEHOLDER.finditer(l):
            inner = m.group(1)
            if inner is not None and not (re.search(r"[ |]", inner) or inner.lower() in TEMPLATE_WORDS):
                continue   # {id}, {orderId}: a variable, not a template slot
            out.append(f"line {i}: `{m.group(0)}`")
    return out


# ───────────── repo facts ─────────────

class Repo:
    """Facts about the target repo, computed from code (impact/depmap) — never from the artifact under test."""

    def __init__(self, path):
        self.path = Path(path).resolve() if path else None
        self._dm = None

    @property
    def dm(self):
        if self._dm is None and self.path:
            sys.path.insert(0, str(ROOT / "impact"))
            import depmap  # noqa: E402
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                self._dm = depmap.build(self.path, None, None)
        return self._dm

    def services(self):
        return {n: u for n, u in (self.dm or {"services": {}})["services"].items() if u.get("kind") == "service"}

    def unit(self, name):
        """Any unit (backend or frontend) by name."""
        return (self.dm or {"services": {}})["services"].get(name)

    def known_tables(self):
        """Every table the repository defines anywhere: migrations, JPA @Table/@Entity names, and CREATE TABLE in any
        .sql file (manual SQL scripts included). Used to tell a documented table from an invented one."""
        out = set(self.tables(None))
        if not self.path:
            return out
        skip = ("node_modules", "target", ".plumbline", ".agentic-sdlc", ".guardrails", ".git")
        for f in self.path.rglob("*.sql"):
            if not any(x in f.parts for x in skip):
                for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?(?:\w+[`\"\]]?\.[`\"\[]?)?(\w+)",
                                     read(f), re.I):
                    out.add(m.group(1).lower())
        for f in self.path.rglob("*.java"):
            if not any(x in f.parts for x in skip) and "/src/test/" not in f.as_posix():
                t = read(f)
                if "@Entity" in t:
                    m = re.search(r'@Table\s*\(\s*(?:name\s*=\s*)?"(\w+)"', t)
                    c = re.search(r"\bclass\s+(\w+)", t)
                    if m:
                        out.add(m.group(1).lower())
                    elif c:
                        out.add(re.sub(r"(?<!^)(?=[A-Z])", "_", c.group(1)).lower())
        return out

    def known_columns(self):
        """Column names the repository defines: CREATE/ALTER TABLE column definitions in any .sql file, @Column(name=),
        and entity fields (snake_case of the Java field name, the default JPA naming)."""
        out = set()
        if not self.path:
            return out
        skip = ("node_modules", "target", ".plumbline", ".agentic-sdlc", ".guardrails", ".git")
        for f in self.path.rglob("*.sql"):
            if not any(x in f.parts for x in skip):
                t = read(f)
                out |= {m.lower() for m in re.findall(r"^\s*[`\"]?(\w+)[`\"]?\s+(?:BIGINT|INT|INTEGER|SMALLINT|VARCHAR|CHAR|TEXT|"
                                                     r"BOOLEAN|BOOL|DATE|TIMESTAMP|DATETIME|DECIMAL|NUMERIC|UUID|JSON|JSONB|"
                                                     r"BLOB|CLOB|REAL|DOUBLE|FLOAT|SERIAL|BIGSERIAL|TINYINT|LONGTEXT)\b", t, re.I | re.M)}
                out |= {m.lower() for m in re.findall(r"\bADD\s+(?:COLUMN\s+)?[`\"]?(\w+)", t, re.I)}
        for f in self.path.rglob("*.java"):
            if not any(x in f.parts for x in skip) and "/src/test/" not in f.as_posix():
                t = read(f)
                if "@Entity" in t or "@Embeddable" in t:
                    out |= {m.lower() for m in re.findall(r'@Column\s*\([^)]*name\s*=\s*"(\w+)"', t)}
                    out |= {re.sub(r"(?<!^)(?=[A-Z])", "_", m).lower()
                            for m in re.findall(r"^\s*(?:private|protected|public)\s+[\w<>,\s?]+\s+(\w+)\s*[;=]", t, re.M)}
        return out

    def file_stems(self):
        """Names of scripts and resources (e.g. panel_management_script.sql) — mentioned in schema notes, not tables."""
        if not self.path:
            return set()
        skip = ("node_modules", "target", ".plumbline", ".git")
        return {f.stem.lower() for f in self.path.rglob("*") if f.suffix in (".sql", ".py", ".sh", ".js", ".ts")
                and not any(x in f.parts for x in skip)}

    def dir(self, svc):
        """The unit's directory (impact/layout.py): services/<svc>, <svc>/, or the repo root for a root app."""
        u = (self.dm or {"services": {}})["services"].get(svc)
        return self.path / (u["path"] if u else f"services/{svc}")

    def claude_md(self, svc):
        """The unit's own CLAUDE.md (src/CLAUDE.md for an app at the repository root; the root file is the master)."""
        d = self.dir(svc)
        return d / "src" / "CLAUDE.md" if d.resolve() == self.path.resolve() else d / "CLAUDE.md"

    def rel(self, svc):
        p = self.dir(svc).relative_to(self.path).as_posix()
        return "" if p == "." else p + "/"

    def endpoints(self, svc=None):
        return [p for n, u in self.services().items() if svc in (None, n) for p in u["provides"]]

    def topics(self):
        return set((self.dm or {}).get("topics", {}))

    def gateway_routes(self):
        return [(e["path"], e["to"]) for e in (self.dm or {}).get("rest_edges", []) if e["kind"] == "route"]

    def port(self, svc):
        return (self.services().get(svc) or {}).get("port")

    def schema(self, svc):
        return (self.services().get(svc) or {}).get("schema")

    def tables(self, svc=None):
        out = set()
        if not self.path:
            return out
        dirs = [self.dir(svc)] if svc else [self.dir(n) for n in self.services()]
        for f in (f for d in dirs for f in d.glob("src/main/resources/db/migration/*.sql")):
            for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?(\w+)", read(f), re.I):
                out.add(m.group(1).lower())
        return out

    def rulebook(self):
        return read(self.path / "CLAUDE.md") if self.path else ""

    def out_of_scope(self):
        """CLAUDE.md Section 18 (Out of Scope) items."""
        sec = section(self.rulebook(), "out of scope")
        return [re.split(r"\s+[—-]\s+", b)[0].strip(" *`").lower() for b in bullets(sec)]


def ep_match(path: str, ep_path: str, loose: bool = False) -> bool:
    """Same endpoint? A fixed segment matches only the same fixed segment; a variable ({id}, {*}) matches only a
    variable — `/market/{symbol}` does NOT document `/market/hours`. loose=True lets a concrete value in an AC
    (`/payments/7/receipt`) match a variable in the code (`/payments/{id}/receipt`)."""
    v = lambda x: x.startswith("{") and x.endswith("}")
    a = path.rstrip("/").split("/")
    b = ep_path.rstrip("/").split("/")
    return len(a) == len(b) and all(x == y or (v(x) and v(y)) or (loose and v(y)) for x, y in zip(a, b))


def endpoints_at(repo: Path, ref: str, svc: str):
    """{(verb, normalised path): fingerprint} of a service's endpoints at a git ref (impact/depmap, from git blobs)."""
    sys.path.insert(0, str(ROOT / "impact"))
    import contextlib
    import io
    import depmap  # noqa: E402
    with contextlib.redirect_stderr(io.StringIO()):
        dm = depmap.build(Path(repo), None, ref)
    u = dm["services"].get(svc) or {}
    return {(p["verb"], re.sub(r"\{[^}]*\}", "{*}", p["path"])): p.get("fp") for p in u.get("provides", [])}


def git_ok_ref(repo, ref) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=repo,
                          capture_output=True).returncode == 0


def changed_lines(repo, base):
    """{file: set(new line numbers)} added/changed between merge-base(base, HEAD) and HEAD."""
    out, cur = {}, None
    diff = subprocess.run(["git", "diff", "-U0", f"{base}...HEAD"], cwd=repo, capture_output=True, text=True).stdout
    for l in diff.splitlines():
        if l.startswith("+++ "):
            cur = l[6:] if l != "+++ /dev/null" else None
            if cur:
                out.setdefault(cur, set())
        elif l.startswith("@@") and cur:
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", l)
            n, c = int(m.group(1)), int(m.group(2) or 1)
            out[cur].update(range(n, n + c))
    return out


def gh(*args):
    """gh CLI (JSON). Returns None when gh is missing or fails — callers SKIP with that reason."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def without_out_of_scope(text: str) -> str:
    """Text minus its own 'Out of Scope' section(s): naming a §18 item THERE is correct, not a violation."""
    lines, out, skip = text.splitlines(), [], None
    for l in lines:
        s = l.strip().strip("`")
        if re.match(r"#+\s", s):
            skip = len(s) - len(s.lstrip("#")) if "out of scope" in s.lower() else (None if skip is None or len(s) - len(s.lstrip("#")) <= skip else skip)
            if skip is not None and "out of scope" in s.lower():
                continue
        if skip is None and not re.match(r"\s*OUT OF SCOPE\b", s):
            out.append(l)
    return "\n".join(out)


def section18_hits(text: str, oos):
    hits = []
    low = without_out_of_scope(text).lower()
    for item in oos:
        words = [w for w in re.findall(r"[a-z]+", item) if len(w) > 3]
        if words and item and item in low:
            hits.append(item)
    return hits
