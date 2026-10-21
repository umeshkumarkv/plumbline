# impact — eval results (2026-10-14)

Codebase: broker-dealer OMS (9 services + frontend). Question per scenario: which OTHER units must review this change?

## Method

| Step | Who | Isolation |
|---|---|---|
| Scenarios (realistic PRs as exact edits) | 4 author agents, one per set | Never saw the tool or the other sets |
| Answer key A | The set's author | Same |
| Answer key B | A separate judge per set | Never saw the tool, the other sets or key A |
| Truth | Units **both** keys list | Units only one key lists are "disputed" and not scored |
| Scoring | `impact/eval_impact.py` (deterministic) | Gives the agreed truth and both raw keys |

"Affected" means the unit consumes, calls or depends on the changed contract and **reads** what changed. Declaring a field and never reading it does not count, and neither do second-hand consumers. Controls are changes that affect nobody.

Judge agreement: set 1 had 43 agreed units and 1 disputed; set 2 had 40 and 2; sets 3 and 4 had 27 and 0, and 23 and 0.

## Results

| Set | Scenarios | Run | Code | Recall | Precision | Controls clean |
|---|---|---|---|---|---|---|
| 1 | 30 | training | v4 | 43/43 (100%) | 97.7% | 9/9 |
| **2** | 30 | **held-out** | v1 | **31/40 (77.5%)** | **88.6%** | 7/7 |
| 2 | 30 | after tuning | v4 | 40/40 | 95.2% | 7/7 |
| **3** | 25 | **held-out** | v3 | **18/27 (66.7%)** | **81.8%** | 6/7 |
| 3 | 25 | after tuning | v4 | 25/27 (92.6%) | 86.2% | 7/7 |
| **4** | 25 | **held-out** | v4 (final; = the code in this release, re-run to confirm) | **22/23 (95.7%)** | **81.5%** | 6/7 |

The bold rows are the honest numbers: each set was scored before anything was tuned on it.
- **Set 3 found real gaps.** Value-format changes (date and epoch formats, `@JsonFormat`), new required request fields and shared cache-key literals were all missed. v4 fixes these in general rules, not per scenario.
- **Set 4 measures v4.** Its one miss: when the frontend's SSE path changed, the tool didn't flag the gateway, which hard-codes that path in a proxy filter (`SseProxyFilter`).

**Where it errs:**
- **v1 and v3 mostly missed units:** 9 misses against 4 false alarms on each of sets 2 and 3.
- **v4 mostly over-flags:** 1 miss against 5 false alarms on set 4. The false alarms are usually the frontend, or a service that uses the same field name in a different contract (for example `rejectionReason` in risk-service).

Over-flagging only adds context for the critic. A miss is the costly error.

## Scale (synthetic, `impact/scale/`)

999 services and 3,266,064 lines of Java: the OMS copied 111 times with renamed services, topics, paths, schemas and ports. Every cluster's audit-service also consumes one topic from cluster 0, and every 10th service depends on a shared library.

| Measure | Result |
|---|---|
| Cold map of all 999 services (one-off, then cached by git tree hash) | 40 s, 71 MB (64 s extracting from git blobs) |
| Warm map | 0.8 s |
| Impact for one PR | 1.5–3.8 s |
| PR: rename a Kafka field (1 cluster) | 2 affected (the 2 consumers that read it) |
| PR: rename a field on a topic consumed by 110 other clusters | 113 affected; critic bundle 75 KB (detail for 25, names for the rest) |
| PR: log line only | 0 affected |
| PR: change a shared library | 99 affected (every dependent module) |
| Gates on changed services only (`--changed-from`) | 19 s |

Raw data: `set*/` (scenarios, both keys, results per run) and `scale-999-services.json`.

## Independent edge check (1.1.1)

`edges/truth.json` is a hand-built map of every OMS link. An agent wrote it by reading the code; it never saw `impact/`. `edges/score_edges.py` compares depmap against it:

| Link | Precision | Recall |
|---|---|---|
| Kafka (topic, service, role) | 16/16 | 16/16 |
| Service→service HTTP, REST calls only | 6/7 | 6/10 (the 4 misses are health checks built from a config map) |
| Service→service HTTP, incl. host:port config links | 10/11 | 10/10 |

The one false edge is api-gateway→auth-service, from a path string in `SecurityConfig`. The map also flags one **suspect** call, which is a real bug: execution-service calls `/api/v1/market/{symbol}`, which does not exist.

## Limits

- **Accuracy comes from one real codebase**, with 9 services and Spring/TypeScript conventions. The synthetic repo tests speed and fan-out only.
- **The same model family wrote the scenarios and the keys.** Changes from real PRs, and dependencies that escaped review in production, are the next test.
- **It works at text level, not type level.** See `impact/README.md`.
