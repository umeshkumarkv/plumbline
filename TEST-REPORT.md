# Plumbline 2.2.0 — test report (2026-10-27)

Claude Code 2.1.309, headless (`claude -p`), on clean git copies of two real repositories:
**candidate-review-system** (Spring Boot + SQLite backend at the repo root, Angular `ui/`) and **broker-dealer**
(9 Spring Boot services + React/Vite frontend). Every result below was checked by hand against the code or the
running system, not taken from the agent's summary.

## 1. Every command does real work (positive runs)

| Command | Repository | Input | Result | Time | Cost |
|---|---|---|---|---|---|
| `/pl-onboard` | candidate-review-system | all units | 3/3 files PASS (backend on attempt 2) | 4m | $1.61 |
| `/pl-onboard` | broker-dealer | order-service, frontend | 3/3 files PASS (order-service on attempt 2: invented Maven wrapper removed) | 4m | $1.50 |
| `/pl-pm` | candidate-review-system | "alert at 30 days on bench" | PRD PASS on attempt 2 (attempt 1: a P3 item contradicted Out of scope) | 2m | $0.50 |
| `/pl-ba` | broker-dealer | "show today's orders and remaining daily limit" | 5 stories across 3 units, all PASS; an 8-point story was split in three | 6m | $2.81 |
| `/pl-arch` | broker-dealer | SCRUM-610 daily-usage API | PASS on attempt 2 (attempt 1 compared a *user* id with a *client* id) | 5m | $1.45 |
| `/pl-dev` | candidate-review-system | CRS-210 admin-only GC endpoint | PASS on attempt 1; Maven unreachable here, said so up front | 2m | $0.47 |
| `/pl-code-review` | broker-dealer | branch with 6 planted defects | FAIL — **6/6 caught** + an unplanted NPE on MARKET orders | 44s | $0.27 |
| `/pl-qa` | broker-dealer (frontend running) | SCRUM-501 max quantity | 4/4 ACs + 6 edge cases PASS, real Playwright run | 4m | $0.47 |
| `/pl-doc` | broker-dealer | merged PR #77 (new endpoint) | spec + CLAUDE.md updated, PASS on attempt 1 | 1m | $0.44 |
| `/pl-devops` | broker-dealer | red CI from a "refactor" | one-line code fix, no test touched, flaky test reported | 4m | $0.44 |
| `/pl-sm` | broker-dealer | sprint CSV export | standup PASS on attempt 1; every list matches the data | 1m | $0.35 |

**Hand checks that matter**
- **QA** logged in through the real UI, typed boundary values, forced a click and Enter on the disabled button; the
  stand-in gateway's order log shows exactly **one** order, quantity **1,000,000** (AC3), none for 1,000,001. No
  password or token in the evidence.
- **Onboarding** changed nothing outside its markers (broker-dealer: only a missing final newline). No secret
  values copied into docs. Real findings: crs `permitAll("/**")`, a hard-coded SQL key, a dead `AuthGuard`, plain-text
  secrets; broker-dealer gateway on 9090 not 8080, 9 of 24 Level-2 checks coded.
- **Arch** found a genuine design gap: broker-dealer has no link between a trader's login and a client, so "a trader
  sees only their own client" cannot work today. The design names it as a prerequisite needing architect sign-off.
- **Doc** documented the real behaviour of the new endpoint (bad input → 500, not 400) instead of an invented 400.
- **DevOps** classified the 4th failure as pre-existing/flaky (not on main, file untouched) and left it alone.

## 2. Every judge rejects bad work (negative runs)

Each role's judge got deliberately flawed work with the role's checklist.

| Role | Planted defects | Caught |
|---|---|---|
| onboard | 2 invented endpoints, invented table, deleted human line | 3/3 |
| pm | vague problem, unmeasurable criterion, out-of-scope item in P1, 32 P1 points, TBD, missing out-of-scope | 6/6 |
| ba | generic role, untestable ACs, other unit's database, 13 points, out-of-scope feature, non-existent endpoint/tables | 6/6 |
| arch | money as number, migration V7 already taken, cross-schema join, non-existent risk endpoint, no access rules, UTC day, 1 test | 7/7 |
| dev | ACs not implemented, test skipped, unrelated change | 3/3 |
| qa | PASS on status code only, PASS on "button exists", skipped AC without reason, password in evidence, guessed cause | 5/5 |
| doc | POST instead of GET, unrelated section deleted, root CLAUDE.md changed, invented 400 | 4/4 (after fix 4) |
| devops | test suite skipped, coverage threshold lowered, root cause not fixed | 3/3 |
| sm | missing Done ticket, missed at-risk, missed blocked, missed unassigned, wrong velocity, DoD wrongly "met", blame | 7/7 |
| **Total** | | **47/47** |

The earlier code-review control (a clean branch) passed with no false alarms.

## 3. One feature, end to end, with the agents (broker-dealer)

Goal given to `/pl-pm`: *find the most important gaps between the domain rules in the root CLAUDE.md and what
order-service implements, and propose a feature that closes the highest-impact one.* Each step was fed the previous
step's output; a person only answered one question (base branch = main).

| Step | Command | Output | Judge | Time | Cost |
|---|---|---|---|---|---|
| 1 | `/pl-pm` | PRD: order-service does not enforce the section-5 state machine — a replayed `execution.completed` can move NEW → FILLED, skipping risk. 10+ other gaps tabled | PASS, attempt 1 | 2m | $0.76 |
| 2 | `/pl-ba` | 5 stories (16 points), blocked-by chain; flagged that root CLAUDE.md (develop, `ai/BD-*`) and settings (main, SCRUM) disagree | 5/5 PASS | 3m | $2.25 |
| 3 | `/pl-arch` ×2 | Designs for story 1 (transition table, exhaustive switch, exception) and story 2 (enforce before save/publish; consumer logs and skips, no DLT) | PASS, attempt 1 | 5m | $1.45 |
| 4 | `/pl-dev` | Branch `ai/SCRUM-702-…`: `OrderStatus.canTransitionTo`, `InvalidOrderTransitionException`, guarded `transitionState`, consumer handling; 4 test files, nothing deleted | PASS | 3m | $0.99 |
| 5 | `/pl-code-review` | PASS, 2 minor (risk-rejection path still sets status directly — story 3; no REST mapping for the new exception) | — | 1m | $0.33 |
| 6 | `/pl-doc` | order-service CLAUDE.md: table, enforcement, where it surfaces; two open questions recorded honestly | PASS, attempt 1 | 2m | $0.44 |
| | | **9 files, +640 / −10** | | **~15m** | **~$6.20** |

**Hand checks:** the gap is real (`transitionState` saved and published any target state). The new
`OrderStatus` and exception were compiled with plain `javac` and checked against all 121 status pairs: **0
mismatches** with the table in root CLAUDE.md section 5 (12 allowed, 109 refused, null refused). The check runs
before any save or publish; the risk-passed chain stays legal step by step. **Not run:** the JUnit tests and the
Kafka/docker checks — Maven Central is blocked here; run `mvn -pl services/order-service test` before merging.

## 4. The same, on candidate-review-system (backend + UI)

Fresh copy of `main`, Plumbline 2.2 copied in, then `/pl-onboard`. Goal given to `/pl-pm`: *find the most important
gaps between the documented domain rules and what the code implements, and propose a feature that closes the
highest-impact one.* No person answered anything; every step got the previous step's files.

| Step | Command | Output | Judge | Time | Cost |
|---|---|---|---|---|---|
| 0 | `/pl-onboard` | root + backend + ui CLAUDE.md | 3/3 PASS | 4.5m | $1.81 |
| 1 | `/pl-pm` | PRD: `salesforce_mapping.md` says a loss reason is mandatory when the stage is *Opportunity Lost*; the backend never checks it, and the UI forces a closure category on **every** position, so users pick meaningless values | PASS, attempt 1 | 2.6m | $0.81 |
| 2 | `/pl-ba` | 5 stories (CRS-301…305: backend rule, billing-date rule, UI, backend tests, UI specs). Caught that the PRD's target form `OpenPositionFormComponent` has no route (dead code) and re-pointed the UI story to the real screens; raised it from 3 to 5 points | 5/5 PASS (2 on attempt 2) | 5.7m | $3.10 |
| 3 | `/pl-arch` ×2 | Backend design (301+302): check before any setter, because `updatePosition` does not roll back on `CommonException`; PUT gets 400 `{message}` like the other endpoints. UI design (303): stage matched by name, not id | PASS, attempt 1 each | 6m | $1.90 |
| 4 | `/pl-dev` | Branch `ai/CRS-303-…`: rule on create / PATCH / PUT, billing window, UI validators and readable API errors; 2 backend test classes, 1 UI spec | PASS, attempt 1 | 4m | $1.50 |
| 5 | `/pl-code-review` | PASS, 2 minor (no component specs for the forms; Lost check skipped for an inactive stage id — intentional, commented) | — | 0.8m | $0.29 |
| 6 | `/pl-doc` | backend and ui CLAUDE.md: the rule, the real error bodies, which endpoints still give a 500 | PASS, attempt 1 | 1.4m | $0.45 |
| | | **14 files, +792 / −19** | | **~25m** | **~$9.90** |

**Hand checks:** the gap is real (`validate()` checks only SOW Signed and Opportunity Revisit; the UI had
`Validators.required` on closure category always). Every method, field and type the backend change uses exists
(`findByOpportunityIdOrderByPositionSequence`, `Integer closureCategoryId`, `LocalDate` billing dates); the Lost
check in `updatePosition` runs before any setter. The UI spec runs **25/25**; two planted mutants in the helper
(`<` → `<=` on billing dates, `===` → `!==` on the Lost stage) are caught (3 and 4 failures). The doc's claim that
`GlobalExceptionHandler` maps only bean-validation errors was checked against the class.
**Not run:** the backend JUnit tests (Maven Central blocked here) — run `./mvnw test` before merging. `/pl-qa` was
skipped: it needs the running backend.

**Operator mistake worth knowing:** the first `/pl-code-review` was told only about the UI story, so it flagged the
backend half as out of scope (correct for what it was told). When a branch carries several stories, name all of them.

## 5. Problems found and fixed in this round
1. `/pl-doc` judge accepted an invented 400 as "minor, not checked" → must trace each documented error code to its
   handler.
2. A helper ran in the background and the command reported "still waiting" as if finished → helpers run in the
   foreground; the command waits for each result.
3. Claude Code refused the SM writer's `report.md` ("subagents should return findings as text") → draft renamed
   `standup.md`; every helper can return `FILE: <path>` content for the command to save.
4. Orchestrators still sometimes run `grep`/`mkdir` themselves. Works in Claude Code (bash/Git Bash); the rule
   against it stays. Watch this in Copilot on Windows.

## 6. Not tested
- **GitHub Copilot** (no Copilot login here; VS Code allows clicks only). Files match VS Code's documented format.
- **Backend builds** — Maven Central is blocked in the test environment; dev and QA stories used the frontends, and
  `/pl-dev` on a backend story reported honestly that tests could not run.
- **Windows.**
- QA ran against the real frontend with a **stand-in API** for the Java services.
