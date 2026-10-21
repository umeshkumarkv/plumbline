# bench — Stage 2 of every Plumbline loop

Every eval loop runs three stages:

```
ORIGINATOR (agent writes the artifact) ─► BENCHMARK (bench/run.py, deterministic) ─► JUDGE (isolated critic)
                                              │ FAIL → back to the originator; the judge is not called
                                              └ PASS → report goes to the judge as facts
```

The loop passes only if **both** the benchmark and the judge pass. The judge never re-checks what the benchmark
measured. It spends its effort on what code cannot measure.

```bash
python3 bench/run.py <agent> [inputs] --name <prefix>   # writes .plumbline/run/review/<prefix>-benchmark.{json,md}
```

| Agent | Inputs | What the benchmark measures (no LLM) | What the judge keeps |
|---|---|---|---|
| pm | `--artifact prd.md --repo .` | 6 sections, named owner, gap/impact, ≥2 verifiable criteria, dependency lines, no §18 item in P1–P3, P1 ≤ 20 pts, no placeholders | problem specificity, value, domain fit |
| ba | `--artifact story.md --repo . [--facts]` | summary format, role, every AC = method+path+status, 200/404/400 coverage, points ∈ {1,2,3,5,8}, tech constraints, service exists and is the only one, port = code, AC paths route to the service, seed table exists, no §18 | right slice, right ACs |
| arch | `--artifact design.md --story story.md --repo .` | 9 blocks, service/port/schema = code, gateway route, next free migration, external calls hit real endpoints, consumed topics have a producer, AC error statuses have codes, ≥3 tests/layer, RBAC, headers | design quality, trade-offs, NFRs, identity domains |
| dev | `--repo . --base develop` | gates (0 NEW), impact (no BREAKING), surefire 0 failures, JaCoCo ≥ 80%, a test per changed class | logic, domain correctness, test quality |
| code-review | `--repo <worktree> --base origin/develop --pr N` | everything dev measures at the reviewed SHA + protected paths + CI checks green | 12-category audit beyond the gates |
| qa | `--results qa-results.json --story story.md [--replay]` | every AC has evidence, verdict = expected vs actual, envelope, money as string, screenshots, 4 edge cases, GETs reproduce on replay | assertions prove the AC, DB/Kafka evidence |
| devops | `--repo . [--branch b]` | YAML, pinned actions, no curl\|sh, checksums, permissions, no PR code under `pull_request_target`, no secrets, pinned images, actionlint, CI green | root cause, minimality, rollback |
| sm | `--artifact standup.md --facts sprint-facts.json` | sections, lists = what the data implies, flags, velocity, DoD on GitHub | honesty, prioritisation |
| doc | `--repo . --base develop --service s` | openapi parses, touched endpoints documented (older gaps = debt), money `type: string`, topics/env vars/new deps in CLAUDE.md, links | clarity, accuracy |
| onboard | `--artifact CLAUDE.md --repo . --service s` | 11 sections; port/schema; endpoints, topics, downstream calls, entities, tables, Redis prefixes both documented (coverage) **and** real (no invented facts) | usefulness, business rules |

Result per check: `PASS`, `FAIL` (fails the stage), `WARN` (for the judge to weigh), `SKIP` (with the reason).
`source: supplied` marks checks that rest on data the originator provided (e.g. a JIRA export). The judge may question them.

Exit codes: `0` PASS, `1` FAIL, `2` usage error (wrong command or missing input; not a gap).

`scope_check.py` runs before the benchmark. `snapshot --name N --writable "ARTIFACT…"` records the working tree (including gitignored files and `.plumbline/run/`) and every git ref, stores the snapshot outside the repository and prints `SNAPSHOT <path> <sha256>`. After the originator returns, `check <role> --snapshot <path> --sha <sha>` fails (exit 1) on: a path outside the role's allowed paths, a protected control file, any `.plumbline/run/` file other than the artifact and `.plumbline/run/work/N/fixlog.md`, a moved ref, a test/coverage change in a `pom.xml`, or a tampered snapshot. Each violation is a `SCOPE:` feedback item.

Self-test: `python3 selftest/bench_selftest.py`. Each agent has a good and a bad fixture in `selftest/bench-fixture/`.
The bad fixture must fail on exactly its planted checks.
