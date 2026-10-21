#!/usr/bin/env python3
"""Build a synthetic monorepo of ~1,000 services by replicating a real one, for scale tests.

  make_monorepo.py <template_repo> <out_dir> --clusters 111 [--git]

Each cluster k is a renamed copy of every service in the template: service names (order-service -> order-service-c007),
Kafka topics (x.y.z -> x.y.z.c007), REST paths (/api/v1/... -> /api/v1/c007/...), DB schemas (a_schema ->
a_c007_schema) and ports are made unique, so the dependency graph is ~N independent copies of a real one.
To make it a monorepo rather than N islands, every cluster's audit-service also consumes one topic from cluster 0,
and a shared library module (libs/common-events) is depended on by every 10th service.
"""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

TEXT = {".java", ".yml", ".yaml", ".properties", ".sql", ".xml", ".conf", ".md", ".json"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("out")
    ap.add_argument("--clusters", type=int, default=111)
    ap.add_argument("--git", action="store_true")
    a = ap.parse_args()
    src, out = Path(a.template), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "services").mkdir(parents=True)
    names = sorted(d.name for d in (src / "services").iterdir() if d.is_dir())
    topics = set()
    for f in (src / "services").rglob("*.java"):
        topics |= set(re.findall(r"\"([a-z]+(?:\.[a-z]+){1,})\"", f.read_text(errors="replace")))
    topics = sorted(t for t in topics if not t.startswith(("com.", "org.", "java.", "spring.")))
    ports = {}
    for n in names:
        y = src / "services" / n / "src/main/resources/application.yml"
        m = re.search(r"^server:\s*\n\s+port:\s*(\d+)", y.read_text(), re.M) if y.exists() else None
        if m:
            ports[n] = int(m.group(1))
    modules = []
    for k in range(a.clusters):
        c = f"c{k:03d}"
        for n in names:
            dst = out / "services" / f"{n}-{c}"
            shutil.copytree(src / "services" / n, dst, ignore=shutil.ignore_patterns("target"))
            for f in dst.rglob("*"):
                if not f.is_file() or f.suffix not in TEXT:
                    continue
                t = f.read_text(errors="replace")
                for other in names:
                    t = re.sub(rf"\b{re.escape(other)}\b(?!-c\d)", f"{other}-{c}", t)
                for tp in topics:
                    t = t.replace(f'"{tp}"', f'"{tp}.{c}"').replace(f"{tp}-group", f"{tp}.{c}-group")
                t = t.replace("/api/v1/", f"/api/v1/{c}/")
                t = re.sub(r"\b(\w+)_schema\b", rf"\1_{c}_schema", t)
                for svc, p in ports.items():
                    t = re.sub(rf"(?<=[:=]){p}\b|(?<=port: ){p}\b", str(20000 + k * 20 + names.index(svc)), t)
                if n == "audit-service" and k > 0 and f.name == "AuditEventConsumer.java":
                    t = t.replace('@KafkaListener(topics = "order.state.changed.' + c + '"',
                                  '@KafkaListener(topics = {"order.state.changed.' + c + '", "order.state.changed.c000"}', 1)
                f.write_text(t)
            modules.append(f"services/{n}-{c}")
            if len(modules) % 10 == 0:
                pom = dst / "pom.xml"
                pt = pom.read_text()
                pom.write_text(pt.replace("<dependencies>", "<dependencies>\n        <dependency><groupId>com.brokerdealer"
                                          "</groupId><artifactId>common-events</artifactId><version>1.0.0</version></dependency>", 1))
    lib = out / "libs/common-events/src/main/java/com/brokerdealer/common"
    lib.mkdir(parents=True)
    (lib / "EventEnvelope.java").write_text("package com.brokerdealer.common;\n\npublic record EventEnvelope(String id, String type, String payload) {}\n")
    (out / "libs/common-events/pom.xml").write_text("<project><modelVersion>4.0.0</modelVersion><groupId>com.brokerdealer</groupId>"
                                                    "<artifactId>common-events</artifactId><version>1.0.0</version></project>\n")
    mods = "\n".join(f"    <module>{m}</module>" for m in ["libs/common-events"] + modules)
    (out / "pom.xml").write_text(f"<project><modelVersion>4.0.0</modelVersion><groupId>com.brokerdealer</groupId>"
                                 f"<artifactId>monorepo-parent</artifactId><version>1.0.0</version><packaging>pom</packaging>\n"
                                 f"  <modules>\n{mods}\n  </modules>\n</project>\n")
    if a.git:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=out, check=True)
        subprocess.run(["git", "add", "-A"], cwd=out, check=True)
        subprocess.run(["git", "-c", "user.name=scale", "-c", "user.email=s@s", "commit", "-qm", "base"], cwd=out, check=True)
    loc = sum(len(f.read_text(errors="replace").splitlines()) for f in (out / "services").rglob("*.java"))
    print(f"{len(modules)} services, {loc:,} Java lines")


if __name__ == "__main__":
    main()
