# Benchmark results (2026-10-19)

## Self-test: `selftest/bench_selftest.py`, 15/15
- **Good fixtures:** each of the 10 agents' benchmarks passes its good fixture.
- **Bad fixtures:** each fails its bad fixture on exactly the planted checks: PM 6, BA 6, Arch 7, Onboard 4, QA 6, SM 3, DevOps 5, Dev 3, Code Review 1 (rulebook edit) and Doc 1 (moved endpoint).
- **Attack regression cases** (from the independent review), all closed:
  - a forged QA results file;
  - invented entity, table, Redis key and downstream call;
  - usage errors, which must exit 2;
  - stale test reports.

## Real codebase: `broker-dealer` @ develop, 9 services
These are the onboard benchmark's results on the **existing** service CLAUDE.md files, the docs every agent reads. Raw data is in `eval/oms/`.

| Service | Drift items | Checks failing |
|---|---|---|
| marketdata-service | 22 | undocumented endpoints, invented `/market/{symbol}`, undocumented entities/tables/Redis keys |
| risk-service | 13 | 5 undocumented endpoints (rule approval flow), 3 entities, 3 tables, the `dup:` Redis key |
| order-service | 11 | 4 undocumented endpoints; documented calls to a missing endpoint and an unused one; execution-service call not documented |
| client-service | 7 | undocumented endpoints, invented `PATCH /reserved-cash`, Redis key |
| auth-service | 4 | undocumented endpoints, table |
| execution-service | 4 | documents a call to a missing endpoint (the code really calls it: a live bug), an entity, a table |
| api-gateway | 2 | port 8080 in doc vs 9090 in code; SSE proxy call to notification-service not documented |
| audit-service | 1 | table not named in the schema section |
| notification-service | 0 | |

- **Total:** 64 drift items in 8 of 9 services.
- **Independent precision audit** (all 54 items of the first run were checked against the code by a reviewer who did not write the benchmark): **53/54 real**. The one false positive (a section heading synonym) is fixed.
- **The 4 new invented-call findings:** all 4 are real.
- **The 15 OB-10 items:** these are tables missing from the schema section that the template asks for. They are template gaps, not invented facts.

DevOps benchmark: **29 plaintext credential lines**, all confirmed real. They come from `k8s/secret.yaml`, docker-compose passwords and `${…:brokerdealer}` defaults. With `--base`, these are reported as pre-existing debt (DO-8b WARN), and only newly added secrets fail.

## Limits
- **Text-level checks.** Prose that names an item still counts as documenting it (OB-9 and similar). The judge rates whether it is documented *well*.
- **Supplied facts.** SM and BA blocked-by checks rest on the JIRA export the originator saves, and they are labelled `supplied`. QA replay only re-runs plain GET curls against a running stack.
- **One real codebase.** Accuracy was measured on one repo (Java/Spring). The fixtures cover each check's logic, not every coding style.
