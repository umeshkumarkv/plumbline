#!/usr/bin/env python3
"""Plumbline Guardrails — structural gates Semgrep cannot express.

Usage: structure_check.py <repo_root> [--json]
Emits findings as JSON lines: {"rule": ..., "path": ..., "line": ..., "message": ...}

Rules (CLAUDE.md references):
  C2-class-suffix          §13c  class in a layer package must carry the layer suffix
  C10-service-test-missing §15   every *Service class in main has a *ServiceTest
  C12-flyway-filename      C12   V{n}__{snake_case}.sql (double underscore)
  C12-flyway-destructive   C12   no DROP TABLE / TRUNCATE (approved ones live in the baseline)
  C12-flyway-foreign-schema §3   migration touches only its own service schema
  C12-flyway-duplicate-version   versions unique per service
  C2-kafka-topic-name      §13b  topics dot.separated.lower
  C2-kafka-group-name      §13b  groupId == {service}-{topic}-group
"""
import json
import re
import sys
from pathlib import Path

SUFFIX_BY_PACKAGE = {
    "controller": ("Controller",),
    "repository": ("Repository",),
    "mapper": ("Mapper",),
    "config": ("Config", "Properties", "Filter"),
    "producer": ("Producer",),
    "consumer": ("Consumer",),
    "request": ("Request",),
    "response": ("Response",),
    "exception": ("Exception", "Handler"),
}
# A class in a layer package is held to the suffix only if it carries that layer's stereotype.
STEREOTYPE_BY_PACKAGE = {
    "controller": r"@(Rest)?Controller\b",
    "repository": r"@Repository\b|extends\s+(Jpa|Crud|PagingAndSorting)Repository",
    "config": r"@Configuration\b|@ConfigurationProperties\b|extends\s+\w*Filter\b|implements\s+\w*Filter\b",
    "producer": r"KafkaTemplate",
    "consumer": r"@KafkaListener\b",
    "mapper": r"@Mapper\b",
    "exception": r"extends\s+\w*Exception\b|@RestControllerAdvice\b|@ControllerAdvice\b",
}
# service schema names as declared in entities (CLAUDE.md §3: one schema per service)
SCHEMA_BY_SERVICE = {
    "auth-service": "auth_schema", "order-service": "order_schema", "client-service": "client_schema",
    "marketdata-service": "market_schema", "risk-service": "risk_schema",
    "execution-service": "execution_schema", "audit-service": "audit_schema",
}
ALL_SCHEMAS = set(SCHEMA_BY_SERVICE.values())

findings = []


def add(rule, path, line, message):
    findings.append({"rule": rule, "path": str(path), "line": line, "message": message})


def service_of(path: Path):
    parts = path.parts
    if "services" in parts:
        i = parts.index("services")
        if i + 1 < len(parts):
            return parts[i + 1]
    return None


def check_java(root: Path):
    main_classes, test_classes = {}, set()
    for f in root.glob("services/*/src/**/*.java"):
        rel = f.relative_to(root)
        text = f.read_text(errors="ignore")
        if "/src/test/" in str(rel):
            test_classes.add((service_of(rel), f.stem))
            continue
        pkg_dir = f.parent.name
        decl = re.search(r"^\s*public\s+(?:final\s+|abstract\s+)*(class|interface|record|enum)\s+(\w+)", text, re.M)
        if not decl:
            continue
        kind, name = decl.groups()
        main_classes[(service_of(rel), name)] = rel
        suffixes = SUFFIX_BY_PACKAGE.get(pkg_dir)
        # Only classes that play the layer's role must carry its suffix (helpers may live alongside).
        stereotype = STEREOTYPE_BY_PACKAGE.get(pkg_dir)
        plays_role = stereotype is None or re.search(stereotype, text)
        if suffixes and kind != "enum" and plays_role and not name.endswith(suffixes):
            line = text[: decl.start()].count("\n") + 1
            add("C2-class-suffix", rel, line, f"{kind} {name} in package '{pkg_dir}' must end with {'/'.join(suffixes)} (CLAUDE.md §13c)")
        # kafka naming
        for m in re.finditer(r"@KafkaListener\((.*?)\)\s*\n", text, re.S):
            body, line = m.group(1), text[: m.start()].count("\n") + 1
            topics = re.findall(r'topics\s*=\s*"([^"]+)"', body)
            group = re.search(r'groupId\s*=\s*"([^"]+)"', body)
            for t in topics:
                if not re.fullmatch(r"[a-z]+(\.[a-z]+)+(\.DLT)?", t):
                    add("C2-kafka-topic-name", rel, line, f"topic '{t}' must be dot.separated.lower (CLAUDE.md §13b)")
                expected = f"{service_of(rel)}-{t}-group"
                if group and group.group(1) != expected:
                    add("C2-kafka-group-name", rel, line, f"groupId '{group.group(1)}' should be '{expected}' (CLAUDE.md §13b)")
    for (svc, name), rel in main_classes.items():
        if name.endswith("Service") and (svc, name + "Test") not in test_classes:
            add("C10-service-test-missing", rel, 1, f"{name} has no {name}Test (CLAUDE.md §15)")
    check_entity_enums(root)


def check_entity_enums(root: Path):
    """C1-enum-not-string: an entity field whose type is an enum must be @Enumerated(EnumType.STRING)
    (JPA defaults to ORDINAL when the annotation is missing). Enum types are resolved per service."""
    enums = {}
    for f in root.glob("services/*/src/main/**/*.java"):
        for m in re.finditer(r"\benum\s+(\w+)", f.read_text(errors="ignore")):
            enums.setdefault(service_of(f.relative_to(root)), set()).add(m.group(1))
    for f in root.glob("services/*/src/main/**/*.java"):
        text = f.read_text(errors="ignore")
        if "@Entity" not in text:
            continue
        rel = f.relative_to(root)
        svc_enums = enums.get(service_of(rel), set())
        for m in re.finditer(r"^[ \t]*(?:private|protected|public)\s+(\w+)\s+(\w+)\s*(?:=[^;]*)?;", text, re.M):
            typ, field = m.groups()
            if typ not in svc_enums:
                continue
            # annotations between previous statement end and this field
            prev = max(text.rfind(";", 0, m.start()), text.rfind("{", 0, m.start()))
            block = text[prev + 1: m.start()]
            if "@Convert" in block or "@Transient" in block:
                continue
            if not re.search(r"@Enumerated\s*\(\s*(value\s*=\s*)?(jakarta\.persistence\.)?EnumType\.STRING\s*\)", block):
                line = text[: m.start(1)].count("\n") + 1
                add("C1-enum-not-string", rel, line,
                    f"entity field {field} of enum type {typ} lacks @Enumerated(EnumType.STRING); JPA defaults to ORDINAL (CLAUDE.md §13a, §13f)")


def check_unscanned_java(root: Path):
    """C5-java-outside-services: gates scan services/ only, so production Java elsewhere would escape them."""
    for f in root.glob("**/src/main/java/**/*.java"):
        rel = f.relative_to(root)
        if rel.parts[0] not in ("services", "node_modules") and not {".plumbline", ".agentic-sdlc", ".guardrails"} & set(rel.parts):
            add("C5-java-outside-services", rel, 1,
                "production Java outside services/ is not scanned by the gates; move it under services/<svc> (CLAUDE.md §3, §4)")


def check_flyway(root: Path):
    seen = {}
    for f in root.glob("services/*/src/main/resources/db/migration/*.sql"):
        rel = f.relative_to(root)
        svc = service_of(rel)
        m = re.fullmatch(r"V(\d+)__([a-z0-9_]+)\.sql", f.name)
        if not m:
            add("C12-flyway-filename", rel, 1, "migration must be named V{n}__{snake_case}.sql")
        else:
            key = (svc, int(m.group(1)))
            if key in seen:
                add("C12-flyway-duplicate-version", rel, 1, f"version V{m.group(1)} already used by {seen[key]}")
            seen[key] = f.name
        text = f.read_text(errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            u = line.upper()
            if re.search(r"\b(DROP\s+TABLE|TRUNCATE)\b", u):
                add("C12-flyway-destructive", rel, i, "DROP TABLE / TRUNCATE: only allowed once a human adds it to the baseline via a policy PR")
            own = SCHEMA_BY_SERVICE.get(svc)
            for s in ALL_SCHEMAS - {own}:
                if re.search(rf"\b{s}\.", line, re.I):
                    add("C12-flyway-foreign-schema", rel, i, f"{svc} migration touches {s} (CLAUDE.md §3)")


def main():
    root = Path(sys.argv[1]).resolve()
    check_java(root)
    check_flyway(root)
    check_unscanned_java(root)
    for f in findings:
        print(json.dumps(f))


if __name__ == "__main__":
    main()
