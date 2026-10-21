#!/usr/bin/env python3
"""Which other deployable units does a change affect, and what must the reviewer see? Deterministic; no LLM.

  impact.py --base-dir OLD --head-dir NEW [--json out.json] [--bundle out.md] [--cache DIR]
  impact.py --repo R --base origin/develop [--head HEAD] ...     (git mode)

Diffs the dependency maps (depmap.py) of both trees at CONTRACT level, then filters by the KEYS that changed
(field names, JSON/Map keys, headers, literals) so a unit is only reported when it uses what changed:

  provider side   an endpoint/producer contract changed  -> its callers/consumers that use a changed key
                  (all of them when the change has no key-level detail, e.g. a type annotation)
                  an endpoint/topic disappeared          -> BREAKING for every remaining caller/consumer
  consumer side   a call/listener changed                -> the provider, if it references the changed keys,
                                                            or if the call now targets a different endpoint
  other files     a changed file in no contract          -> connected units that use a changed key
  config          server.port / app name changed         -> units holding host:port references to it
  gateway         a route changed                        -> the target service and callers of the old prefix
  db, build       migrations of a schema others read; internal Maven modules and their dependents
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import depmap
import layout  # noqa: E402

COMMON = {"get", "set", "put", "add", "of", "build", "builder", "stream", "map", "filter", "collect", "toString",
          "equals", "hashCode", "debug", "info", "warn", "error", "trace", "log", "value", "data", "id", "type",
          "name", "list", "size", "length", "then", "catch", "push", "join", "split", "trim", "format", "orElse",
          "isEmpty", "ok", "status", "body", "result", "response", "request", "this", "true", "false", "null",
          "return", "new", "public", "private", "final", "static", "void", "String", "Integer", "Long", "class",
          "import", "package", "length", "message", "event", "payload", "e", "ex", "key", "toList", "forEach",
          "const", "let", "var", "await", "async", "function", "props", "state"}
TOKEN_LIT = re.compile(r"\"([^\"\n]*)\"|'([^'\n]*)'|`([^`\n]*)`")
MEMBER = re.compile(r"\.(\w+)\b")
OBJKEY = re.compile(r"(?:^|[{,\s])(\w+)\??\s*:(?!:)")
DECL = re.compile(r"[\w>\]]\s+(\w+)\s*(?:;|=(?!=)|,|\))")
BUILDER = re.compile(r"\.(\w+)\s*\(")
GETTER = re.compile(r"\b(?:get|is|set)([A-Z]\w*)\s*\(")
PORT = re.compile(r"^\s*port\s*:\s*(\d+)", re.M)


def files_of(root: Path):
    out = {}
    for f in root.rglob("*"):
        rel = f.relative_to(root)
        if f.is_file() and not f.is_symlink() and not ({".git", "node_modules", "target", "dist"} & set(rel.parts)):
            out[rel.as_posix()] = f
    return out


def changed_files(base: Path, head: Path):
    a, b = files_of(base), files_of(head)
    return [p for p in sorted(set(a) | set(b))
            if p not in a or p not in b or a[p].read_bytes() != b[p].read_bytes()]


ENUMCONST = re.compile(r"^\s*([A-Z][A-Z0-9_]+)\s*(?:[,;]|\(|$)")
CONSTUSE = re.compile(r"\.([A-Z][A-Z0-9_]+)\b|\bcase\s+([A-Z][A-Z0-9_]+)\b")
ANNOT = re.compile(r"@(RequestParam|RequestHeader|JsonProperty|JsonAlias|PathVariable|SerializedName|CookieValue)\s*"
                   r"(?:\(\s*(?:(?:value|name)\s*=\s*)?\"([^\"]+)\"[^)]*\)|\([^)]*\))?\s*"
                   r"(?:(?:private|protected|public|final)\s+)*[\w<>\[\]?.]+\s+(\w+)")
READ = [re.compile(r"\.get(?:OrDefault)?\(\s*\"(\w+)\""), re.compile(r"\b(?:get|is)([A-Z]\w*)\(\s*\)"),
        re.compile(r"\.(\w+)\b(?!\s*\()"), re.compile(r"\.(\w+)\(\s*\)"), re.compile(r"\[\s*['\"](\w+)['\"]\s*\]"),
        re.compile(r"\"([A-Z][A-Z0-9_]+)\"")]


def _keep(t, allow_upper=False):
    return len(t) >= 2 and t not in COMMON and not t.isdigit() and (allow_upper or not t.isupper()) and \
        (len(t) >= 3 or allow_upper)


def strip_comment(line):
    """Drop a trailing // comment that is not inside a string literal."""
    q = False
    for i, c in enumerate(line):
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            q = not q
        elif not q and line.startswith("//", i):
            return line[:i]
    return line


def drop_moves(base: Path, head: Path, ch):
    """A file deleted at one path and added with identical content at another moved; it did not change."""
    import hashlib
    gone = {f for f in ch if (base / f).is_file() and not (head / f).is_file()}
    new = {f for f in ch if (head / f).is_file() and not (base / f).is_file()}
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    by_hash = {}
    for f in new:
        by_hash.setdefault(h(head / f), []).append(f)
    moved = set()
    for f in gone:
        k = h(base / f)
        if by_hash.get(k):
            moved |= {f, by_hash[k].pop()}
    return [f for f in ch if f not in moved]


def tokens(lines, literals_only=False, in_enum=False):
    out, vals = set(), set()
    lines = [strip_comment(x) for x in lines]
    for line in lines:
        s = line.strip()
        if s.startswith(("//", "*", "/*", "#", "import ", "package ")) or re.match(r"\s*log(ger)?\.\w+\(", s):
            continue
        for m in TOKEN_LIT.finditer(line):
            lit = next(g for g in m.groups() if g is not None)
            if re.fullmatch(r"[A-Za-z][\w.\-/{}$:]{1,80}", lit) and " " not in lit:
                (vals if lit.isupper() else out).add(lit)
        for m in ANNOT.finditer(line):
            out.add(m.group(2) or m.group(3))
        if literals_only:
            continue
        for rx in (MEMBER, OBJKEY, DECL, BUILDER):
            out |= set(rx.findall(line))
        out |= {g[:1].lower() + g[1:] for g in GETTER.findall(line)}
        vals |= {a or b for a, b in CONSTUSE.findall(line)}
        if in_enum:
            vals |= set(ENUMCONST.findall(line))
    return {t for t in out if _keep(t)} | {v for v in vals if _keep(v, True) and len(v) >= 2}


def read_tokens(lines):
    """Keys a line READS: Map.get("k"), getK(), obj.k, accessor k(), ["k"], "CONST" comparisons."""
    out = set()
    for line in map(strip_comment, lines):
        s = line.strip()
        if s.startswith(("//", "*", "/*", "import ")) or re.match(r"\s*log(ger)?\.\w+\(", s):
            continue
        for rx in READ:
            for g in rx.findall(line):
                g = g[:1].lower() + g[1:] if rx is READ[1] else g
                out.add(g)
    return {t for t in out if _keep(t, t.isupper())}


TYPED = re.compile(r"([\w<>\[\]?.]+)\s+(\w+)\s*[;=,)]")


SILENT = "__json_unchanged__"
VALUE = [re.compile(r"\.(\w+)\s*\("), re.compile(r"(?!x)x"), re.compile(r"target\s*=\s*\"(\w+)\""),
         re.compile(r"[\"'](\w+)[\"']"), re.compile(r"^\s*(?:[\w<>\[\]?.]+\s+)+(\w+)\s*[;=]")]
JSONPROP = re.compile(r"@JsonProperty\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"[^)]*\)\s*(?:@[\w.]+(?:\([^)]*\))?\s*)*"
                      r"(?:(?:private|protected|public|final)\s+)*[\w<>\[\]?.]+\s+(\w+)")


def value_tokens(line):
    out = set()
    for i, rx in enumerate(VALUE):
        for g in rx.findall(line):
            out.add(g[:1].lower() + g[1:] if i == 1 else g)
    return {t for t in out if _keep(t)}


def json_names(text):
    """field name -> JSON name for fields annotated with @JsonProperty."""
    return {f: j for j, f in JSONPROP.findall(text)}


def annotated_targets(lines, idx_list):
    """Fields (or all fields of a class) that annotation-only lines at these indexes attach to."""
    out = set()
    text = "\n".join(lines)
    for i in idx_list:
        if not re.match(r"\s*@", lines[i]):
            continue
        j = i + 1
        while j < len(lines) and (re.match(r"\s*@", lines[j]) or not lines[j].strip()):
            j += 1
        if j >= len(lines):
            continue
        m = re.match(r"\s*(?:(?:private|protected|public|final|static)\s+)*[\w<>\[\]?.]+\s+(\w+)\s*[;=]", lines[j])
        if m:
            out.add(m.group(1))
        elif re.search(r"\b(class|record)\s+\w+", lines[j]):
            for t, n in re.findall(r"^[ \t]*(?:(?:private|protected|public|final)\s+)*([\w<>\[\]?.]+)\s+(\w+)\s*;", text, re.M):
                out.add(n)
            for comps in re.findall(r"\brecord\s+\w+\s*\(([^)]*)\)", text, re.S):
                out |= {c.strip().split()[-1] for c in comps.split(",") if c.strip()}
    return {t for t in out if _keep(t)}


def file_keys(base: Path, head: Path, rel: str):
    """Keys whose usage or VALUE changed in this file. Returns (removed literal/constant keys, all keys, read keys).
    - tokens on removed vs added lines, compared symmetrically (literals and identifiers separately)
    - a declaration whose type changed, or whose producing expression changed (builder .x(...), getX() mapping,
      @Mapping(target="x")) yields x: the key stays, its value format changes
    - annotation lines added/removed (@JsonFormat, @JsonInclude, ...) yield the field they attach to, or every field
      of the class for a class-level annotation
    - a field with @JsonProperty("j") is reported as j (its JSON name), so renaming the Java field alone is silent"""
    a_text = (base / rel).read_text(errors="replace") if (base / rel).exists() else ""
    b_text = (head / rel).read_text(errors="replace") if (head / rel).exists() else ""
    a, b = a_text.splitlines(), b_text.splitlines()
    in_enum = bool(re.search(r"\benum\s+\w+", a_text + b_text))
    rem, add, value, ann = [], [], set(), set()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            rem += a[i1:i2]
            ann |= annotated_targets(a, range(i1, i2))
        if op in ("replace", "insert"):
            add += b[j1:j2]
            ann |= annotated_targets(b, range(j1, j2))
        if op == "replace":
            for x, y in zip(map(strip_comment, a[i1:i2]), map(strip_comment, b[j1:j2])):
                if x.strip() != y.strip() and not re.match(r"\s*(//|\*|log)", x.strip()):
                    value |= value_tokens(x) & value_tokens(y)
    tr, ta = tokens(rem, in_enum=in_enum), tokens(add, in_enum=in_enum)
    lr, la = tokens(rem, True), tokens(add, True)
    ident = tr ^ ta
    lit = lr ^ la
    removed = (lr - la) | {t for t in tr - ta if t.isupper()}
    trd = {n: t for line in rem for t, n in TYPED.findall(line)}
    tad = {n: t for line in add for t, n in TYPED.findall(line)}
    typechg = {n for n in set(trd) & set(tad) if trd[n] != tad[n] and n not in COMMON}
    reads = read_tokens(rem) ^ read_tokens(add)
    allk = lit | ident | typechg | value | ann
    ja, jb = json_names(a_text), json_names(b_text)
    if ja or jb:   # translate Java field names to their JSON names; a rename that keeps the JSON name is silent
        mapped = set()
        for k in allk:
            if k in ja or k in jb:
                mapped |= {ja.get(k, k) if k in ja else None, jb.get(k, k) if k in jb else None} - {None}
            else:
                mapped.add(k)
        if ja and jb and set(ja.values()) == set(jb.values()):
            mapped -= set(ja.values()) - (lit & set(ja.values()))
        allk = mapped or {SILENT}   # only Java names changed; the JSON contract did not
    return removed, allk, reads, value - {SILENT}


def key_regex(keys, reads_only=False):
    alts = "|".join(map(re.escape, sorted(keys, key=len, reverse=True)))
    caps = "|".join(re.escape(k[:1].upper() + k[1:]) for k in keys if re.fullmatch(r"\w+", k))
    if reads_only:   # a unit that only DECLARES or WRITES a key does not depend on it
        pat = (rf"[\"'`]({alts})[\"'`]|\.({alts})\b(?!\s*\((?!\s*\)))|\bcase\s+({alts})\b|[{{,]\s*({alts})\s*[}},]"
               rf"|\b({alts})\s*\??\s*:")
        if caps:
            pat += rf"|\b(?:get|is)({caps})\s*\(\s*\)"
        return re.compile(pat)
    pat = rf"[\"'`]({alts})[\"'`]|\.({alts})\b|\b({alts})\s*\??\s*[:;=,)]|\bcase\s+({alts})\b"
    if caps:
        pat += rf"|\b(?:get|is|set)({caps})\s*\("
    return re.compile(pat)


def declared(root: Path, files, keys):
    """Keys declared as fields/record components in these files (deserialisation targets such as response DTOs)."""
    out = set()
    rx = re.compile(r"[\w>\]]\s+(" + "|".join(map(re.escape, keys)) + r")\s*[;,)=]")
    for rel in files:
        p = root / rel
        if p.is_file() and rel.endswith(".java"):
            out |= set(rx.findall(p.read_text(errors="replace")))
    return out


def evidence(root: Path, files, keys, limit=6, reads_only=False, unit_files=None):
    """Lines in `files` that use a key. reads_only: only reads count, except that a key DECLARED in a DTO in
    `files` counts when the unit reads it anywhere (getK(), .k(), obj.k) — Jackson fills DTO fields by name."""
    if not keys:
        return []
    if reads_only and unit_files:
        dec = declared(root, files, keys)
        if dec:
            hits = evidence(root, unit_files, dec, limit, True)
            if hits:
                return hits
    rx = key_regex(keys, reads_only)
    out = []
    for rel in sorted(set(files)):
        p = root / rel
        if not p.is_file():
            continue
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if rx.search(line) and not line.strip().startswith(("//", "*", "import ")):
                out.append(f"{rel}:{i}: {line.strip()[:150]}")
                if len(out) >= limit:
                    return out
    return out


def unit_source(root: Path, dm, unit):
    u = dm["services"].get(unit)
    if not u:
        return []
    base = root / u["path"]
    return [f.relative_to(root).as_posix() for f in depmap.unit_files(
        base, {".java", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml", ".properties", ".conf"})
        if "package-lock" not in f.name]


def grep_units(root: Path, dm, literals, exclude=None, limit=4):
    """Units whose source contains one of these exact literals (git grep when available: fast on huge repos)."""
    out = {}
    pats = sorted(literals)
    files = []
    try:
        args = ["git", "-C", str(root), "grep", "-n", "-F"] + [x for p in pats for x in ("-e", p)]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode in (0, 1) and (root / ".git").exists():
            files = [ln.split(":", 2) for ln in r.stdout.splitlines()]
    except FileNotFoundError:
        pass
    if not files:
        for name, u in dm["services"].items():
            for rel in unit_source(root, dm, name):
                for i, line in enumerate((root / rel).read_text(errors="replace").splitlines(), 1):
                    if any(p in line for p in pats):
                        files.append([rel, str(i), line])
    for rel, ln, text in files:
        v = unit_of(dm, rel)
        if v and v != exclude and "/src/test/" not in rel:
            if len(out.setdefault(v, [])) < limit:
                out[v].append(f"{rel}:{ln}: {text.strip()[:150]}")
    return out


def unit_of(dm, rel):
    for name, u in dm["services"].items():
        if rel.startswith(u["path"] + "/"):
            return name
    return None


def changed_lines(base: Path, head: Path, rel: str):
    a = (base / rel).read_text(errors="replace").splitlines() if (base / rel).exists() else []
    b = (head / rel).read_text(errors="replace").splitlines() if (head / rel).exists() else []
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out += list(range(j1 + 1, max(j2, j1 + 1) + 1))
    return out


def ts_imports(head: Path, rel: str, depth=2):
    """A frontend file plus the local modules it imports (to find which APIs a page uses)."""
    seen, frontier = {rel}, [rel]
    for _ in range(depth):
        nxt = []
        for f in frontier:
            p = head / f
            if not p.exists():
                continue
            for imp in re.findall(r"from\s+['\"](\.{1,2}/[^'\"]+)['\"]", p.read_text(errors="replace")):
                for ext in ("", ".ts", ".tsx", ".js", "/index.ts", "/index.tsx"):
                    q = (p.parent / (imp + ext)).resolve()
                    if q.is_file():
                        r = q.relative_to(head.resolve()).as_posix()
                        if r not in seen:
                            seen.add(r)
                            nxt.append(r)
                        break
        frontier = nxt
    return seen


def path_owner(dm, path):
    """Service owning the longest provided-path prefix of `path` (at least 3 segments), else a gateway route."""
    segs = path.strip("/").split("/")
    best, owner = 0, None
    for u in dm["services"].values():
        for p in u["provides"]:
            ps = p["path"].strip("/").split("/")
            n = 0
            for a, b in zip(segs, ps):
                if a != b and "{*}" not in (a, b):
                    break
                n += 1
            if n >= 3 and n > best:
                best, owner = n, p["service"]
        for c in u["calls"]:
            if c.get("prefix") and (path + "/").startswith(c["path"] + "/") and not owner:
                owner = c["host"] if c["host"] in dm["services"] else None
    return owner


class Impact:
    def __init__(self, base: Path, head: Path, cache=None, B=None, H=None, ch=None):
        self.base, self.head = base, head
        self.B = B or depmap.build(base, cache)
        self.H = H or depmap.build(head, cache)
        self.ch = drop_moves(base, head, ch if ch is not None else changed_files(base, head))
        self.chset = set(self.ch)
        fk = {f: file_keys(base, head, f) for f in self.ch}
        self.keys = {f: k[1] for f, k in fk.items()}
        self.removed_lits = {f: k[0] for f, k in fk.items()}
        self.read_keys = {f: k[2] for f, k in fk.items()}
        self.value_keys = {f: k[3] for f, k in fk.items()}
        self.explained = {}
        self.enum_fields()
        self.affected, self.breaking = {}, set()
        self.covered = set()   # changed files explained by a contract rule

    def enum_fields(self):
        """An enum constant rename affects every unit reading a field of that enum type: add those field names."""
        for f in self.ch:
            consts = {k for k in self.keys.get(f, set()) if k.isupper()}
            p = self.head / f if (self.head / f).exists() else self.base / f
            if not consts or not f.endswith(".java"):
                continue
            m = re.search(r"\benum\s+(\w+)", p.read_text(errors="replace"))
            u = unit_of(self.H, f)
            if not m or not u:
                continue
            names = set()
            for g in unit_source(self.head, self.H, u):
                if g.endswith(".java"):
                    names |= set(re.findall(rf"\b{m.group(1)}\s+(\w+)\s*[;=,)]", (self.head / g).read_text(errors="replace")))
            names = {n for n in names if n not in COMMON}
            self.keys[f] |= names
            self.removed_lits[f] |= names

    def emitted(self, u):
        """Field names this unit sends to others: fields declared in its response DTOs and event payloads."""
        if not hasattr(self, "_emitted"):
            self._emitted = {}
        if u not in self._emitted:
            files = set()
            us = self.H["services"].get(u, {})
            for p in us.get("provides", []):
                files |= set(p["contract"]) - {p["file"]} - set(p.get("request_files", []))
            for k in us.get("kafka", []):
                if k["role"] == "producer":
                    files |= set(k["contract"]) - {k["file"]}
            names = set()
            for rel in files:
                fp = self.head / rel
                if fp.is_file():
                    t = fp.read_text(errors="replace")
                    names |= {n for _t, n in depmap.FIELD.findall(t)}
                    for comps in depmap.RECORD.findall(t):
                        names |= {c.strip().split()[-1] for c in comps.split(",") if c.strip()}
            self._emitted[u] = names
        return self._emitted[u]

    def hit(self, unit, reason, files=(), ev=()):
        if unit:
            self.affected.setdefault(unit, []).append({"reason": reason, "files": sorted(set(files)),
                                                       "evidence": list(ev)})

    def keys_of(self, files):
        out = set()
        for f in files:
            out |= self.keys.get(f, set())
        return out

    # ── provider/producer contracts ──
    def kafka(self):
        B, H = self.B, self.H
        for topic in sorted(set(B["topics"]) | set(H["topics"])):
            bt = B["topics"].get(topic, {"producers": [], "consumers": []})
            ht = H["topics"].get(topic, {"producers": [], "consumers": []})
            bp = {(p["service"], p["fp"]): p for p in bt["producers"]}
            hp = {(p["service"], p["fp"]): p for p in ht["producers"]}
            for key in set(bp) ^ set(hp):
                prod = hp.get(key) or bp.get(key)
                svc = prod["service"]
                files = [f for p in [bp.get(key), hp.get(key)] if p for f in p["contract"]]
                self.covered |= self.chset & set(files)
                gone = key in bp and not any(s == svc for s, _ in hp)
                keys = self.keys_of(files)
                self.explained.setdefault(svc, set()).update(keys)
                for c in {c["service"]: c for c in bt["consumers"] + ht["consumers"]}.values():
                    if c["service"] == svc:
                        continue
                    cons = [x for x in ht["consumers"] + bt["consumers"] if x["service"] == c["service"]]
                    scope = {f for x in cons for f in x["contract"] + x.get("weak", [])}
                    if gone and ht["consumers"] and not ht["producers"]:
                        self.breaking.add(f"topic `{topic}` lost its producer ({svc}); {c['service']} still consumes it")
                        self.hit(c["service"], f"consumes `{topic}`, which {svc} no longer produces", scope)
                        continue
                    ev = evidence(self.head, scope, keys, reads_only=True,
                                  unit_files=unit_source(self.head, self.H, c["service"]))
                    if not keys or ev:
                        self.hit(c["service"], f"consumes `{topic}`; {svc} changed the payload contract"
                                 + (f" (keys: {', '.join(sorted(keys))[:120]})" if keys else " (no key-level detail)"),
                                 scope | set(files), ev)
            # consumer side
            bc = {(c["service"], c["fp"]): c for c in bt["consumers"]}
            hc = {(c["service"], c["fp"]): c for c in ht["consumers"]}
            for key in set(bc) ^ set(hc):
                cons = hc.get(key) or bc.get(key)
                svc = cons["service"]
                files = [f for c in [bc.get(key), hc.get(key)] if c for f in c["contract"] + c.get("weak", [])]
                self.covered |= self.chset & set(files)
                keys = set().union(*[self.read_keys.get(f, set()) for f in files]) if files else set()
                for p in {p["service"] for p in ht["producers"] or bt["producers"]} - {svc}:
                    ev = evidence(self.head, unit_source(self.head, H, p), keys)
                    new_topic = key in hc and not any(s == svc for s, _ in bc)
                    if ev or new_topic:
                        self.hit(p, f"produces `{topic}`; consumer {svc} changed what it reads"
                                 + (f" (keys: {', '.join(sorted(keys))[:120]})" if keys else ""), files, ev)
                if key in hc and not ht["producers"] and not any(s == svc for s, _ in bc):
                    self.breaking.add(f"{svc} now consumes `{topic}`, which nobody produces")

    def rest(self):
        B, H = self.B, self.H
        bep = {depmap.ep_key(p): p for u in B["services"].values() for p in u["provides"]}
        hep = {depmap.ep_key(p): p for u in H["services"].values() for p in u["provides"]}
        changed = {k for k in set(bep) | set(hep) if (bep.get(k) or {}).get("fp") != (hep.get(k) or {}).get("fp")}
        for k in changed:
            for p in (bep.get(k), hep.get(k)):
                if p:
                    self.covered |= self.chset & set(p["contract"])
        # provider side: callers of a changed/removed endpoint
        for e in B["rest_edges"] + H["rest_edges"]:
            if e["kind"] != "rest" or not e.get("to"):
                continue
            hit_eps = set(e["endpoints"]) & changed
            if not hit_eps:
                continue
            files = [f for k in hit_eps for p in (bep.get(k), hep.get(k)) if p for f in p["contract"]]
            keys = self.keys_of(files)
            self.explained.setdefault(e["to"], set()).update(keys)
            verb = e["call"].get("verb")   # GET -> POST on the same path is a removal for a GET caller
            still = [p for p in hep.values() if p["service"] == e["to"] and depmap.seg_match(e["path"], p["path"])
                     and (not verb or p["verb"] in (verb, "ANY"))]
            caller = e["from"]
            if caller not in H["services"]:
                continue
            if not still:
                self.breaking.add(f"{caller} calls `{e['path']}` on {e['to']}, which no longer exists "
                                  f"({e['call']['file']}:{e['call']['line']})")
                self.hit(caller, f"calls {e['to']} `{e['path']}`, which was removed or moved", [e["call"]["file"]] + files,
                         [f"{e['call']['file']}:{e['call']['line']}"])
                continue
            if e["confidence"] in ("ambiguous", "suspect") and not (hit_eps & {depmap.ep_key(p) for p in still}):
                continue
            req = {f for k in hit_eps for p in (bep.get(k), hep.get(k)) if p for f in p.get("request_files", [])}
            req_keys = self.keys_of(req & self.chset) - {SILENT}
            if req_keys:   # the request body contract changed: every caller sends that body
                self.hit(caller, f"calls {e['to']} `{e['path']}` ({e['call']['file']}:{e['call']['line']}); the request "
                         f"body it sends changed (keys: {', '.join(sorted(req_keys))[:120]})", [e["call"]["file"]] + sorted(req),
                         [f"{e['call']['file']}:{e['call']['line']}"])
                continue
            scope = set(e["call"]["contract"]) | set(e["call"].get("weak", []))
            if H["services"][caller]["kind"] == "frontend":
                scope |= set(unit_source(self.head, H, caller))
            ev = evidence(self.head, scope, keys, reads_only=True, unit_files=unit_source(self.head, H, caller))
            if not keys or ev:
                self.hit(caller, f"calls {e['to']} `{e['path']}` ({e['call']['file']}:{e['call']['line']}); "
                         f"endpoint contract changed" + (f" (keys: {', '.join(sorted(keys))[:120]})" if keys else ""),
                         scope | set(files), ev)
        # caller side: a caller's call changed (Java client methods)
        bcalls = {(e["from"], e["call"]["fp"]): e for e in B["rest_edges"] if e["kind"] == "rest"}
        hcalls = {(e["from"], e["call"]["fp"]): e for e in H["rest_edges"] if e["kind"] == "rest"}
        for key in set(bcalls) ^ set(hcalls):
            e = hcalls.get(key) or bcalls.get(key)
            if H["services"].get(e["from"], {}).get("kind") == "frontend":
                continue   # frontend handled by import tracing below
            files = list(e["call"]["contract"]) + list(e["call"].get("weak", []))
            self.covered |= self.chset & set(files)
            if not e.get("to") or e["to"] == e["from"]:
                continue
            keys = self.keys_of(files)
            new_path = key in hcalls and e["path"] not in {x["path"] for (f, _), x in bcalls.items() if f == e["from"]}
            ev = evidence(self.head, unit_source(self.head, H, e["to"]), keys)
            if ev or new_path:
                self.hit(e["to"], f"{e['from']} changed its call to `{e['path']}` ({e['call']['file']}:{e['call']['line']})"
                         + (f" (keys: {', '.join(sorted(keys))[:120]})" if keys else ""), files, ev)

    def frontend(self):
        H, B = self.H, self.B
        for name, u in H["services"].items():
            if u["kind"] != "frontend":
                continue
            changed = [f for f in self.ch if f.startswith(u["path"] + "/")]
            if not changed:
                continue
            bpaths = {c["path"] for c in B["services"].get(name, {}).get("calls", [])}
            for f in changed:
                reach = ts_imports(self.head, f) | ts_imports(self.base, f)
                edges = [e for e in H["rest_edges"] + B["rest_edges"] if e["from"] == name and e.get("to")
                         and e["call"]["file"] in reach]
                lines = changed_lines(self.base, self.head, f)
                near = [e for e in edges if e["call"]["file"] == f and any(abs(e["call"]["line"] - ln) <= 12 for ln in lines)]
                if near:   # the edit sits next to specific API calls: those are the providers it concerns
                    edges = near
                keys = self.keys.get(f, set())
                self.covered.add(f)
                # new calls that resolve to no endpoint: the owning service by route/path prefix
                for c in H["services"][name]["calls"]:
                    if c["file"] == f and c["path"] not in bpaths:
                        if any(e.get("to") and (e["call"] is c or e["call"]["fp"] == c["fp"]) for e in H["rest_edges"]):
                            continue
                        owner = path_owner(H, c["path"])
                        if owner:
                            self.breaking.add(f"{name} calls `{c['path']}`, which {owner} does not provide ({f}:{c['line']})")
                            self.hit(owner, f"{name} now calls `{c['path']}` on {owner}, which has no such endpoint",
                                     [f], [f"{f}:{c['line']}"])
                for to in sorted({e["to"] for e in edges}):
                    es = [e for e in edges if e["to"] == to]
                    new_path = any(e["path"] not in bpaths and e["call"]["file"] == f for e in es)
                    ev = evidence(self.head, unit_source(self.head, H, to), keys)
                    if ev or new_path:
                        self.hit(to, f"{name} changed how it uses {to} ({f})"
                                 + (f" (keys: {', '.join(sorted(keys))[:120]})" if keys else ""),
                                 [e["call"]["file"] for e in es], ev)

    def gateway_and_config(self):
        B, H = self.B, self.H
        broutes = {(c["caller"], c["host"], c["path"]): c for u in B["services"].values() for c in u["calls"] if c.get("prefix")}
        hroutes = {(c["caller"], c["host"], c["path"]): c for u in H["services"].values() for c in u["calls"] if c.get("prefix")}
        for k in set(broutes) ^ set(hroutes):
            c = broutes.get(k) or hroutes.get(k)
            self.covered |= self.chset & set(c["contract"])
            gw, host, prefix = k
            if host in H["services"]:
                self.hit(host, f"gateway {gw} route for `{prefix}` changed", c["contract"])
            if k in broutes and k not in hroutes:
                for u in H["services"].values():
                    direct = u["kind"] == "service" and any(r["unit"] == u["name"] and r["to"] == host for r in H["url_edges"])
                    if u["name"] in (gw, host) or direct:
                        continue
                    callers = [x for x in u["calls"] if not x.get("prefix") and (x["path"] + "/").startswith(prefix + "/")]
                    if callers and not any((x["path"] + "/").startswith(p + "/") for (_, _, p) in hroutes for x in callers):
                        self.breaking.add(f"gateway no longer routes `{prefix}`; {u['name']} still calls it")
                        self.hit(u["name"], f"calls `{prefix}/**` through gateway {gw}; that route changed",
                                 [x["file"] for x in callers], [f"{x['file']}:{x['line']}" for x in callers[:5]])
        for name in set(B["services"]) - set(H["services"]):   # a removed service: who still points at it
            for r in B["url_edges"]:
                if r["to"] == name and r["unit"] in H["services"]:
                    self.hit(r["unit"], f"references {name} at {r['host']}:{r['port']}, which was removed",
                             [r["file"]], [f"{r['file']}:{r['line']}"])
        for (gw, host, prefix), c in hroutes.items():
            if host in B["services"] and host not in H["services"]:
                self.breaking.add(f"gateway {gw} still routes `{prefix}` to {host}, which no longer exists ({c['file']}:{c['line']})")
                self.hit(gw, f"routes `{prefix}` to {host}, which was removed", c["contract"], [f"{c['file']}:{c['line']}"])
        # server.port / application name changes -> host:port references
        for name, u in B["services"].items():
            h = H["services"].get(name)
            if not h or u["kind"] != "service":
                continue
            if u.get("port") != h.get("port") or u.get("app_name") != h.get("app_name"):
                for f in self.ch:
                    if f.startswith(u["path"] + "/src/main/resources/"):
                        self.covered.add(f)
                for r in B["url_edges"]:
                    if r["to"] == name and r["unit"] != name:
                        old_port = r["port"] == u.get("port")
                        if (u.get("port") != h.get("port") and old_port) or u.get("app_name") != h.get("app_name"):
                            self.hit(r["unit"], f"references {name} at {r['host']}:{r['port']}; {name}'s "
                                     f"{'port' if u.get('port') != h.get('port') else 'name'} changed",
                                     [r["file"]], [f"{r['file']}:{r['line']}"])

    def db_and_build(self):
        H = self.H
        for name, u in H["services"].items():
            if any(f.startswith(u["path"] + "/") and "/db/migration/" in f for f in self.ch):
                for other in H["services"].values():
                    for q in other["foreign_sql"]:
                        if q["owner"] == name:
                            self.hit(other["name"], f"reads {q['schema']} (owned by {name}, whose migrations changed)",
                                     [q["file"]], [f"{q['file']}:{q['line']}"])
        mods = H["modules"]
        dirs = {v["dir"]: m for m, v in mods.items()}
        changed_mods = set()
        for f in self.ch:
            parts = f.split("/")
            for i in range(len(parts) - 1, -1, -1):
                d = "/".join(parts[:i]) or "."
                if d in dirs:
                    if d != "." or f == "pom.xml":
                        changed_mods.add(dirs[d])
                    break
        self.global_change = "pom.xml" in self.chset
        lib_changes = {m for m in changed_mods if mods[m]["dir"] != "." and not unit_of(H, mods[m]["dir"] + "/x")}
        frontier, dependents = set(lib_changes), set()
        while frontier:
            nxt = {m for m, v in mods.items() if set(v["deps"]) & frontier and m not in dependents}
            dependents |= nxt
            frontier = nxt
        for m in dependents:
            u = unit_of(H, mods[m]["dir"] + "/x")
            self.hit(u, f"depends on changed library module(s) {', '.join(sorted(lib_changes))}")
        if self.global_change:
            for u in H["services"]:
                self.hit(u, "root pom.xml changed (parent of every module)")

    def uncovered(self):
        """Keys a unit stops emitting (removed literals, enum constants, header/claim names) that no provider-side
        contract rule already explained: downstream units (topic consumers, Java callers, routed services, JWT
        verifiers) that still READ one of them are affected."""
        H = self.H
        for f in self.ch:
            u = unit_of(H, f) or unit_of(self.B, f)
            if not u or u not in H["services"] or H["services"][u].get("kind") == "frontend":
                continue   # a deleted unit is handled by the contract rules (lost topics, endpoints, routes, URLs)
            vkeys = (self.value_keys.get(f, set()) & self.emitted(u)) - self.explained.get(u, set())
            keys = (self.removed_lits.get(f, set()) | vkeys) - self.explained.get(u, set())
            if not keys:
                continue
            neighbours = {}
            for t in H["topics"].values():
                if any(p["service"] == u for p in t["producers"]):
                    for c in t["consumers"]:
                        neighbours.setdefault(c["service"], set()).update(c["contract"] + c.get("weak", []))
            for e in H["rest_edges"]:
                if e.get("to") == u and e["from"] != u:
                    neighbours.setdefault(e["from"], set()).update(set(e["call"]["contract"]) | set(e["call"].get("weak", [])))
                if e["kind"] == "route" and e["from"] == u and e.get("to"):   # a gateway's routed services
                    neighbours.setdefault(e["to"], set()).update(unit_source(self.head, H, e["to"]))
            values = {k for k in keys if k.isupper()} | vkeys
            if values:   # enum values / reformatted fields reach the frontend through any response
                for v, uu in H["services"].items():
                    if uu["kind"] == "frontend" and any(e["from"] == v and e.get("to") == u for e in H["rest_edges"]):
                        neighbours.setdefault(v, set()).update(unit_source(self.head, H, v))
            if H["services"].get(u, {}).get("jwt", {}).get("issuer"):
                for v, uu in H["services"].items():
                    if v != u and uu.get("jwt", {}).get("verifier"):
                        neighbours.setdefault(v, set()).update(uu["jwt"]["verifier"])
            shared = {k for k in keys if re.search(r"[:/.\-]", k) and len(k) >= 6}
            if shared:   # namespaced literals (cache keys, queue names, URNs) are contracts even without an edge
                for v, hits in grep_units(self.head, H, shared, exclude=u).items():
                    self.hit(v, f"uses literal(s) {', '.join(sorted(shared))[:120]} that {u} changed in {f}", [f], hits)
            for v in neighbours:
                if v == u:
                    continue
                ev = evidence(self.head, neighbours[v], keys, reads_only=True, unit_files=unit_source(self.head, H, v))
                if ev:
                    self.hit(v, f"reads key(s) {', '.join(sorted(keys))[:120]} that {u} changed in {f}", [f], ev)

    def run(self):
        for d in self.H.get("duplicates", []):
            self.breaking.add(f"two services share the name {d} (spring.application.name must be unique)")
        self.kafka()
        self.rest()
        self.frontend()
        self.gateway_and_config()
        self.db_and_build()
        self.uncovered()
        changed_units = sorted({unit_of(self.H, f) or unit_of(self.B, f) for f in self.ch} - {None})
        for u in changed_units:
            if not self.global_change:
                self.affected.pop(u, None)
        return {"changed_files": self.ch, "changed_units": changed_units, "changed_services": changed_units,
                "affected": self.affected, "breaking": sorted(self.breaking), "global": self.global_change,
                "keys": {f: sorted(k)[:30] for f, k in self.keys.items() if k},
                "stats": {"units": len(self.H["services"]),
                          "depmap_scanned": self.H["stats"]["scanned"] + self.B["stats"]["scanned"],
                          "depmap_cached": self.H["stats"]["cached"] + self.B["stats"]["cached"]}}


def analyse(base: Path, head: Path, cache=None):
    return Impact(base, head, cache).run()


def analyse_git(repo: Path, base_ref: str, head_ref: str = "HEAD", cache=None):
    """Scalable mode: the working tree is at head_ref. Maps for both revisions come from git tree hashes + cache;
    only changed units are extracted, and only changed files are materialised from the base revision."""
    repo = repo.resolve()
    mb = subprocess.run(["git", "-C", str(repo), "merge-base", base_ref, head_ref], capture_output=True, text=True,
                        check=True).stdout.strip()
    ch = [l for l in subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "--no-renames", mb, head_ref],
                                    capture_output=True, text=True, check=True).stdout.splitlines() if l]
    H = depmap.build(repo, cache, head_ref)
    B = depmap.build(repo, cache, mb)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for f in ch:
            r = subprocess.run(["git", "-C", str(repo), "show", f"{mb}:{f}"], capture_output=True)
            if r.returncode == 0:
                (base / f).parent.mkdir(parents=True, exist_ok=True)
                (base / f).write_bytes(r.stdout)
        return Impact(base, repo, cache, B=B, H=H, ch=ch).run()


def bundle(res: dict, head: Path, budget: int = 60000, detail_units: int = 25) -> str:
    """Markdown for a critic. Large fan-outs are summarised: full detail for the first `detail_units` units
    (breaking first), names only for the rest; the JSON output always has everything."""
    md = ["# Impact of this change (deterministic, from impact.py)", "",
          f"Changed units: {', '.join(res['changed_units']) or '(none)'}",
          f"Affected units: {', '.join(sorted(res['affected'])) or '(none)'}"]
    if res["global"]:
        md.append("**Root build file changed: every module is affected.**")
    if res["breaking"]:
        md += ["", "## BREAKING"] + [f"- {b}" for b in res["breaking"]]
    files = []
    order = sorted(res["affected"], key=lambda u: (not any(u in b for b in res["breaking"]), u))
    rest = order[detail_units:]
    for unit in order[:detail_units]:
        reasons = res["affected"][unit]
        md += ["", f"## {unit}"]
        for r in reasons:
            md.append(f"- {r['reason']}")
            md += [f"  - uses it: `{ev}`" for ev in r["evidence"]]
            files += r["files"]
    if rest:
        md += ["", f"## {len(rest)} more affected units (same review question; details in impact.json)",
               ", ".join(rest)]
    md += ["", "## Counterpart files (read these against the diff)"]
    used = sum(len(x) for x in md)
    for f in sorted(set(files)):
        p = head / f
        if not p.is_file():
            md.append(f"- {f} (deleted in this change)")
            continue
        text = p.read_text(errors="replace")
        if used + len(text) > budget:
            md.append(f"- {f} (not inlined: context budget reached; read it from the repo)")
            continue
        used += len(text)
        md += [f"### {f}", "```", text.rstrip(), "```"]
    return "\n".join(md) + "\n"


def materialise(repo: Path, ref: str, dst: Path):
    dst.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(repo), "archive", ref], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dst)], input=tar, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir")
    ap.add_argument("--head-dir")
    ap.add_argument("--repo")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--json")
    ap.add_argument("--bundle")
    ap.add_argument("--cache")
    ap.add_argument("--config", help="trusted project.yaml for the unit layout (in CI: the base branch's copy)")
    ap.add_argument("--fail-on-breaking", action="store_true",
                    help="exit 1 when a counterpart is left pointing at something that no longer exists")
    a = ap.parse_args()
    if a.config:
        layout.TRUSTED_CONFIG = a.config
    cache = Path(a.cache) if a.cache else None
    if a.repo:
        res = analyse_git(Path(a.repo), a.base, a.head, cache)
        head = Path(a.repo).resolve()
    else:
        base, head = Path(a.base_dir).resolve(), Path(a.head_dir).resolve()
        res = analyse(base, head, cache)
    if a.bundle:
        Path(a.bundle).write_text(bundle(res, head))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    print(f"impact: changed {res['changed_units'] or '-'} -> affected {sorted(res['affected']) or '-'}"
          f"{' BREAKING: ' + str(len(res['breaking'])) if res['breaking'] else ''}")
    for b in res["breaking"]:
        print("  BREAKING", b)
    return 1 if (a.fail_on_breaking and res["breaking"]) else 0


if __name__ == "__main__":
    sys.exit(main())
