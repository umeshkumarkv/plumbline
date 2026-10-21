# Dev Eval Loop — Plumbline

Implement a JIRA story with automated code-review evaluation and retry.
Runs implementation → evaluation → retry on failure — max 3 attempts.
On persistent failure after 3 attempts, escalates to human.

## Usage
```
/plumbline-dev SCRUM-{n}
```

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

---

> **Demo login:** read `PLUMBLINE_DEMO_USER` and `PLUMBLINE_DEMO_PASSWORD` from the environment. If unset, STOP and ask the user to export them. Never print their values or write them into files, PRs or JIRA.

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
3. Escalate to the Arch Agent: "Run /plumbline-arch SCRUM-{n} — design gap found"
4. Do NOT retry with a self-invented fix

A design gap is not a code problem. It is an architecture problem. The Arch Agent
must update the design. The Dev Agent then re-runs with the corrected design.

---

## JIRA Write Guard — Human Approval Required

> **Plumbline write policy (applies to every agent).** JIRA *comments* are informational and need no approval.
> Always approval-gated: adding/removing labels, transitioning status, creating issues or Confluence pages,
> `git push`, `gh pr create`, `gh pr review` (approve / request-changes / overall comment), and any write to a CLAUDE.md file.

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
- Must have label `plumbline-dor-ready` — if missing, STOP: "Run /plumbline-ba first."
- Must have label `plumbline-arch-approved` — if missing, STOP: "Run /plumbline-arch SCRUM-{n} first."
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
11. Save the originator's inputs (it has no JIRA access): write `.plumbline/run/review/{ticket}-story.md` (summary, description,
    ACs, tech constraints as fetched) and `.plumbline/run/review/{ticket}-design.md` (the full text of the approved Arch design
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

### Stage 1 — Originator: the `plumbline-dev-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the story in `.plumbline/run/review/{ticket}-story.md`; the approved design in `.plumbline/run/review/{ticket}-design.md`
2. **Feedback file (attempt 2+).** Write `.plumbline/run/work/{ticket}-dev/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/run/work/{ticket}-dev/brief.md`: the task in one paragraph, the input file paths, the artifact
   `code and tests under services/ (and frontend/), uncommitted`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/run/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${PLUMBLINE_HOME:-.plumbline}
   python3 "$G/bench/scope_check.py" snapshot --name {ticket}-dev --writable "" --role dev
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-dev-originator` and the prompt `Brief: .plumbline/run/work/{ticket}-dev/brief.md`.
   Pass nothing else: not your reasoning, not the judge's free text.
   Then run the `CHECK:` command **exactly as printed** (copy it; do not retype the sha). It verifies the sha of the
   snapshot and checker copy with Python (works on macOS and Linux) and runs the check; exit 1 = violations or tampering.
   `<dir>` holds the snapshot and a private copy of the checker outside the repository; the sha check proves neither
   was swapped while the originator ran.
   **Exit 1:** each `SCOPE:` line is a violation. Revert it (restore the file, delete what was added, reset a moved ref),
   carry the items into the feedback file, and count the attempt as failed. **Exit 0:** continue.


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

#### Three stages: ORIGINATOR → BENCHMARK → JUDGE

Every attempt of this loop runs three stages, in this order. They are separate roles. This command is the **orchestrator**:
it fetches inputs into files, calls the originator, runs the benchmark, calls the judge, routes feedback, counts attempts,
escalates, and makes every external write (JIRA, GitHub, Confluence) only after both stages pass and a human approves.

| Stage | Who | What it decides | Sees |
|---|---|---|---|
| 1. Originator | the `plumbline-<role>-originator` subagent this orchestrator calls (Claude Code: `.claude/agents/`; Copilot: `.github/agents/`) | produces or revises the artifact | the brief, the input files, the rulebook, the feedback (attempt 2+) |
| 2. Benchmark | `bench/run.py` (deterministic, no LLM) | measurable facts: PASS / FAIL / WARN per check | the artifact + the repo / CI / supplied facts |
| 3. Judge | the isolated `plumbline-critic` | what code cannot measure: correctness, completeness, quality | the artifact, the benchmark report, the rubric, the rulebook. **Never** your reasoning or drafts |

**Every run starts at attempt 1.** The attempt counter lives only in this run, never in files. If `.plumbline/run/work/{name}/`
exists from an earlier run, move it to `.plumbline/run/work/{name}/previous-<YYYYMMDD-HHMM>/` before Stage 1 (keep it as history;
do not read its attempt number). Existing drafts in `.plumbline/run/review/` are the starting artifact for attempt 1, and the
last run's open findings (from its escalation or feedback file) go into attempt 1's feedback file.

Rules
1. **Benchmark first.** Run Stage 2 as soon as the artifact is written. If its verdict is **FAIL**, this attempt
   fails: every FAIL check becomes a gap (`BENCH:<check id> — <detail>`), **skip Stage 3** and go to the Decision
   step. Fixing those needs no LLM opinion, and the judge's time is spent only on artifacts that are measurably sound.
2. **The judge gets the report as facts.** Pass `.plumbline/run/review/{name}-benchmark.md` to the critic as `BENCHMARK`.
   The judge does not re-check what the benchmark measured; it judges what it could not. WARN items are for the
   judge to weigh. Checks marked `supplied` depend on data you provided (e.g. JIRA): the judge may question them.
3. **Both must pass.** The loop passes only if the benchmark verdict is PASS **and** the judge verdict is PASS.
   The judge cannot override a benchmark FAIL; a benchmark PASS is not an approval.
4. **Never weaken the benchmark.** Do not edit `bench/`, its fixtures, the gates, the baseline or the rulebook to turn
   a check green. A wrong check is reported to the user as a benchmark defect, with the evidence.
5. **Exit code 2** (usage error: missing artifact or input) is your mistake, not a gap: fix the command and re-run.

#### Feedback loop — how a failed attempt is fixed (at least 3 attempts before a human)

```
attempt 1..3:  ORIGINATOR writes / revises ──► BENCHMARK ──PASS──► JUDGE ──PASS──► done (handoff)
                     ▲                             │ FAIL            │ FAIL
                     └──── failing checks ─────────┘                 │
                     └──── findings: rule · location · fix ──────────┘
after attempt 3 without PASS ──► ESCALATE to a human with the full history
```
1. **What goes back to the originator:** exactly the failing benchmark checks (`BENCH:<id>`, detail, evidence) and the
   judge's findings (`JUDGE:<id>`, rule, `path:line` + quote or what is missing, required fix). Never the critic's free
   text, and never a verdict to aim for.
2. **The originator fixes each item** in the artifact and writes `.plumbline/run/work/{name}/fixlog.md`, one line per item:
   `<id> — fixed: <what changed, where>` or `<id> — disputed: <evidence>`. A disputed item stays open. The originator
   may not delete or weaken a rubric item, test or check to close a finding.
3. **The next attempt re-runs both stages in full.** The benchmark re-runs every check, so a fix that breaks something
   else is caught. The judge runs again in a **new** context. It gets the revised artifact, the new benchmark report and
   `PRIOR_FINDINGS` (ids, rules, locations only) to mark each RESOLVED or STILL PRESENT. It never gets the fix log.
4. **At least 3 attempts.** `max_attempts = 3`. A loop escalates only when attempt 3 still fails, or at once on one of
   its Hard Stops (decisions only a human can make: missing design, blocked dependency, scope outside CLAUDE.md).
   If attempt 2 fails on the same items as attempt 1, attempt 3 must take a different approach and say which.
5. **The escalation report** lists, per attempt: the benchmark verdict and failing checks, the judge's findings, and what
   the originator changed. It then lists the items still open, disputed items with both sides' evidence, and the
   decision needed from the human. Nothing is written to JIRA, GitHub or Confluence as approved.

Exceptions: `/plumbline-devops` pushes its fix to the feature branch before Stage 2 because its evidence is a CI run
(never to `main`/`develop`, nothing merged). `/plumbline-code-review` has no originator: the PR under review is the
artifact, so it runs Stages 2 and 3 only.

Set `G=${PLUMBLINE_HOME:-.plumbline}` (absolute path when running inside a review worktree). The base branch is
`base_branch` in `$G/project.yaml` (written by `init.py`); where this spec says `develop`, use that branch.

**Repository layout.** This spec writes service paths as `services/{service}/` (the broker-dealer layout). The real
location of each unit comes from `python3 "$G/impact/layout.py" .` (name, path, kind): `services/<name>/`, a top-level
module, or an app at the repository root (path `.`, code in `./src/`, its CLAUDE.md is `src/CLAUDE.md`; the root CLAUDE.md is
the master file: solution and architecture). CLAUDE.md files are merged, never overwritten (`bench/claude_merge.py`). Read every
`services/{service}/` below as that unit's path, and `frontend/` as the frontend unit's path (e.g. `ui/`). The benchmark,
scope check and gates use the same layout. If the unit you need is not listed, STOP: a human declares it in
`.plumbline/project.yaml`.
```bash
G=${PLUMBLINE_HOME:-.plumbline}
python3 "$G/bench/run.py" dev --repo . --base develop --name {ticket}-dev
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_findings` as `BENCH:<id> — <detail>`, **skip the critic**, go to Step E.
- **Exit 0 (PASS):** continue to the critic; pass `.plumbline/run/review/{ticket}-dev-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: deterministic gates (Semgrep + structure + domain, 0 NEW against the baseline), the cross-service impact check (no BREAKING), surefire results (0 failures) for every changed service, JaCoCo >= 80%, a *Test for every changed Service/Controller/Consumer/Producer/Rule. The originator runs the tests in Stage 1 to get them green; the reports the benchmark reads come from the orchestrator's own `mvn verify` above.

#### Stage 3 — Judge: isolated critic (the author never grades its own work)

The checklist in this step is the **rubric**. You (the author) do not mark it. An independent critic does.
Run this stage only when the Stage 2 benchmark verdict is PASS (see *Three stages* above).

1. Write the artifact to a file. For code, include uncommitted and new files:
   `mkdir -p .plumbline/run/review && git add -A -N && git diff develop -- . ':!.plumbline' > .plumbline/run/review/{ticket}-attempt.diff` — then assert the file is non-empty.
   (In the code-review loop the artifact is the PR diff from the pinned review worktree — see its Phase 0.)
   For a design/story/PRD/draft, write the markdown to `.plumbline/run/review/{ticket}-{artifact}.md`.
   Facts the critic cannot read itself (JIRA blocker status, labels) go into a short `FACTS` header at the top of the artifact file,
   stated as data (ticket keys + statuses), never as conclusions.
   For a code artifact that touches `services/`, also write the **impact bundle** (deterministic; which other
   services consume or call what changed, with the counterpart files):
   `python3 "${PLUMBLINE_HOME:-.plumbline}/impact/impact.py" --repo . --base develop --cache ~/.cache/plumbline-impact --json .plumbline/run/review/{ticket}-impact.json --bundle .plumbline/run/review/{ticket}-impact.md`
   (in a working tree with uncommitted changes, commit to a scratch branch first or use `--base-dir`/`--head-dir`).
   Write this step's checklist to `.plumbline/run/review/{ticket}-rubric.md`: the item lines only, with any line naming the attempt
   number (e.g. `… — Attempt {attempt}`) removed. This file is the rubric the critic applies.
2. Invoke the `plumbline-critic` subagent with the Agent tool. Pass **only**: the artifact path, the rubric name, the rubric file path, rulebook paths (root `CLAUDE.md`, the service `CLAUDE.md`, and the domain pack — see *Domain pack* below), the impact bundle path when there is one, the **benchmark report** `.plumbline/run/review/{name}-benchmark.md` as `BENCHMARK`, and (from attempt 2) the prior finding ids with their locations. Never pass anything from `.plumbline/run/work/`.
   **Never pass** your reasoning, your earlier drafts, the attempt number, or what you think the verdict should be.
3. Check the critic's evidence before using it: for each `location` finding, confirm the quoted text exists at that path and line. Drop findings whose quote does not match, and note them as `discarded (evidence mismatch)` in the scorecard.
4. Use the critic's `items` as this step's PASS/GAP results and its `findings` as the attempt's gaps. Feed the optimizer only the findings (rule, location, fix), never the critic's free-text reasoning.
5. On the final attempt the critic runs again on the final artifact (verifier pass). The loop only passes if that run is PASS.

**Domain pack.** If `.plumbline/project.yaml` has `domain_pack:`, pass that path (or no pack when it says `none`).
Without a project.yaml, pass `${PLUMBLINE_HOME:-.plumbline}/packs/domain-rules/rules.yaml` (the broker-dealer pack).
Never apply another domain's rules to this repository.
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
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/run/review/{name}-benchmark.md)
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

Co-Authored-By: Claude <noreply@anthropic.com>
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

Next step  : /plumbline-qa SCRUM-{n}  (after code review approves PR)

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
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
3. Re-run /plumbline-dev SCRUM-{n} after clarification
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
