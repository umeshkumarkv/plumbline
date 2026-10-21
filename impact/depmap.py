#!/usr/bin/env python3
"""Deterministic service dependency map for a Java/Spring monorepo (+ a TypeScript frontend). No LLM involved.

  depmap.py <repo> [-o depmap.json] [--cache DIR]

Per deployable unit (services/<name>/, and any top-level folder with a package.json):
  kafka     producers (KafkaTemplate.send) and consumers (@KafkaListener). Contract = the sending/listening METHOD
            (not the whole file) + the payload class + every service-local type those reference (closure).
  provides  REST endpoints: mapping + method body + request/response types (incl. types only named in the body,
            for controllers that return Map/ResponseEntity<?>).
  calls     REST calls: "/api/..." literals incl. string concatenation ("/a/" + id + "/b"), TS template literals
            (`/a/${id}/b`), axios baseURL; gateway routes (Path=... -> uri host).
  urlrefs   host:port references in config/code (http://svc:8084, localhost:8084) -> which service they point at.
  schema    owned DB schema; SQL literals reading another service's schema.
  modules   internal Maven module dependencies.
Contract fingerprints let impact.py diff two maps. Per-unit results are cached by a content hash, so a PR only
re-extracts the units it changes.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout  # noqa: E402

VERSION = 8   # 8: layouts, comments stripped, TS constants, unresolved calls (7: verb from statement start)
SKIP = ("/src/test/", "/target/", "/node_modules/", "/e2e/", "/dist/", "/build/")
TYPE_DECL = re.compile(r"\b(?:class|record|interface|enum)\s+([A-Z]\w*)")
CONST = re.compile(r"static\s+final\s+String\s+([A-Z_][A-Z0-9_]*)\s*=\s*\"([^\"]+)\"")
SEND = re.compile(r"\b\w*[Tt]emplate\s*\.\s*send\s*\(")
LISTENER = re.compile(r"@KafkaListener\s*\(")
CTRL = re.compile(r"@(?:Rest)?Controller\b")
CLASS_MAP = re.compile(r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?\{?\s*\"([^\"]*)\"")
METHOD_MAP = re.compile(r"@(Get|Post|Put|Delete|Patch|Request)Mapping\b")
FIELD = re.compile(r"^[ \t]*(?:@\w+(?:\([^)\n]*\))?\s+)*(?:(?:private|protected|public|static|final|transient|volatile)\s+)*"
                   r"((?!return\b|throw\b|else\b|new\b)[A-Za-z_][\w<>\[\], ?.]*?)\s+(\w+)\s*(?:;|=(?!=))", re.M)
RECORD = re.compile(r"\brecord\s+\w+\s*\(([^)]*)\)", re.S)
CAP = re.compile(r"\b([A-Z]\w*)\b")
URLREF = re.compile(r"(?:https?|wss?)://([A-Za-z][\w.-]*):(\d{2,5})|\b(localhost|127\.0\.0\.1):(\d{2,5})")
JDK = {"String", "Integer", "Long", "Double", "Float", "Boolean", "Short", "Byte", "Character", "Object", "List",
       "Map", "Set", "Optional", "BigDecimal", "BigInteger", "UUID", "Instant", "LocalDate", "LocalDateTime",
       "OffsetDateTime", "ZonedDateTime", "Duration", "ResponseEntity", "Collection", "Void", "HashMap", "ArrayList",
       "Page", "Pageable", "Mono", "Flux", "ConsumerRecord", "Acknowledgment", "JsonNode", "Payload", "Valid",
       "RequestBody", "PathVariable", "RequestParam", "RequestHeader", "Header", "HttpServletRequest", "Authentication",
       "Principal", "MultipartFile", "SseEmitter", "T", "Override", "Transactional", "Collectors", "Math", "System",
       "Arrays", "Objects", "Stream", "RoundingMode", "HttpStatus", "HttpMethod", "HttpEntity", "HttpHeaders",
       "MediaType", "Exception", "RuntimeException", "IllegalArgumentException", "IllegalStateException", "Logger",
       "LoggerFactory", "LinkedHashMap", "TreeMap", "Comparator", "ChronoUnit", "ZoneId", "DateTimeFormatter",
       "KafkaTemplate", "ObjectMapper", "RestTemplate", "Value", "Slf4j", "Builder", "Data"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def norm_path(p: str) -> str:
    p = re.sub(r"\$\{[^}]*\}", "{*}", p)
    p = re.sub(r"\{[^}]*\}", "{*}", p)
    p = "/" + p.split("?")[0].strip("/")
    return re.sub(r"/+", "/", p)


def join(a: str, b: str) -> str:
    return norm_path((a or "") + "/" + (b or ""))


def flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = d
    return out


def load_props(svc_dir: Path) -> dict:
    props = {}
    for f in sorted((svc_dir / "src/main/resources").glob("application*.properties")):
        for line in f.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "!")) and ("=" in line or ":" in line):
                k, v = re.split(r"\s*[=:]\s*", line, maxsplit=1)
                props.setdefault(k.strip(), v.strip())
    for f in sorted((svc_dir / "src/main/resources").glob("application*.y*ml")):
        try:
            for doc in yaml.safe_load_all(f.read_text()):
                if isinstance(doc, dict):
                    props.update(flatten(doc))
        except yaml.YAMLError:
            pass
    return props


def resolve(value: str, consts: dict, props: dict):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    else:
        name = value.split(".")[-1]
        if re.fullmatch(r"[A-Z_][A-Z0-9_]*", name) and name in consts:
            value = consts[name]
    m = re.fullmatch(r"\$\{([^:}]+)(?::([^}]*))?\}", value)
    if m:
        value = str(props.get(m.group(1), m.group(2) or f"${{{m.group(1)}}}"))
    return value


def normalise(src: str) -> str:
    """Code without comments and whitespace runs, so comment-only edits do not change a contract fingerprint."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r'("(?:[^"\\\n]|\\.)*")|//[^\n]*', lambda m: m.group(1) or "", src)
    return re.sub(r"\s+", " ", src).strip()


def type_names(t: str):
    return [n for n in CAP.findall(t or "") if n not in JDK]


def balanced(src: str, i: int, open_="(", close=")"):
    """Index just past the bracket group starting at src[i] == open_ (ignores brackets in string literals)."""
    depth, j, n = 0, i, len(src)
    while j < n:
        c = src[j]
        if c == '"':
            j += 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
        elif c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return n


def method_after(src: str, i: int):
    """(signature, body, start, end) of the first method declared after position i."""
    m = re.compile(r"(?:@\w+(?:\s*\([^)]*\))?\s*)*(?:public|protected|private)?\s*(?:static\s+)?"
                   r"([\w<>\[\], ?.]+?)\s+(\w+)\s*\(").search(src, i)
    if not m:
        return "", "", i, i
    pe = balanced(src, m.end() - 1)
    b = src.find("{", pe)
    if b < 0 or src[pe:b].strip().endswith(";"):
        return src[m.start():pe], "", m.start(), pe
    be = balanced(src, b, "{", "}")
    return src[m.start():pe], src[b:be], m.start(), be


def enclosing_method(src: str, i: int):
    """(signature, body) of the method containing position i."""
    best = ("", "", 0, 0)
    for m in re.finditer(r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?.]+?\s+\w+\s*\(", src[:i]):
        sig, body, s, e = method_after(src, m.start())
        if s <= i < e:
            best = (sig, body, s, e)
    return best[0], best[1]


def with_helpers(src: str, body: str, depth=2):
    """Method body plus the bodies of same-class methods it calls (private helpers), so a change in a helper
    changes the contract fingerprint of the listener/endpoint that uses it."""
    out, seen, frontier = body, set(), [body]
    for _ in range(depth):
        nxt = []
        for b in frontier:
            for name in set(re.findall(r"(?<![.\w])(\w+)\s*\(", b)) - seen:
                seen.add(name)
                m = re.search(r"(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\], ?.]+?\s+" + re.escape(name) + r"\s*\(", src)
                if m:
                    _sig, hb, _s, _e = method_after(src, m.start())
                    if hb and hb not in out:
                        out += "\n" + hb
                        nxt.append(hb)
        frontier = nxt
    return out


def concat_path(src: str, i: int):
    """Path expression starting at a string literal: "/api/x/" + id + "/y" -> /api/x/{*}/y."""
    out, j, n = "", i, len(src)
    while j < n:
        while j < n and src[j] in " \t\r\n":
            j += 1
        if j < n and src[j] == '"':
            k = src.find('"', j + 1)
            out += src[j + 1:k]
            j = k + 1
        else:
            m = re.match(r"[\w.]+(?:\([^()]*\))?", src[j:])
            if not m or not m.group(0):
                break
            out += "{*}"
            j += m.end()
        while j < n and src[j] in " \t\r\n":
            j += 1
        if j < n and src[j] == "+":
            j += 1
            continue
        break
    return out


JAVA_TOKENS = re.compile(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|//[^\n]*|/\*.*?\*/', re.S)


def strip_comments(src: str) -> str:
    """Java source with // and /* */ comments blanked (newlines kept, so line numbers stay right). Commented-out
    mappings are not endpoints."""
    return JAVA_TOKENS.sub(lambda m: m.group(0) if m.group(0)[0] in "\"'" else re.sub(r"[^\n]", " ", m.group(0)), src)


def unit_files(d: Path, exts, root_unit=False):
    """A unit's files. For an app at the repository root, only what it owns (src/, build files), not other units."""
    top = (lambda f: f.relative_to(d).parts[0] in layout.ROOT_OWNS) if root_unit else (lambda f: True)
    return sorted(f for f in d.rglob("*") if f.is_file() and not f.is_symlink() and f.suffix in exts
                  and top(f) and not any(s in "/" + f.relative_to(d).as_posix() for s in SKIP))


def dir_hash(files, root: Path) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def url_refs(repo: Path, unit: str, files):
    out = []
    for f in files:
        if f.name in ("package-lock.json",):
            continue
        text = f.read_text(errors="replace")
        for m in URLREF.finditer(text):
            host, port = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            out.append({"unit": unit, "host": host, "port": int(port), "file": f.relative_to(repo).as_posix(),
                        "line": text[:m.start()].count("\n") + 1})
    return out


class ServiceScan:
    def __init__(self, repo: Path, svc_dir: Path, all_schemas: dict | None = None, default_name=None):
        self.repo, self.dir = repo, svc_dir
        self.props = load_props(svc_dir)
        # identity = the name other services use for it (spring.application.name), so moving a folder is not a change
        app = self.props.get("spring.application.name")
        self.name = str(app) if app and re.fullmatch(r"[\w.-]+", str(app)) else (default_name or svc_dir.name)
        self.files = unit_files(svc_dir, {".java", ".yml", ".yaml", ".properties", ".sql", ".xml", ".conf"},
                                root_unit=svc_dir.resolve() == repo.resolve())
        self.java = {f: strip_comments(f.read_text(errors="replace")) for f in self.files if f.suffix == ".java"}
        self.types = {}
        for f, src in self.java.items():
            for t in TYPE_DECL.findall(src):
                self.types.setdefault(t, f)
        self.consts = {}
        for src in self.java.values():
            self.consts.update(dict(CONST.findall(src)))
        self.all_schemas = all_schemas

    def rel(self, f: Path) -> str:
        return f.relative_to(self.repo).as_posix()

    def field_types(self, src):
        return {name: t for t, name in FIELD.findall(src)}

    def body_types(self, src: str, body: str):
        """Types a method body uses: declarations, new X(, X.class, X.method(, and the types of fields it touches."""
        names = set()
        for decl in re.findall(r"\b([A-Z]\w*(?:<[^;=()]*>)?)\s+\w+\s*=", body):
            names |= set(type_names(decl))
        names |= set(re.findall(r"new\s+([A-Z]\w*)", body))
        names |= set(re.findall(r"\b([A-Z]\w*)\.class\b", body))
        names |= set(re.findall(r"\b([A-Z]\w*)\.\w+\s*\(", body))
        ft = self.field_types(src)
        for used in set(re.findall(r"\b(\w+)\s*\.", body)):
            if used in ft:
                names |= set(type_names(ft[used]))
        return [n for n in names if n not in JDK]

    def is_component(self, name):
        src = self.java[self.types[name]]
        return bool(re.search(r"@(Service|Component|Repository|Configuration|RestController|Controller)\b", src)) \
            or name.endswith(("Repository", "Service", "Client", "Mapper", "Producer", "Consumer"))

    def closure(self, names, depth=3):
        """Data types reachable from `names` via fields/record components. Components (services, repositories,
        clients, mappers) are not expanded and are not returned: they are behaviour, not contract shape."""
        seen, frontier = {}, [n for n in names if n in self.types and not self.is_component(n)]
        for _ in range(depth + 1):
            nxt = []
            for n in frontier:
                if n in seen:
                    continue
                f = self.types[n]
                seen[n] = f
                src = self.java[f]
                refs = [t for ft, _ in FIELD.findall(src) for t in type_names(ft)]
                for comps in RECORD.findall(src):
                    refs += [t for c in comps.split(",") for t in type_names(c.strip().rsplit(" ", 1)[0])]
                nxt += [r for r in refs if r in self.types and r not in seen and not self.is_component(r)]
            frontier = nxt
        return sorted({self.rel(f) for f in seen.values()})

    def collaborators(self, src, body):
        """Component classes a method delegates to (e.g. a listener passing a Map payload to a service)."""
        ft = self.field_types(src)
        out = set()
        for used in set(re.findall(r"\b(\w+)\s*\.", body)):
            for t in type_names(ft.get(used, "")):
                if t in self.types and self.is_component(t):
                    out.add(self.rel(self.types[t]))
        return sorted(out)

    def fp(self, key: str, text: str, files, own: Path):
        """Fingerprint = the method text (minus logging and comments) + every other contract file's content."""
        text = re.sub(r"\b(?:log|logger|LOG|LOGGER)\s*\.\s*\w+\s*\((?:[^;\"]|\"(?:[^\"\\]|\\.)*\")*\)\s*;", "", text)
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"\s+", " ", text)
        h = hashlib.sha256((key + "\0" + text).encode())
        for f in sorted(files):
            if f != self.rel(own):
                h.update(normalise((self.repo / f).read_text(errors="replace")).encode())
        return h.hexdigest()[:16]

    def kafka(self):
        out = []
        for f, src in self.java.items():
            for m in SEND.finditer(src):
                end = balanced(src, m.end() - 1)
                args = split_args(src[m.end():end - 1])
                if not args:
                    continue
                topic = resolve(args[0], self.consts, self.props)
                sig, body = enclosing_method(src, m.start())
                body = with_helpers(src, body)
                var = args[-1].strip()
                ptype = None
                if re.fullmatch(r"\w+", var):
                    for d in re.findall(r"([\w<>\[\]?.]+)\s+" + re.escape(var) + r"\s*[,)=;]", sig + body):
                        names = type_names(d)
                        if names:
                            ptype = names[-1]
                            break
                names = ([ptype] if ptype else []) + self.body_types(src, body)
                files = sorted({self.rel(f)} | set(self.closure(names)))
                out.append({"topic": topic, "service": self.name, "role": "producer", "file": self.rel(f),
                            "line": src[:m.start()].count("\n") + 1, "payload": ptype or "?", "contract": files, "weak": self.collaborators(src, body),
                            "method": sig + body, "fp": self.fp(topic, src[m.start():end] + sig + body, files, f)})
            for m in LISTENER.finditer(src):
                end = balanced(src, m.end() - 1)
                args = src[m.end():end - 1]
                tm = re.search(r"topics\s*=\s*(\{[^}]*\}|\"[^\"]*\"|[\w.${}:-]+)", args)
                if not tm:
                    continue
                raw = tm.group(1).strip("{}")
                topics = [resolve(t, self.consts, self.props)
                          for t in re.findall(r"\"[^\"]*\"|\$\{[^}]*\}|[A-Za-z_][\w.]*", raw)]
                sig, body, _s, _e = method_after(src, end)
                body = with_helpers(src, body)
                params = sig[sig.find("(") + 1:]
                first = re.sub(r"@\w+(\([^)]*\))?", "", split_args(params)[0] if split_args(params) else "").strip()
                cr = re.search(r"ConsumerRecord<\s*[\w.]+\s*,\s*([\w.<>]+)\s*>", first)
                pn = type_names(cr.group(1) if cr else first.rsplit(" ", 1)[0])
                ptype = pn[-1] if pn else ("Map" if "Map" in first else "?")
                files = sorted({self.rel(f)} | set(self.closure([ptype] + self.body_types(src, body))))
                for t in topics:
                    out.append({"topic": t, "service": self.name, "role": "consumer", "file": self.rel(f),
                                "line": src[:m.start()].count("\n") + 1, "payload": ptype, "contract": files, "weak": self.collaborators(src, body),
                                "method": sig + body, "fp": self.fp(t, sig + body, files, f)})
        return out

    def rest_provided(self):
        out = []
        for f, src in self.java.items():
            if not CTRL.search(src):
                continue
            head = src[:src.find(" class ")] if " class " in src else src
            cm = CLASS_MAP.search(head)
            base = cm.group(1) if cm else ""
            for m in METHOD_MAP.finditer(src, len(head)):
                verb = m.group(1)
                ann_end = m.end()
                args = ""
                if src[ann_end:ann_end + 1] == "(":
                    e2 = balanced(src, ann_end)
                    args, ann_end = src[ann_end + 1:e2 - 1], e2
                pm = re.search(r"(?:value\s*=\s*|path\s*=\s*)?\{?\s*\"([^\"]*)\"", args)
                path = join(base, pm.group(1) if pm else "")
                if verb == "Request":
                    vm = re.search(r"RequestMethod\.(\w+)", args)
                    verb = vm.group(1).title() if vm else "Any"
                sig, body, _s, _e = method_after(src, ann_end)
                body = with_helpers(src, body)
                names = type_names(sig.split("(")[0]) + type_names(sig[sig.find("("):]) + self.body_types(src, body)
                files = sorted({self.rel(f)} | set(self.closure(names)))
                req_types = [t for prm in split_args(sig[sig.find("(") + 1:sig.rfind(")")]) if "@RequestBody" in prm
                             for t in type_names(re.sub(r"@\w+(\([^)]*\))?", "", prm).strip().rsplit(" ", 1)[0])]
                request_files = self.closure(req_types)
                out.append({"service": self.name, "verb": verb.upper(), "path": path, "file": self.rel(f),
                            "request_files": request_files,
                            "line": src[:m.start()].count("\n") + 1, "contract": files, "weak": self.collaborators(src, body), "method": sig + body,
                            "fp": self.fp(verb + " " + path, src[m.start():ann_end] + sig + body, files, f)})
        return out

    def rest_called(self):
        out = []
        for f, src in self.java.items():
            if CTRL.search(src):
                continue
            for m in re.finditer(r"\"/api/", src):
                p = concat_path(src, m.start())
                sig, body = enclosing_method(src, m.start())
                rt = re.findall(r"([A-Z]\w*)\.class", src[m.start():m.start() + 400])
                names = [t for t in rt if t not in JDK][:1] + self.body_types(src, body)
                files = sorted({self.rel(f)} | set(self.closure(names)))
                np_ = norm_path(p)
                # the verb may come before the path (`restTemplate.getForObject(base + "/api/..")`) or after it
                # (`String url = base + "/api/.."; ... HttpMethod.GET`): look from the start of the statement
                stmt = max(src.rfind(";", 0, m.start()), src.rfind("{", 0, m.start())) + 1
                near = src[stmt:m.start() + 500]
                vm = re.search(r"HttpMethod\.(GET|POST|PUT|PATCH|DELETE)|\b(get|post|put|patch|delete)For(?:Object|Entity)\b"
                               r"|\.(get|post|put|patch|delete)\(\)", near)
                verb = next((g for g in vm.groups() if g), None).upper() if vm else None
                out.append({"caller": self.name, "path": np_, "verb": verb, "file": self.rel(f),
                            "line": src[:m.start()].count("\n") + 1, "contract": files, "weak": self.collaborators(src, body), "method": sig + body,
                            "fp": self.fp(np_, sig + body, files, f)})
        return out

    def gateway_routes(self):
        out = []
        for f in (self.dir / "src/main/resources").glob("application*.y*ml"):
            text = f.read_text(errors="replace")
            for m in re.finditer(r"uri:\s*\S*?//([\w-]+)(?::(\d+))?[^\n]*\n\s*predicates:\s*\n((?:\s*-\s*[^\n]+\n?)+)", text):
                host = m.group(1)
                for pm in re.finditer(r"Path=([^\s]+)", m.group(3)):
                    for p in pm.group(1).split(","):
                        out.append({"caller": self.name, "path": norm_path(p.replace("/**", "")), "prefix": True,
                                    "host": host, "file": self.rel(f), "line": text[:m.start()].count("\n") + 1,
                                    "contract": [self.rel(f)], "method": m.group(0), "fp": sha(m.group(0).encode())})
        return out

    def schema(self):
        for k in ("spring.jpa.properties.hibernate.default_schema", "spring.flyway.schemas"):
            if self.props.get(k):
                return str(self.props[k]).split(",")[0].strip()
        return None

    def schema_refs(self):
        """SQL literals naming a schema (resolved to owners at link time, so cache entries stay independent)."""
        out = []
        for f, src in self.java.items():
            for m in re.finditer(r"\"[^\"]*\b(\w+_schema)\.\w+[^\"]*\"", src):
                out.append({"service": self.name, "schema": m.group(1), "file": self.rel(f),
                            "line": src[:m.start()].count("\n") + 1})
        return out

    def scan(self):
        port = self.props.get("server.port")
        try:
            port = int(re.sub(r"\$\{[^:}]*:?([^}]*)\}", r"\1", str(port))) if port is not None else None
        except ValueError:
            port = None
        if port is None and self.java \
                and any("@SpringBootApplication" in src for src in self.java.values()):
            port = 8080            # Spring Boot default when no server.port is set
        return {"name": self.name, "kind": "service", "path": self.rel(self.dir), "schema": self.schema(),
                "port": port, "app_name": self.props.get("spring.application.name"),
                "kafka": self.kafka(), "provides": self.rest_provided(),
                "calls": self.rest_called() + self.gateway_routes(), "schema_refs": self.schema_refs(),
                "module": pom_module(self.dir / "pom.xml", self.repo),
                "urlrefs": url_refs(self.repo, self.name, self.files), "jwt": self.jwt(), "files": len(self.java)}

    def jwt(self):
        """Token issuer/verifier roles: a service that verifies JWTs depends on the claims the issuer writes."""
        iss = [self.rel(f) for f, t in self.java.items() if re.search(r"Jwts\.builder\(\)|\.signWith\(", t)]
        ver = [self.rel(f) for f, t in self.java.items()
               if re.search(r"Jwts\.parser|parseSignedClaims|parseClaimsJws|\bClaims\b", t)]
        return {"issuer": iss, "verifier": ver}


def split_args(s: str):
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c == '"':
            k = i + 1
            while k < len(s) and s[k] != '"':
                k += 2 if s[k] == "\\" else 1
            cur += s[i:k + 1]
            i = k + 1
            continue
        if c in "([{<":
            depth += 1
        elif c in ")]}>":
            depth -= 1
        if c == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


TS_GEN = r"(?:<(?:[^<>()]|<[^<>()]*>)*>)?"            # .post<Record<string, number>>(
TS_CALL = re.compile(r"\.(get|post|put|delete|patch)\s*" + TS_GEN + r"\s*\(\s*(['\"`])")
TS_CALL_VAR = re.compile(r"\.(get|post|put|delete|patch)\s*" + TS_GEN + r"\s*\(\s*(\w+)\s*[,)]")
TS_LOCAL = re.compile(r"\b(?:const|let|var)\s+(\w+)\s*(?::\s*string\s*)?=\s*(['\"`])(.*?)\2", re.S)
TS_BASE = re.compile(r"baseURL\s*:\s*['\"`](/[^'\"`]*)['\"`]")


TS_OBJ = re.compile(r"(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*\{(.*?)\n\s*\}", re.S)
TS_FIELD = re.compile(r"^\s*(?:(?:private|public|protected|readonly|static)\s+)*(\w+)\s*(?::\s*string\s*)?=\s*(['\"`])((?:/|\$\{)[^'\"`]*)\2", re.M)
TS_TPL = re.compile(r"(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*`([^`]*\$\{[^`]*)`")
TS_STR = re.compile(r"(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*(['\"`])(/[^'\"`$]*)\2")


def ts_constants(texts):
    """Path constants the calls are built from: `const X = '/api/..'` and `const OBJ = { KEY: '/api/..' }` (Angular
    and React services commonly compose `${BASE}${OBJ.KEY}/${id}`)."""
    out = {}
    for t in texts:
        for m in TS_STR.finditer(t):
            out[m.group(1)] = m.group(3)
        for m in TS_OBJ.finditer(t):
            for k, _q, v in re.findall(r"(\w+)\s*:\s*(['\"`])([^'\"`]*)\2", m.group(2)):
                if v.startswith(("/", "${")):
                    out[f"{m.group(1)}.{k}"] = v
        for m in TS_TPL.finditer(t):              # const X = `${BASE}/opt`
            out.setdefault(m.group(1), m.group(2))
    for _ in range(3):                            # constants built from other constants
        for k, v in list(out.items()):
            if "${" in v:
                out[k] = resolve_template(v, {a: b for a, b in out.items() if "${" not in b}, keep_unknown=True)
    known = {k: v for k, v in out.items() if "${" not in v}
    for k, v in out.items():                      # `${API_BASE_URL}${X.ADMIN}`: drop the base, keep the path
        if "${" in v:
            r = resolve_template(v, known)
            if r and "{x}" not in r:
                known[k] = r
    return {k: v for k, v in known.items() if v.startswith("/")}


def ts_fields(text, consts):
    """Class fields of ONE file (`private baseUrl = `${API}${X.ADMIN}``) as `this.baseUrl` — per file, because every
    service class has its own baseUrl."""
    out = {}
    for m in TS_FIELD.finditer(text):
        v = m.group(3)
        if "${" in v:
            v = resolve_template(v, consts)
            if not v or "{x}" in v:
                continue
        if v.startswith("/"):
            out[f"this.{m.group(1)}"] = v
    return out


def resolve_template(lit, consts, keep_unknown=False):
    """`${API_BASE_URL}${OPT.X}/${id}` -> `/api/opt/x/{x}`: known path constants are substituted, a leading
    unknown expression is the host/base URL (dropped), any other expression is a path variable. If the leading
    unknown expression could itself be a path prefix (the result does not start with /api), the call is not resolved:
    better no edge than an invented one."""
    parts = re.split(r"(\$\{[^}]*\})", lit)
    out, first, dropped = [], True, False
    for p in parts:
        if not p:
            continue
        if p.startswith("${"):
            expr = p[2:-1].strip()
            if expr in consts:
                out.append(consts[expr])
            elif keep_unknown:
                out.append(p)
            elif first:
                dropped = True              # base URL / environment.apiUrl: not part of the path
            else:
                out.append("{x}")
        else:
            out.append(p)
        first = False
    path = "".join(out)
    if keep_unknown:
        return path
    if not path.startswith("/") or (dropped and not path.startswith("/api")):
        return ""
    return path


def scan_frontend(repo: Path, fe: Path):
    files = unit_files(fe, {".ts", ".tsx", ".js", ".jsx", ".conf", ".mjs", ".cjs"})
    src_files = [f for f in files if f.suffix in (".ts", ".tsx", ".js", ".jsx") and ".test." not in f.name
                 and ".spec." not in f.name and not f.name.startswith(("vite.config", "playwright"))]
    texts = {f: f.read_text(errors="replace") for f in src_files}
    bases = sorted({m for t in texts.values() for m in TS_BASE.findall(t)})
    base = bases[0] if bases else ""
    consts = ts_constants(texts.values())
    calls, file_spans, unresolved = [], [], []
    for f, text in texts.items():
        rel = f.relative_to(repo).as_posix()
        spans = []
        consts_all = consts
        consts = {**consts_all, **ts_fields(text, consts_all)}
        for m in TS_CALL.finditer(text):
            q = m.group(2)
            k = m.end()
            while k < len(text) and text[k] != q:
                k += 2 if text[k] == "\\" else 1
            lit = text[m.end():k]
            if q == "`" and "${" in lit:
                raw, lit = lit, resolve_template(lit, consts)
                if not lit and "/" in raw:
                    unresolved.append(f"{rel}:{text[:m.start()].count(chr(10)) + 1}")
            if not lit or not lit.startswith("/"):
                continue
            full = lit if lit.startswith("/api/") else join(base, lit)
            spans.append((m.start(), norm_path(full), m.group(1).upper()))
        for m in TS_CALL_VAR.finditer(text):     # const url = `${BASE}/x`; this.http.get(url, ...)
            local = [v for v in TS_LOCAL.finditer(text, 0, m.start()) if v.group(1) == m.group(2)]
            if not local:
                if re.search(r"url|endpoint|path|api", m.group(2), re.I):
                    unresolved.append(f"{rel}:{text[:m.start()].count(chr(10)) + 1}")
                continue
            v = local[-1]
            lit = resolve_template(v.group(3), consts) if "${" in v.group(3) else v.group(3)
            if lit and lit.startswith("/"):
                full = lit if lit.startswith("/api/") else join(base, lit)
                spans.append((m.start(), norm_path(full), m.group(1).upper()))
        seen = {pos for pos, _p, _v in spans}
        for m in re.finditer(r"['\"`](/api/[^'\"`]*)['\"`]", text):
            if norm_path(m.group(1)) == norm_path(base) or any(abs(m.start() - s0) < 80 for s0 in seen):
                continue
            spans.append((m.start(), norm_path(m.group(1)), None))
        file_spans.append((f, spans))
        consts = consts_all
    resolved = {p for _f, sp in file_spans for _pos, p, v in sp if v}
    for f, spans in file_spans:
        text, rel = texts[f], f.relative_to(repo).as_posix()
        # a bare '/api/x' literal that only serves as the prefix of resolved calls is a base constant, not a call
        spans = [x for x in spans if x[2] or not any(r != x[1] and r.startswith(x[1].rstrip("/") + "/") for r in resolved)]
        for pos, p, verb in spans:
            calls.append({"caller": fe.name, "path": p, "verb": verb, "file": rel, "line": text[:pos].count("\n") + 1,
                          "contract": [rel], "method": "", "fp": sha((p + rel).encode())})
    return {"name": fe.name, "kind": "frontend", "path": fe.relative_to(repo).as_posix(), "schema": None, "port": None,
            "app_name": None, "kafka": [], "provides": [], "calls": calls, "schema_refs": [], "module": None,
            "unresolved": unresolved,
            "jwt": {"issuer": [], "verifier": []},
            "urlrefs": url_refs(repo, fe.name, [f for f in files if f.suffix in (".conf", ".ts", ".js", ".mjs", ".cjs")
                                               or f.name.startswith("vite.config")]),
            "files": len(src_files)}


def pom_module(pom: Path, repo: Path, text: str | None = None):
    if text is None:
        if not pom.is_file():
            return None
        text = pom.read_text(errors="replace")
    t = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    body = re.sub(r"<parent>.*?</parent>", "", t, flags=re.S)
    body = re.sub(r"<build>.*?</build>", "", body, flags=re.S)
    body = re.sub(r"<dependencyManagement>.*?</dependencyManagement>", "", body, flags=re.S)
    aid = re.search(r"<artifactId>([^<]+)</artifactId>", body)
    if not aid:
        return None
    deps = re.findall(r"<dependency>.*?<artifactId>([^<]+)</artifactId>.*?</dependency>", body, re.S)
    rel = pom.parent.relative_to(repo).as_posix()
    return {"artifact": aid.group(1).strip(), "dir": rel if rel != "" else ".", "deps": sorted(set(d.strip() for d in deps))}


def maven_modules(repo: Path):
    mods = {}
    for pom in repo.rglob("pom.xml"):
        if any(s in pom.as_posix() for s in ("/target/", "/node_modules/")):
            continue
        t = re.sub(r"<!--.*?-->", "", pom.read_text(errors="replace"), flags=re.S)
        body = re.sub(r"<parent>.*?</parent>", "", t, flags=re.S)
        body = re.sub(r"<build>.*?</build>", "", body, flags=re.S)
        body = re.sub(r"<dependencyManagement>.*?</dependencyManagement>", "", body, flags=re.S)
        aid = re.search(r"<artifactId>([^<]+)</artifactId>", body)
        if not aid:
            continue
        deps = re.findall(r"<dependency>.*?<artifactId>([^<]+)</artifactId>.*?</dependency>", body, re.S)
        mods[aid.group(1).strip()] = {"dir": pom.parent.relative_to(repo).as_posix() or ".",
                                      "deps": sorted(set(d.strip() for d in deps))}
    return mods


def seg_match(call: str, provided: str) -> bool:
    a, b = call.strip("/").split("/"), provided.strip("/").split("/")
    return len(a) == len(b) and all(x == y or x == "{*}" or y == "{*}" for x, y in zip(a, b))


def specificity(call: str, provided: str) -> int:
    return sum(x == y and x != "{*}" for x, y in zip(call.strip("/").split("/"), provided.strip("/").split("/")))


def link(dm: dict):
    schemas = {}
    for n, u in dm["services"].items():
        if u.get("schema"):
            schemas[u["schema"]] = n
    dm["schemas"] = schemas
    for n, u in dm["services"].items():
        u["foreign_sql"] = [{**r, "owner": schemas[r["schema"]]} for r in u.get("schema_refs", [])
                            if r["schema"] in schemas and schemas[r["schema"]] != n]
    provides = [p for s in dm["services"].values() for p in s["provides"]]
    index = {}
    for p in provides:
        segs = p["path"].strip("/").split("/")
        index.setdefault((len(segs), tuple(segs[:3]) if "{*}" not in segs[:3] else None), []).append(p)
    edges = []
    for s in dm["services"].values():
        for c in s["calls"]:
            if c.get("prefix"):
                target = c["host"] if c["host"] in dm["services"] else None
                eps = [p for p in provides if p["service"] == target and (p["path"] + "/").startswith(c["path"] + "/")]
                edges.append({"kind": "route", "from": c["caller"], "to": target, "path": c["path"], "call": c,
                              "endpoints": [ep_key(p) for p in eps], "confidence": "route"})
                continue
            matches = [p for p in candidates(index, c["path"]) if seg_match(c["path"], p["path"]) and p["service"] != c["caller"]
                       and (not c.get("verb") or p["verb"] in (c["verb"], "ANY"))]
            if matches:   # keep only the most specific matches (fewest wildcard segments)
                best = max(specificity(c["path"], p["path"]) for p in matches)
                matches = [p for p in matches if specificity(c["path"], p["path"]) == best]
            conf = "exact" if len(matches) == 1 else ("ambiguous" if matches else "unresolved")
            # a runtime segment ({*}) that lines up only with FIXED endpoint segments (e.g. `/market/{symbol}` vs
            # `/market/hours`) almost certainly hits no real endpoint: report it instead of guessing
            var_ok = lambda p: all(not (x == "{*}" and y != "{*}") for x, y in
                                   zip(c["path"].strip("/").split("/"), p["path"].strip("/").split("/")))
            if matches and not any(var_ok(m) for m in matches):
                conf = "suspect"
            for t in sorted({m["service"] for m in matches}) or [None]:
                edges.append({"kind": "rest", "from": c["caller"], "to": t, "path": c["path"], "call": c,
                              "endpoints": [ep_key(m) for m in matches if m["service"] == t], "confidence": conf})
    dm["rest_edges"] = edges
    topics = {}
    for s in dm["services"].values():
        for k in s["kafka"]:
            topics.setdefault(k["topic"], {"producers": [], "consumers": []})[k["role"] + "s"].append(k)
    dm["topics"] = topics
    ports = {s["port"]: n for n, s in dm["services"].items() if s.get("port")}
    names = {n: n for n in dm["services"]}
    names.update({s["app_name"]: n for n, s in dm["services"].items() if s.get("app_name")})
    refs = []
    for s in dm["services"].values():
        for r in s["urlrefs"]:
            tgt = names.get(r["host"]) or (ports.get(r["port"]) if r["host"] in ("localhost", "127.0.0.1") else None)
            if tgt and tgt != r["unit"]:
                refs.append({**r, "to": tgt})
    dm["url_edges"] = refs


def candidates(index, path):
    segs = path.strip("/").split("/")
    out = list(index.get((len(segs), None), []))
    if "{*}" in segs[:3]:
        return out + [p for (n, k), ps in index.items() if n == len(segs) and k is not None for p in ps]
    return out + index.get((len(segs), tuple(segs[:3])), [])


def ep_key(p):
    return f"{p['service']} {p['verb']} {p['path']}"


SVC_EXT = {".java", ".yml", ".yaml", ".properties", ".sql", ".xml", ".conf"}
FE_EXT = {".ts", ".tsx", ".js", ".jsx", ".conf", ".mjs", ".cjs"}


def git(repo, *args, data=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return r.stdout if data else r.stdout.decode()


def git_units(repo: Path, ref: str):
    """[(unit, tree_hash)] for every unit (impact/layout.py) at `ref`. A root unit hashes only what it owns."""
    out = []
    for u in layout.units(repo, ref):
        if u["path"] == ".":
            h = hashlib.sha256(git(repo, "ls-tree", ref, "--", *layout.ROOT_OWNS).encode()).hexdigest()[:40]
        else:
            h = git(repo, "rev-parse", f"{ref}:{u['path']}").strip()
        out.append((u, h))
    return out


def materialise_raw(repo: Path, ref: str, path: str, root: Path):
    """Write the blobs of `path` at `ref` exactly as stored (no .gitattributes filters, encodings or export rules).
    Symlinks and submodules are skipped."""
    out = git(repo, "ls-tree", "-r", "-z", ref, "--", path, data=True).split(b"\0")
    entries = []
    for e in out:
        if not e:
            continue
        meta, p = e.split(b"\t", 1)
        mode, typ, h = meta.split()
        if typ == b"blob" and mode in (b"100644", b"100755"):
            entries.append((h.decode(), p.decode()))
    if not entries:
        return
    proc = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], capture_output=True, check=True,
                          input=b"".join(h.encode() + b"\n" for h, _ in entries))
    data, pos = proc.stdout, 0
    for h, p in entries:
        nl = data.index(b"\n", pos)
        size = int(data[pos:nl].split()[2])
        blob = data[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        dst = (root / p).resolve()
        if not str(dst).startswith(str(root.resolve()) + "/"):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(blob)


def attributes_present(repo: Path, ref: str) -> bool:
    """True if anything could make the checked-out files differ from the stored blobs."""
    if any(p.endswith(".gitattributes") for p in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()):
        return True
    info = repo / ".git" / "info" / "attributes"
    if info.exists() and info.read_text(errors="replace").strip():
        return True
    try:
        return bool(git(repo, "config", "--get", "core.attributesFile").strip())
    except subprocess.CalledProcessError:
        return False


def build(repo: Path, cache: Path | None = None, ref: str | None = None):
    """Dependency map of `repo` (working tree), or of git revision `ref` without checking it out: units are keyed by
    their git tree hash, so only units missing from the cache are extracted (materialised with git archive)."""
    repo = repo.resolve()
    units, stats = {}, {"scanned": 0, "cached": 0}
    dups = []
    tmp = None
    checked_out = False
    if ref:
        listing = git_units(repo, ref)
        try:   # the clean checked-out commit with no attribute rules: the working tree equals the stored blobs
            checked_out = (git(repo, "rev-parse", ref).strip() == git(repo, "rev-parse", "HEAD").strip()
                           and not git(repo, "status", "--porcelain", "--untracked-files=no").strip()
                           and not attributes_present(repo, ref))
        except subprocess.CalledProcessError:
            checked_out = False
        unit_list = [(u, h) for u, h in listing]
    else:
        unit_list = []
        for u in layout.units(repo):
            d = repo / u["path"]
            files = unit_files(d, FE_EXT if u["kind"] == "frontend" else SVC_EXT, root_unit=u["path"] == ".")
            unit_list.append((u, "c" + dir_hash(files, repo)))
    try:
        for u, h in unit_list:
            path, name, is_fe = u["path"], u["name"], u["kind"] == "frontend"
            key = f"v{VERSION}-{name}-{h}"
            cf = cache / f"{key}.json" if cache else None
            if cf and cf.exists():
                entry = json.loads(cf.read_text())
                if entry["name"] in units:
                    dups.append(f"{entry['name']}: {units[entry['name']]['path']} and {entry['path']}")
                units[entry["name"]] = entry
                stats["cached"] += 1
                continue
            root = repo
            if ref and not checked_out:
                if tmp is None:
                    tmp = Path(tempfile.mkdtemp(prefix="depmap-"))
                root = tmp
                (root / path).mkdir(parents=True, exist_ok=True)
                for part in ([x for x in layout.ROOT_OWNS] if path == "." else [path]):
                    materialise_raw(repo, ref, part, root)
            ud = root / path
            entry = scan_frontend(root, ud) if is_fe else ServiceScan(root, ud, default_name=name).scan()
            if entry["name"] in units:
                dups.append(f"{entry['name']}: {units[entry['name']]['path']} and {entry['path']}")
            units[entry["name"]] = entry
            stats["scanned"] += 1
            if cf:
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_text(json.dumps(entry))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    # modules: each service carries its own pom; other poms (root, libs) are few and read directly
    mods = {u["module"]["artifact"]: u["module"] for u in units.values() if u.get("module")}
    if ref:
        others = [p for p in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
                  if p.endswith("pom.xml") and not p.startswith("services/") and "/node_modules/" not in p
                  and p not in {("" if u["path"] == "." else u["path"] + "/") + "pom.xml" for u, _ in unit_list}]
        for p in others:
            m = pom_module(repo / p, repo, git(repo, "show", f"{ref}:{p}"))
            if m:
                mods[m["artifact"]] = m
    else:
        for pom in repo.rglob("pom.xml"):
            rel = pom.relative_to(repo).as_posix()
            if rel.startswith("services/") or "/target/" in rel or "node_modules" in rel:
                continue
            m = pom_module(pom, repo)
            if m:
                mods[m["artifact"]] = m
    dm = {"version": VERSION, "services": units, "modules": mods, "stats": stats, "ref": ref, "duplicates": dups}
    link(dm)
    return dm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("-o", "--out")
    ap.add_argument("--cache")
    ap.add_argument("--config", help="trusted project.yaml for the unit layout (in CI: the base branch's copy)")
    ap.add_argument("--ref", help="build the map of this git revision (uses tree hashes; no checkout needed)")
    a = ap.parse_args()
    if a.config:
        layout.TRUSTED_CONFIG = a.config
    dm = build(Path(a.repo), Path(a.cache) if a.cache else None, a.ref)
    if a.out:
        Path(a.out).write_text(json.dumps(dm, indent=1, sort_keys=True))
    s = dm["services"]
    e = dm["rest_edges"]
    print(f"depmap: {len(s)} units, {len(dm['topics'])} topics ({sum(len(x['kafka']) for x in s.values())} producer/consumer"
          f" sites), {sum(len(x['provides']) for x in s.values())} REST endpoints, {len(e)} call edges "
          f"({sum(x['confidence'] == 'unresolved' for x in e)} unresolved, {sum(x['confidence'] == 'suspect' for x in e)} suspect, {sum(x['confidence'] == 'ambiguous' for x in e)}"
          f" ambiguous), {len(dm['url_edges'])} host:port refs, {len(dm['modules'])} maven modules; "
          f"scanned {dm['stats']['scanned']}, cached {dm['stats']['cached']}", file=sys.stderr)
    for x in e:
        if x["confidence"] == "suspect":
            print(f"  SUSPECT CALL {x['from']} -> {x['to']} `{x['path']}` ({x['call']['file']}:{x['call']['line']}): "
                  f"the runtime segment only lines up with fixed endpoints; probably calls nothing", file=sys.stderr)


if __name__ == "__main__":
    main()
