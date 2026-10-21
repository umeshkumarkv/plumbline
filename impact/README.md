# impact — which other services does this change affect?

The answer to "LLMs can't review a monorepo with 1,000 services". A reviewer, human or LLM, does not need the
whole repo. It needs **the diff plus the contracts that diff touches and the code on the other side of them**.
Finding those is a graph problem, and graphs are deterministic code, not prompts.

```
PR diff ──► depmap (per service, cached by git tree hash) ──► contract diff ──► key filter ──► affected services
                                                                                          └─► impact.md for the critic
```

## What it maps (no LLM)

| Link | How it is found |
|---|---|
| Kafka | `KafkaTemplate.send` / `@KafkaListener`. Topics come from literals, constants or `${property}`. The contract is the sending/listening **method** (incl. private helpers it calls) + payload class + types it references |
| REST | Controller mappings (verb + path) + request/response DTOs, incl. DTOs only named in the method body. Calls: `"/api/..."` literals incl. `"/a/" + id + "/b"`, TS template literals, axios `baseURL`, HTTP verb |
| Gateway | `Path=` predicates → target host |
| Config | `host:port` references (yml, Java defaults, nginx, vite) → owning service by name or port |
| JWT | issuers (`Jwts.builder`) → verifiers (`Claims`, `parseSignedClaims`) |
| DB | SQL literals naming another service's schema |
| Build | internal Maven module dependencies |
| Shared literals | namespaced strings such as cache-key prefixes are found by `git grep` across the repo |

## How "affected" is decided

1. Diff the contract fingerprints of base and head. Fingerprints ignore comments, whitespace and logging.
2. Compute the **keys** that changed:
   - renamed or removed fields, Map keys, headers, claims and enum values;
   - fields whose type or format changed (`@JsonFormat`, the mapper expression, the builder value);
   - `@JsonProperty` names (renaming only the Java field is silent).
3. A counterpart is affected if it **reads** one of those keys. Reading includes `get("k")`, `getK()`, `obj.k`, `case K` and `"K".equals`, and a DTO field that the unit reads anywhere.
4. Some changes affect every counterpart regardless of keys:
   - a request body changed;
   - an endpoint or topic disappeared (marked **BREAKING**);
   - the change gives no key-level detail.

## Use

```bash
# CI / large repos: maps come from git tree hashes and the cache; only changed services are extracted
python3 impact/impact.py --repo . --base origin/develop --cache ~/.cache/plumbline-impact \
    --json impact.json --bundle impact.md [--fail-on-breaking]
# two directories
python3 impact/impact.py --base-dir OLD --head-dir NEW --json impact.json --bundle impact.md
# the map itself
python3 impact/depmap.py . --ref HEAD --cache ~/.cache/plumbline-impact -o depmap.json
```

`impact.md` goes to the isolated critic as `IMPACT` (see `loops/shared/isolated-critic.md`, `gates/ci/critic.yml`).
`--fail-on-breaking` makes it a deterministic gate in `gates/ci/guardrails.yml`.

## Measured (details: `eval/impact/RESULTS.md`)

- **Accuracy on the OMS:** 4 sets of 25–30 realistic changes, written by agents that never saw the tool. Each was scored against two independent answer keys. Recall on the three held-out runs, each scored before any tuning on that set: **77.5% → 66.7% → 95.7%** as the tool improved; precision **82–89%**. The earlier versions mostly *missed* units (9 misses vs 4 false alarms on each of sets 2 and 3). The final version mostly *over-flags*: 1 miss vs 5 false alarms on set 4.
- **Scale:** 999 services and 3.27 M lines of Java, synthetic (the OMS copied 111 times with renames):

| Measure | Result |
|---|---|
| Cold map (one-off; 64 s when extracting from stored git blobs) | 40 s, 71 MB |
| Warm map | 0.8 s |
| Impact per PR | 1.5–3.8 s, ≤ 140 MB |
| Gates on changed services only (`--changed-from`) | 19 s |
| Critic bundle size | ≤ 75 KB (fan-outs over 25 services are summarised) |

## CI safety

- PR workflows only **restore** the cache. It is written by `gates/ci/impact-cache.yml` from merged commits.
- Units are extracted from stored git blobs, not the working tree, whenever the repo has `.gitattributes`. Attribute rules (encodings, filters) can't change what the map sees.
- `.gitattributes` is a protected path.
- The gates fail closed on any source file that isn't plain UTF-8.
- A service is identified by `spring.application.name`, so moving its folder is not a change.

## Limits

- Java/Spring + TypeScript conventions only. Other stacks need their own extractors (same design).
- Text-level, not type-level: a key shared by unrelated contracts can cause a false alarm, and a contract expressed
  without any of the patterns above (reflection, generated clients, dynamic topic names) is invisible.
  `depmap` lists unresolved calls; treat a high unresolved count as a coverage gap. It also prints **suspect** calls:
  a runtime path segment that only lines up with fixed endpoints usually means the call hits nothing.
- Accuracy was measured on one codebase (9 services). The synthetic scale test measures speed and fan-out, not accuracy.
