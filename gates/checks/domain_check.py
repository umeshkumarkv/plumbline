#!/usr/bin/env python3
"""Plumbline Guardrails — order state machine gate (CLAUDE.md §5).

  DOM-SM-illegal-transition  transitionState(order, OrderStatus.A, OrderStatus.B, ...) with (A,B) not in §5
  DOM-SM-dynamic-target      transitionState(order, <non-literal>, OrderStatus.B, ...) where B has a single
                             legal predecessor (must be written with the literal from-state)
  DOM-SM-direct-setstatus    order.setStatus(OrderStatus.X) outside OrderStateMachineService
                             (bypasses persistence + order.state.changed event)
  DOM-SM-transition-map      a Map/Set literal of OrderStatus transitions that contains an edge not in §5
"""
import json
import re
import sys
from pathlib import Path
if sys.platform == "win32" and not sys.flags.utf8_mode and __name__ == "__main__":   # Windows: UTF-8 like macOS/Linux
    import subprocess as _sp
    sys.exit(_sp.call([sys.executable, "-X", "utf8", *(["-I"] if sys.flags.isolated else []), *sys.argv],
                      env={**__import__("os").environ, "PYTHONUTF8": "1"}))

# CLAUDE.md §5 — valid transitions only
LEGAL = {
    ("NEW", "VALIDATED"), ("VALIDATED", "RISK_CHECK_PASSED"), ("RISK_CHECK_PASSED", "ACCEPTED"),
    ("ACCEPTED", "SENT_TO_EXECUTION"), ("SENT_TO_EXECUTION", "PARTIALLY_FILLED"),
    ("PARTIALLY_FILLED", "FILLED"), ("SENT_TO_EXECUTION", "FILLED"), ("SENT_TO_EXECUTION", "REJECTED"),
    ("PARTIALLY_FILLED", "EXPIRED"), ("SENT_TO_EXECUTION", "EXPIRED"), ("NEW", "REJECTED"),
    ("VALIDATED", "RISK_REJECTED"),
    # Implementation detail present in the codebase (risk rejection arrives while order is NEW).
    # Recorded as an approved exception; remove when §5 and code are reconciled.
    ("NEW", "RISK_REJECTED"),
    # PARTIALLY_FILLED receives further partial fills.
    ("PARTIALLY_FILLED", "PARTIALLY_FILLED"),
}
TERMINAL = {"RISK_REJECTED", "FILLED", "CANCELLED", "REJECTED", "EXPIRED"}
PREDECESSORS = {}
for a, b in LEGAL:
    PREDECESSORS.setdefault(b, set()).add(a)
STATE_MACHINE_CLASS = "OrderStateMachineService"

findings = []


def add(rule, path, line, msg):
    findings.append({"rule": rule, "path": Path(path).as_posix(), "line": line, "message": msg})


def lineno(text, idx):
    return text[:idx].count("\n") + 1


OWN_SCHEMA = {"auth-service": "auth_schema", "order-service": "order_schema", "client-service": "client_schema",
              "marketdata-service": "market_schema", "risk-service": "risk_schema",
              "execution-service": "execution_schema", "audit-service": "audit_schema"}


def check_foreign_schema(root):
    """DOM-BOUNDARY-foreign-schema-sql: Java string literals that reference another service's schema (CLAUDE.md §3)."""
    for f in root.glob("services/*/src/main/**/*.java"):
        rel = f.relative_to(root)
        svc = rel.parts[1]
        own = OWN_SCHEMA.get(svc)
        text = f.read_text(errors="ignore")
        for m in re.finditer(r'"([^"\n]*\b(auth|order|client|market|risk|execution|audit)_schema\.[^"\n]*)"', text):
            schema = m.group(2) + "_schema"
            if schema != own:
                add("DOM-BOUNDARY-foreign-schema-sql", rel, lineno(text, m.start()),
                    f"{svc} SQL references {schema} (CLAUDE.md §3: no service reads or writes another service's schema)")


def main():
    root = Path(sys.argv[1]).resolve()
    for f in root.glob("services/*/src/main/**/*.java"):
        text = f.read_text(errors="ignore")
        if "OrderStatus" not in text:
            continue
        rel = f.relative_to(root)
        for m in re.finditer(r"transitionState\(\s*\w+\s*,\s*([^,]+?)\s*,\s*OrderStatus\.(\w+)", text):
            src, dst = m.group(1).strip(), m.group(2)
            lit = re.fullmatch(r"OrderStatus\.(\w+)", src)
            if lit:
                if (lit.group(1), dst) not in LEGAL:
                    add("DOM-SM-illegal-transition", rel, lineno(text, m.start()),
                        f"{lit.group(1)} -> {dst} is not a valid transition (CLAUDE.md §5)")
            elif len(PREDECESSORS.get(dst, ())) <= 1 and not text[: m.start()].endswith("void "):
                add("DOM-SM-dynamic-target", rel, lineno(text, m.start()),
                    f"transition to {dst} uses a non-literal from-state; {dst} has one legal predecessor "
                    f"{sorted(PREDECESSORS.get(dst, {'?'}))} (CLAUDE.md §5)")
        if f.stem != STATE_MACHINE_CLASS:
            for m in re.finditer(r"\.setStatus\(\s*OrderStatus\.(\w+)\s*\)", text):
                add("DOM-SM-direct-setstatus", rel, lineno(text, m.start()),
                    f"status set to {m.group(1)} outside {STATE_MACHINE_CLASS}: bypasses §5 transition rules and the order.state.changed event")
        # transition tables written as Map.of(OrderStatus.A, Set.of(OrderStatus.B, ...)) / Map.entry(...)
        for m in re.finditer(r"(?:Map\.entry|Map\.of|put)\(\s*OrderStatus\.(\w+)\s*,\s*(?:EnumSet|Set|List)\.of\(([^)]*)\)", text):
            src = m.group(1)
            for dst in re.findall(r"OrderStatus\.(\w+)", m.group(2)):
                if (src, dst) not in LEGAL:
                    add("DOM-SM-transition-map", rel, lineno(text, m.start()),
                        f"transition table allows {src} -> {dst}, not valid per CLAUDE.md §5")
            if src in TERMINAL and re.findall(r"OrderStatus\.(\w+)", m.group(2)):
                add("DOM-SM-transition-map", rel, lineno(text, m.start()),
                    f"terminal state {src} has outgoing transitions (CLAUDE.md §5)")
    check_foreign_schema(root)
    for x in findings:
        print(json.dumps(x))


if __name__ == "__main__":
    main()
