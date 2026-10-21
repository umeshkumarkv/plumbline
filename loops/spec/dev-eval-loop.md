<!-- @copilot -->
---
agent: agent
description: Implement a JIRA story with self-review, tests and retry, then raise a PR (Plumbline Dev)
---

<!-- @end -->
# Dev Eval Loop — Plumbline

Implement a JIRA story with automated code-review evaluation and retry.
Runs implementation → evaluation → retry on failure — max 3 attempts.
On persistent failure after 3 attempts, escalates to human.

## Usage
```
/dev-eval-loop SCRUM-{n}
```
<!-- @copilot -->

Target: ${input:target:SCRUM-n}
<!-- @end -->

## How It Works

```
Attempt 1..3
  1 ORIGINATOR  implements / fixes the code, runs tests ◄─────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py dev (gates · impact · tests · coverage) ── FAIL  ┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · 12-category ── FAIL ────────────────┘ then BOTH stages re-run
        ↓ PASS
  commit, push, PR
After attempt 3 without PASS → ESCALATE → human (full attempt history, open + disputed items)
```
<!-- @copilot -->

---

## Copilot Runtime Conventions — read before anything else

- **Mode:** run in Copilot Chat **Agent** mode. Ask/Edit modes cannot call tools.
- **Subagents:** Stage 1 (originator) and Stage 3 (judge) run as isolated subagents from `.github/agents/`. They need a VS Code with custom-agent subagents and the **Run Subagent** tool (`agent/runSubagent`) enabled in this chat's tool picker. If it is missing, STOP before Stage 1 and tell the user (never do the originator's work in this chat); the judge has a new-chat fallback (`/plumbline-critic`).
- **Arguments:** use the value of `target` above (or text typed after the command) wherever this spec says `SCRUM-{n}`, `pr:{n}`, etc.
- **Atlassian tools:** before the first JIRA or Confluence call, call `getAccessibleAtlassianResources` once, keep the `cloudId`, and pass it on every Atlassian call. Tool names may carry a server prefix (e.g. `atlassian_getJiraIssue`) — use the tool whose name ends with the name written in this spec.
- **Approval gates:** wherever this spec says "Write Guard", print the approval block, then END YOUR TURN and wait for the user's next message. Only an explicit "yes" from the user counts. Copilot's own tool-confirmation dialog is NOT the approval.
- **Project rules:** Copilot does not load `CLAUDE.md` automatically. When this spec says read `CLAUDE.md` or `services/{service}/CLAUDE.md`, open and read the file.
- **Terminal:** run shell commands with the terminal tool from the repo root. Pre-flight once per session: `gh auth status` (if the spec uses `gh`) and `java -version` if the spec uses `mvn` or Gradle: the JDK must match the Java version the build declares (`<java.version>` / `maven.compiler.release` / `<release>` in pom.xml, or the Gradle toolchain), e.g. 17 or 21. A newer JDK is acceptable only if `./mvnw -q -DskipTests compile` (or `mvn …`) succeeds with it; on macOS a matching JDK can be selected with `export JAVA_HOME=$(/usr/libexec/java_home -v <version>)`. Onboarding reads code and only needs the JDK for the optional coverage scan (J8): if no suitable JDK is available, skip J8 and record it, do not stop. If `gh auth status` fails, or another loop has no suitable JDK, STOP and tell the user.
- **Demo login:** read `PLUMBLINE_DEMO_USER` and `PLUMBLINE_DEMO_PASSWORD` from the environment. If unset, STOP and ask the user to export them. Never print their values.
- **Reporting:** report execution time as written. Token counts are not available in Copilot — omit them.
<!-- @end -->

---

<!-- @claude -->
> **Demo login:** read `PLUMBLINE_DEMO_USER` and `PLUMBLINE_DEMO_PASSWORD` from the environment. If unset, STOP and ask the user to export them. Never print their values or write them into files, PRs or JIRA.

<!-- @end -->
## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: implementing code per the approved arch design on the JIRA ticket.

This agent **NEVER**:
- Makes architecture decisions
- Changes the data model, endpoint design, or Kafka/Redis strategy independently
- Adds new dependencies without CLAUDE.md approval
- Bypasses or modifies the arch design to work around a gap

### Design Gap Rule — HARD STOP

If implementation reveals a gap in the arch design (a field does not exist,
a comparison is between incompatible UUID domains, a security assumption is wrong,
or any AC cannot be implemented as designed), the Dev Agent MUST:

1. STOP immediately — do not implement a workaround
2. Post the gap to JIRA with full evidence (which field, which line, why it is wrong)
3. Escalate to the Arch Agent: "Run /arch-eval-loop SCRUM-{n} — design gap found"
4. Do NOT retry with a self-invented fix

A design gap is not a code problem. It is an architecture problem. The Arch Agent
must update the design. The Dev Agent then re-runs with the corrected design.

---

## JIRA Write Guard — Human Approval Required

<!-- @include shared/write-policy.md -->
Before performing ANY of the following operations, STOP and request explicit user approval:
- Adding or removing a label on any ticket
- Transitioning a ticket status

Approval format:
```
JIRA ACTION — AWAITING YOUR APPROVAL
  Ticket : SCRUM-{n}
  Action : {transition to "In Progress" | transition to "In Review" | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the JIRA write operation until the user types "yes".

---

## GitHub Write Guard — Human Approval Required

Before performing ANY of the following operations, STOP and request explicit user approval:
- `git push` to any remote branch
- `gh pr create` to raise a pull request

Approval format:
```
GITHUB ACTION — AWAITING YOUR APPROVAL
  Action  : {push branch "ai/SCRUM-{n}-{slug}" to origin | create PR "{title}" → develop}
  Branch  : ai/SCRUM-{n}-{slug}
  Reason  : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the git push or gh pr create until the user types "yes".

---

## Phase 0 — Pre-flight (all gates must pass before any code)

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Fetch the JIRA story using `getJiraIssue(SCRUM-{n})`
2. Extract: summary, description, acceptance criteria, tech constraints, blocked-by links, labels

### Gate 1 — Definition of Ready
- Must have label `plumbline-dor-ready` — if missing, STOP: "Run /ba-eval-loop first."
- Must have label `plumbline-arch-approved` — if missing, STOP: "Run /arch-eval-loop SCRUM-{n} first."
- Must NOT have label `plumbline-arch-blocked` — if present, STOP and show the blocking comment.

### Gate 2 — Blockers
3. Check every blocked-by ticket — if any is not Done, STOP and list the open blockers.

### Gate 3 — JIRA Transition
4. Apply the JIRA Write Guard, then transition JIRA: To Do → **In Progress**
5. Add JIRA comment: "Dev Eval Loop starting SCRUM-{n} — attempt 1 of 3."
6. Read `CLAUDE.md` fully (all sections)
7. Identify the service from the ticket
8. Read `services/{service}/CLAUDE.md` fully
9. Read `services/{service}/openapi.yaml` — extract exact endpoint path, HTTP method, request/response shape, field names, HTTP status codes
10. Check if branch `ai/SCRUM-{n}-*` already exists: `git branch -a | grep SCRUM-{n}`
    - If exists: `git checkout ai/SCRUM-{n}-{slug}`
    - If not: `git checkout develop && git pull origin develop && git checkout -b ai/SCRUM-{n}-{kebab-slug-of-summary}`
11. Save the originator's inputs (it has no JIRA access): write `.plumbline/review/{ticket}-story.md` (summary, description,
    ACs, tech constraints as fetched) and `.plumbline/review/{ticket}-design.md` (the full text of the approved Arch design
    comment on SCRUM-{n}, the one that set `plumbline-arch-approved`). If no such comment exists — Design Gap Rule, STOP.

---

## Eval Loop State

Initialize before the loop:
```
attempt      = 1
max_attempts = 3
all_findings = []   ← accumulated FAIL items across attempts
loop_passed  = false
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEV EVAL LOOP — Attempt {attempt} / {max_attempts}
Story : SCRUM-{n} — {summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_findings` is not empty, they go to the originator through the feedback file (Stage 1, step 2): every item
must be resolved before this attempt is evaluated.

<!-- @originator role=dev name={ticket}-dev tools=Read,Grep,Glob,Write,Edit,Bash net=build artifact="code and tests under services/ (and frontend/), uncommitted" inputs="the story in `.plumbline/review/{ticket}-story.md`; the approved design in `.plumbline/review/{ticket}-design.md`" -->
### Step B — Stage 1 Originator: Implement (always in this layer order)

1. **Domain** — add fields or new enum to JPA entity if needed
2. **Flyway migration** — `V{next}__description.sql` for any schema changes
3. **DTOs** — `dto/request/XxxRequest.java` and `dto/response/XxxResponse.java`
4. **Mapper** — MapStruct mapper in `mapper/XxxMapper.java`
5. **Repository** — new query methods in `repository/XxxRepository.java` if needed
6. **Service** — all business logic in `service/XxxService.java`; return DTOs, never entities
7. **Controller** — thin layer in `controller/XxxController.java`; delegate to service; use standard envelope
8. **Exception** — new `exception/XxxException.java` + update `GlobalExceptionHandler` if needed
9. **Config** — Resilience4j, RestTemplate, Redis config if this story requires external calls
10. **Tests** — unit tests for service + controller; cover every AC + every error path
    - **Stale spec rule:** if this story modifies or removes a feature that existing Playwright specs
      (`frontend/e2e/*.spec.ts`) assert, update those specs to match the new behavior in the same commit.
      A spec that asserts old behavior and now fails is a FAIL in Category 10 — do not leave it broken.

#### Mandatory standards — enforce every line

- BigDecimal for ALL monetary values — never double, float, long, int
- UUID for ALL primary keys — never Long, Integer, String
- Instant for UTC timestamps, LocalDate for date-only — never Date or Calendar
- @Enumerated(EnumType.STRING) on every enum field — never ORDINAL
- @RequiredArgsConstructor for DI — never @Autowired on fields
- @Slf4j on every class that logs — log IDs and states only, never PII or monetary values
- Standard response envelope: `{ "data": {}, "meta": { "timestamp": "...", "requestId": "..." } }`
- Standard error envelope: `{ "error": { "code": "...", "message": "..." }, "meta": {} }`
- Controller is thin — no business logic
- Service never returns JPA entities — always map to DTO first
- Write blocking code — never Mono/Flux/Reactor

### Step C — Run Tests

```bash
cd services/{service}
mvn test 2>&1 | tail -40
```

If `mvn test` fails:
- Read the failure output carefully
- Fix the root cause
- Run `mvn test` again (one fix attempt per loop attempt)
- If still failing after fix: record it in your fix log as open, stop, and return (the orchestrator evaluates)

```bash
mvn verify 2>&1 | grep -E "BUILD|JaCoCo|coverage|COVERED"
```

Record:
- test_result: PASS or FAIL (with failure count)
- jacoco_result: PASS (>= 80%) or FAIL (< 80%, with actual %)
<!-- @end-originator -->

### Step D — Evaluate: Stage 2 benchmark, then Stage 3 judge (isolated 12-category review)

Do NOT post to GitHub. This is a local evaluation only.

#### Rebuild the evidence yourself (orchestrator)

The test and coverage reports the benchmark reads must come from you, not from the originator. Delete them and re-run
the build for every changed module:
```bash
CHANGED=$( { git diff --name-only develop -- services; git ls-files -o --exclude-standard services; } \
  | cut -d/ -f1-2 | sort -u | paste -sd, -)   # e.g. services/order-service,services/client-service
[ -z "$CHANGED" ] || mvn -B -q clean verify -pl "$CHANGED" -am 2>&1 | tail -40   # `clean`: nothing in target/ survives
```
`clean` matters: `target/` is build output the scope check does not track, so reports, `jacoco.exec` and compiled test
classes left there by the originator must not reach the benchmark. A test or coverage failure here is a `BENCH:build`
item for the feedback file (skip to Step E). A compilation error is the Hard Stop below.

#### Stage 2 — Benchmark (deterministic, no LLM)

<!-- @include shared/three-stage.md -->
```bash
G=${AGENTIC_SDLC:-.agentic-sdlc}
python3 "$G/bench/run.py" dev --repo . --base develop --name {ticket}-dev
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_findings` as `BENCH:<id> — <detail>`, **skip the critic**, go to Step E.
- **Exit 0 (PASS):** continue to the critic; pass `.plumbline/review/{ticket}-dev-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: deterministic gates (Semgrep + structure + domain, 0 NEW against the baseline), the cross-service impact check (no BREAKING), surefire results (0 failures) for every changed service, JaCoCo >= 80%, a *Test for every changed Service/Controller/Consumer/Producer/Rule. The originator runs the tests in Stage 1 to get them green; the reports the benchmark reads come from the orchestrator's own `mvn verify` above.

<!-- @include shared/isolated-critic.md -->
The 12 categories below are the critic's rubric (`dev 12-category`). The critic marks PASS or FAIL with file:line evidence for each FAIL. You do not.

**Category 1 — Java Type Rules**
- [ ] No `double` or `float` for monetary values — must be `BigDecimal`
- [ ] No `Long` or `Integer` as primary key — must be `UUID`
- [ ] No `Date` or `Calendar` for timestamps — must be `Instant` or `LocalDate`
- [ ] All enum fields annotated `@Enumerated(EnumType.STRING)` — never `ORDINAL`
- [ ] BigDecimal comparisons use `compareTo()` — never `equals()`
- [ ] BigDecimal constructed from String — never from `double`

**Category 2 — Naming Conventions**
- [ ] All class names: PascalCase with correct layer suffix
- [ ] All method and variable names: camelCase
- [ ] All constants and enum values: UPPER_SNAKE_CASE
- [ ] All DB table/column names in migrations: snake_case
- [ ] All REST paths: kebab-case plural nouns
- [ ] JSON fields: camelCase

**Category 3 — Lombok**
- [ ] Entities: `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- [ ] Services/Consumers/Producers: `@RequiredArgsConstructor @Slf4j`
- [ ] Controllers: `@RequiredArgsConstructor`
- [ ] Response DTOs: `@Value @Builder` (immutable)
- [ ] Request DTOs: `@Data`
- [ ] No `@Autowired` on any field

**Category 4 — Dependency Injection**
- [ ] All dependencies via constructor (`@RequiredArgsConstructor`)
- [ ] No field injection
- [ ] No setter injection

**Category 5 — Architecture Boundaries**
- [ ] Controller contains zero business logic
- [ ] Service never returns JPA entities
- [ ] No cross-service database access
- [ ] No `ApplicationEvent` — Kafka only
- [ ] No `Mono`, `Flux`, or any Reactor type
- [ ] No `CompletableFuture` chains to avoid blocking

**Category 6 — API Standards**
- [ ] All success responses: `{ "data": {...}, "meta": {...} }`
- [ ] All error responses: `{ "error": {...}, "meta": {} }`
- [ ] Monetary values serialised as JSON String
- [ ] Timestamps: ISO 8601 UTC
- [ ] Base path: `/api/v1/{resource}` — plural nouns

**Category 7 — Entity Column Conventions**
- [ ] All required fields: `@Column(nullable = false)`
- [ ] All enum fields: `@Enumerated(EnumType.STRING)`
- [ ] All BigDecimal fields: `@Column(precision = 19, scale = 4)`
- [ ] Audit fields present: `createdAt` (not updatable) and `updatedAt`

**Category 8 — Logging**
- [ ] All logging uses `@Slf4j`
- [ ] No passwords, tokens, or secrets in any log statement
- [ ] No PII in log statements
- [ ] No monetary values logged at INFO or above

**Category 9 — Exception Handling**
- [ ] Custom exceptions extend `RuntimeException`
- [ ] Custom exceptions carry machine-readable `errorCode`
- [ ] `GlobalExceptionHandler` with `@RestControllerAdvice` exists
- [ ] No stack traces in API responses
- [ ] No `throw new RuntimeException("message")` from business logic

**Category 10 — Testing**
- [ ] Unit test for every public service method
- [ ] Controller test covers: 200/201/202, 404, 400/422
- [ ] Tests use `@ExtendWith(MockitoExtension.class)` or `@WebMvcTest`
- [ ] Test method names: camelCase, descriptive
- [ ] If story modifies or removes frontend-visible behavior: all `frontend/e2e/*.spec.ts` tests
  that asserted the old behavior have been updated or removed in this commit

**Category 11 — Security**
- [ ] No hardcoded credentials or secrets
- [ ] No stack traces in API responses (GlobalExceptionHandler)
- [ ] No raw SQL with string concatenation

**Category 12 — Flyway Migrations**
- [ ] Migration file: `V{n}__{description}.sql` (double underscore)
- [ ] Migration only modifies this service's own schema
- [ ] No `DROP TABLE` or `TRUNCATE`
- [ ] Idempotent where possible (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`)

### Step E — Decision

Collect this attempt's findings:
```
attempt_findings = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
                 + [all FAIL items from categories 1–12 + test_result FAIL + jacoco FAIL]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition** — ALL of the following:
- Stage 2 benchmark verdict: PASS
- Categories 1–5: zero failures (zero-tolerance categories)
- Categories 6–12: zero failures
- test_result: PASS (0 test failures)
- jacoco_result: PASS (>= 80%)

Print evaluation scorecard:
```
EVAL SCORECARD — Attempt {attempt}
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/review/{name}-benchmark.md)
  Cat 1 Type Rules      : {PASS | FAIL — n violations}
  Cat 2 Naming          : {PASS | FAIL — n violations}
  Cat 3 Lombok          : {PASS | FAIL — n violations}
  Cat 4 DI              : {PASS | FAIL — n violations}
  Cat 5 Architecture    : {PASS | FAIL — n violations}
  Cat 6 API Standards   : {PASS | FAIL — n violations}
  Cat 7 Entity Cols     : {PASS | FAIL — n violations}
  Cat 8 Logging         : {PASS | FAIL — n violations}
  Cat 9 Exceptions      : {PASS | FAIL — n violations}
  Cat 10 Testing        : {PASS | FAIL — n violations}
  Cat 11 Security       : {PASS | FAIL — n violations}
  Cat 12 Migrations     : {PASS | FAIL — n violations}
  mvn test              : {PASS | FAIL}
  JaCoCo coverage       : {PASS — nn% | FAIL — nn%}

  VERDICT : {PASSED — proceed to commit/push | FAILED — {n} violations}
```

**If PASSED:**
- Set `loop_passed = true`
- Exit the loop → go to Phase 1 (Commit and Push)

**If FAILED and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_findings` to `all_findings`
- Increment `attempt`
- Add JIRA comment: "Dev Eval Loop attempt {prev_attempt} FAILED — {n} violations. Starting attempt {attempt}."
- Return to LOOP start (Step A)

**If FAILED and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — Commit and Push (reached only on PASS)

Stage only the files changed for this ticket:

```bash
git add services/{service}/src/... [list specific files]
git commit -m "$(cat <<'EOF'
feat({service}): {short description} — SCRUM-{n}

- {bullet: what was added/changed}
- {bullet: what was added/changed}
- Eval loop: passed on attempt {attempt}/{max_attempts}

{{ai_attribution}}
EOF
)"
```

Apply the **GitHub Write Guard**, then:
```bash
git push -u origin ai/SCRUM-{n}-{slug}
```

---

## Phase 2 — Pull Request

Apply the **GitHub Write Guard**, then:

```bash
gh pr create \
  --title "feat({service}): {summary} — SCRUM-{n}" \
  --base develop \
  --body "$(cat <<'EOF'
## Summary

- [SCRUM-{n}]({jira-url}) — {one-line description}
- Eval loop: {attempt} attempt(s) — passed on attempt {attempt}/{max_attempts}
{if attempt > 1: list what was fixed between attempts}

## Test plan

- [ ] {AC 1 from ticket}
- [ ] {AC 2 from ticket}
- [ ] Unknown ID returns 404
- [ ] JaCoCo coverage >= 80%

## curl test guide

\`\`\`bash
export TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$PLUMBLINE_DEMO_USER\",\"password\":\"$PLUMBLINE_DEMO_PASSWORD\"}" | jq -r '.data.token')

curl -s http://localhost:8080/api/v1/{resource}/{id} \
  -H "Authorization: Bearer $TOKEN" | jq .
\`\`\`

---
Generated by Dev Eval Loop for SCRUM-{n}
EOF
)"
```

---

## Phase 3 — JIRA Close-out

1. Apply the JIRA Write Guard, then transition JIRA: In Progress → **In Review**
2. Add JIRA comment: "Dev Eval Loop PASSED on attempt {attempt}/{max_attempts}. PR raised: {pr_url}"

---

## Phase 4 — Summary to User

```
DEV EVAL LOOP — SCRUM-{n} COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story      : {summary}
Branch     : ai/SCRUM-{n}-{slug}
PR         : {pr_url}
JIRA       : In Review
Tests      : PASSED
Coverage   : >= 80%
Eval Loop  : Passed on attempt {attempt} / {max_attempts}
{if attempt > 1: Fixed between attempts: {list of what changed}}

Next step  : /qa-eval-loop SCRUM-{n}  (after code review approves PR)

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
<!-- @claude -->
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
<!-- @end -->
```

---

## Escalation — reached when all 3 attempts fail

```
DEV EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCRUM-{n} failed evaluation after {max_attempts} attempts.

Persistent violations (across all attempts):
{numbered list of all_findings with file:line references}

Human action required:
1. Review the violations above
2. Either fix manually or provide clarifying constraints
3. Re-run /dev-eval-loop SCRUM-{n} after clarification
```

Post to JIRA as a comment (informational — no approval needed under the Plumbline write policy; any label or transition that follows still needs the Write Guard):
```
Dev Eval Loop ESCALATED — SCRUM-{n}
Failed after 3 attempts. Persistent violations:
{all_findings}
Human review required before retry.
```

STOP — do not push or raise PR.

---

## Hard Stops — always pause and ask the user

- Any blocked-by ticket is not Done
- Acceptance criteria are ambiguous or contradictory
- A new Maven dependency needs to be added (CLAUDE.md must be updated first)
- A schema change would affect another service's tables
- The ticket asks for something in CLAUDE.md Section 18 (Out of Scope)
- `mvn test` fails with a compilation error (not a logic failure) — cannot evaluate
