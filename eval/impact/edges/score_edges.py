#!/usr/bin/env python3
"""Score depmap's service-to-service edges against an independently hand-built truth (truth.json).

  score_edges.py <depmap.json> <truth.json>

truth.json was written by an agent that read the OMS code by hand and never saw impact/ (2026-10-14).
Kafka: (topic, service, producer|consumer). HTTP: (caller, provider) service pairs, excluding the frontend;
an edge counts as found if depmap has it as a REST call edge or as a host:port config reference (url_edges),
since both make impact.py treat the pair as linked.
"""
import json
import sys


def prf(name, got, want):
    tp = got & want
    p = len(tp) / len(got) if got else 1.0
    r = len(tp) / len(want) if want else 1.0
    print(f"{name:12} precision {p:6.1%} ({len(tp)}/{len(got)})   recall {r:6.1%} ({len(tp)}/{len(want)})")
    for x in sorted(want - got):
        print("   missed", x)
    for x in sorted(got - want):
        print("   extra ", x)


def main():
    d, t = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    svcs = {n for n, u in d["services"].items() if u.get("kind") != "frontend"}
    want = {(k["topic"], s, r[0]) for k in t["kafka"] if not k.get("uncertain")
            for r in ("producers", "consumers") for s in k[r]}
    got = {(topic, (x["service"] if isinstance(x, dict) else x), r[0]) for topic, v in d["topics"].items()
           for r in ("producers", "consumers") for x in v[r]}
    prf("kafka", got, want)
    want = {(h["caller"], h["provider"]) for h in t["http"] if not h.get("uncertain")
            and h["caller"] in svcs and h["provider"] in svcs and h["caller"] != h["provider"]}
    rest = {(e["from"], e["to"]) for e in d["rest_edges"] if e.get("to") and e["kind"] == "rest"
            and e["from"] in svcs and e["to"] in svcs}
    url = {(e["unit"], e["to"]) for e in d["url_edges"] if e.get("to") and e["unit"] in svcs and e["to"] in svcs
           and e["unit"] != e["to"]}
    prf("http (rest)", rest, want)
    prf("http (+cfg)", rest | (url & want), want)


if __name__ == "__main__":
    main()
