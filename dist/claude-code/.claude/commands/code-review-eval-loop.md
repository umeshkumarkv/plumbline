# Code Review Eval Loop — Plumbline

Audit a PR diff against CLAUDE.md coding standards with round-tracking across fix cycles.
Tracks review rounds: audit → REQUEST CHANGES → dev fixes → re-audit until APPROVED or max rounds.
On persistent violations after 3 rounds, escalates to human.

## Usage
```
/code-review-eval-loop SCRUM-{n}
/code-review-eval-loop pr:{n}
```

## How It Works

```
Round 1..3   (the PR author's Dev Eval Loop is the originator; this loop is benchmark + judge on the pinned head SHA)
  2 BENCHMARK   bench/run.py code-review (gates · impact · tests · protected paths · CI) ── FAIL ──┐
        ↓ PASS                                                                                     │
  3 JUDGE       isolated critic · code-review 12-category ── FAIL ────────────────────────────────┤
        ↓ PASS                                                                                     ▼
  status plumbline/code-review = success          REQUEST_CHANGES: failing checks + findings (rule · location · fix)
                                             → dev fixes on the branch, pushes → next round re-reviews the
                                               new head; prior findings verified RESOLVED / STILL PRESENT
After round 3 without PASS → ESCALATED → human (all rounds' findings, open + disputed items)
```

Round tracking persists in JIRA — each invocation reads prior round comments to verify
that previously identified violations were resolved before scanning for new ones.

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: auditing the PR diff against CLAUDE.md coding standards (12 categories) and
posting a structured GitHub review. It tracks rounds across separate invocations.

This agent **NEVER**:
- Fixes code or edits source files
- Makes architecture decisions or suggests design changes
- Approves a PR that has unresolved violations
- Requests changes for style issues not covered by CLAUDE.md

Escalate to human if: a violation is ambiguous or a new pattern appears that is not in CLAUDE.md.

---

## GitHub Write Guard — Human Approval Required

> **Plumbline write policy (applies to every agent).** JIRA *comments* are informational and need no approval.
> Always approval-gated: adding/removing labels, transitioning status, creating issues or Confluence pages,
> `git push`, `gh pr create`, `gh pr review` (approve / request-changes / overall comment), and any write to a CLAUDE.md file.

Before performing ANY of the following operations, STOP and request explicit user approval:
- Setting the `plumbline/code-review` commit status (success / failure)
- `gh pr review --comment` (the single overall review; findings go inside it — no separate comments)
- This agent NEVER runs `gh pr review --approve` or `--request-changes`: approvals are human (CODEOWNERS)

Approval format:
```
GITHUB ACTION — AWAITING YOUR APPROVAL
  PR      : #{pr-number} — {pr-title}
  Action  : {set plumbline/code-review status success | set status failure | post review comment}
  Verdict : {APPROVED — all 12 categories pass | REQUEST CHANGES — {n} violation(s)}
  Round   : {n} of {max_rounds}

Proceed? (yes / no)
```
Do NOT set the status or post the review until the user types "yes".

---

## JIRA Write Guard — Human Approval Required

Before performing ANY of the following operations, STOP and request explicit user approval:
- Adding or removing a label on any ticket
- Transitioning a ticket status

Approval format:
```
JIRA ACTION — AWAITING YOUR APPROVAL
  Ticket : SCRUM-{n}
  Action : {add label "plumbline-code-review-approved" | transition to "In Progress" | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```

---

## Phase 0 — Setup

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Read `CLAUDE.md` fully — all sections. Do not skip any.
2. Identify the service from the ticket or PR
3. Read `services/{service}/CLAUDE.md`
4. Fetch the PR number if not provided:
   ```bash
   gh pr list --search "SCRUM-{n}" --json number,title,headRefName,reviewDecision
   ```
5. Check out the PR head in a clean, isolated worktree and pin the reviewed SHA. Everything below (gates, artifact,
   critic, status) uses this worktree and this SHA, never your local working tree:
   ```bash
   REVIEWED_SHA=$(gh pr view {pr-number} --json headRefOid --jq .headRefOid)
   BASE=$(gh pr view {pr-number} --json baseRefName --jq .baseRefName)
   export AGENTIC_SDLC="$(git rev-parse --show-toplevel)/.agentic-sdlc"   # absolute: still valid inside the worktree
   git fetch origin "$BASE" "pull/{pr-number}/head"
   git worktree remove --force .plumbline/review/pr-{pr-number} 2>/dev/null || true   # leftover from an earlier round
   git worktree add --detach .plumbline/review/pr-{pr-number} "$REVIEWED_SHA"
   cd .plumbline/review/pr-{pr-number}
   git diff "origin/$BASE...$REVIEWED_SHA" > ../pr-{pr-number}.diff && test -s ../pr-{pr-number}.diff
   ```
6. List all changed files:
   ```bash
   gh pr view {pr-number} --json files --jq '.files[].path'
   ```
7. Before posting ANY status or review: re-read `headRefOid`. If it differs from `$REVIEWED_SHA`, the PR moved during review.
   STOP and restart the round on the new head. Never post a status for a SHA you did not review.

### Determine Current Round

Read all JIRA comments on SCRUM-{n} to find prior code-review-eval-loop comments:
```
getJiraIssue(issueIdOrKey: "SCRUM-{n}")
```

Search comments for the round marker `[plumbline:code-review pr=#{pr-number} ` (every round comment starts with it — see Phases 3, 4 and Escalation). Do not match on free text.
Only markers for **this PR number** count, and only those **after** the most recent `verdict=APPROVED` marker or reset comment `[plumbline:code-review reset pr=#{pr-number}]`.
A reset counts **only if its JIRA comment author is a human account** (not the account this agent posts with). Agents never post reset markers.

```
round        = (count of qualifying `verdict=REQUEST_CHANGES` markers) + 1
               If the most recent qualifying marker is `verdict=ESCALATED`: STOP — print "Escalated; a human must post
               [plumbline:code-review reset pr=#{pr-number}] after resolving it" and do nothing else.
max_rounds   = 3
prior_violations = []   ← violations listed in the most recent QUALIFYING round marker comment (if any)
loop_passed  = false
```

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CODE REVIEW EVAL LOOP — Round {round} / {max_rounds}
Story : SCRUM-{n} — {summary}
PR    : #{pr-number} — {pr-title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `prior_violations` is not empty (round > 1), print:
```
PRIOR ROUND VIOLATIONS — verify each is resolved before scanning for new ones:
{numbered list of prior_violations with file:line references}
```

---

## Phase 1 — Standards Audit

### Step 1 — Verify Prior Round Violations (rounds 2 and 3 only)

For each violation from `prior_violations`:
- Search the updated diff for the specific file:line
- Verify the violation is no longer present
- Mark: RESOLVED or STILL PRESENT

If any prior violation is STILL PRESENT — it counts as a violation in this round's findings.

### Step 2 — Full 12-Category Audit (Stage 2 benchmark, then Stage 3 judge)

The PR author's Dev Eval Loop was the originator. This loop is a fresh benchmark + judge on the pinned `REVIEWED_SHA`, run from the review worktree.

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

**Every run starts at attempt 1.** The attempt counter lives only in this run, never in files. If `.plumbline/work/{name}/`
exists from an earlier run, move it to `.plumbline/work/{name}/previous-<YYYYMMDD-HHMM>/` before Stage 1 (keep it as history;
do not read its attempt number). Existing drafts in `.plumbline/review/` are the starting artifact for attempt 1, and the
last run's open findings (from its escalation or feedback file) go into attempt 1's feedback file.

Rules
1. **Benchmark first.** Run Stage 2 as soon as the artifact is written. If its verdict is **FAIL**, this attempt
   fails: every FAIL check becomes a gap (`BENCH:<check id> — <detail>`), **skip Stage 3** and go to the Decision
   step. Fixing those needs no LLM opinion, and the judge's time is spent only on artifacts that are measurably sound.
2. **The judge gets the report as facts.** Pass `.plumbline/review/{name}-benchmark.md` to the critic as `BENCHMARK`.
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
2. **The originator fixes each item** in the artifact and writes `.plumbline/work/{name}/fixlog.md`, one line per item:
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

Exceptions: `/devops-eval-loop` pushes its fix to the feature branch before Stage 2 because its evidence is a CI run
(never to `main`/`develop`, nothing merged). `/code-review-eval-loop` has no originator: the PR under review is the
artifact, so it runs Stages 2 and 3 only.

Set `G=${AGENTIC_SDLC:-.agentic-sdlc}` (absolute path when running inside a review worktree). The base branch is
`base_branch` in `$G/project.yaml` (written by `init.py`); where this spec says `develop`, use that branch.

**Repository layout.** This spec writes service paths as `services/{service}/` (the broker-dealer layout). The real
location of each unit comes from `python3 "$G/impact/layout.py" .` (name, path, kind): `services/<name>/`, a top-level
module, or an app at the repository root (path `.`, code in `./src/`, its CLAUDE.md is `src/CLAUDE.md`; the root CLAUDE.md is
the master file: solution and architecture). CLAUDE.md files are merged, never overwritten (`bench/claude_merge.py`). Read every
`services/{service}/` below as that unit's path, and `frontend/` as the frontend unit's path (e.g. `ui/`). The benchmark,
scope check and gates use the same layout. If the unit you need is not listed, STOP: a human declares it in
`.agentic-sdlc/project.yaml`.
```bash
G=${AGENTIC_SDLC:-.agentic-sdlc}
python3 "$G/bench/run.py" code-review --repo . --base "origin/$BASE" --pr {pr-number} --out-dir .. --name pr-{pr-number} \
  --test-cmd 'M=$(git diff --name-only "origin/'"$BASE"'...HEAD" -- services | cut -d/ -f1-2 | sort -u | paste -sd, -); [ -z "$M" ] || mvn -B -q verify -pl "$M" -am'   # fresh worktree: build + test the changed services (none changed: nothing to run)   # cwd = the review worktree; reports land in .plumbline/review/
```
- **Exit 1 (FAIL):** add every FAIL check to `current_findings` as `BENCH:<id> — <detail>`, **skip the critic**, go to the Decision with verdict REQUEST_CHANGES.
- **Exit 0 (PASS):** continue to the critic; pass `.plumbline/review/pr-{pr-number}-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: everything the dev benchmark measures (gates, impact, tests, coverage, test classes) at the reviewed SHA, protected paths, and CI check-runs green on that SHA.

#### Stage 3 — Judge: isolated critic (the author never grades its own work)

The checklist in this step is the **rubric**. You (the author) do not mark it. An independent critic does.
Run this stage only when the Stage 2 benchmark verdict is PASS (see *Three stages* above).

1. Write the artifact to a file. For code, include uncommitted and new files:
   `mkdir -p .plumbline/review && git add -A -N && git diff develop -- . ':!.plumbline' > .plumbline/review/{ticket}-attempt.diff` — then assert the file is non-empty.
   (In the code-review loop the artifact is the PR diff from the pinned review worktree — see its Phase 0.)
   For a design/story/PRD/draft, write the markdown to `.plumbline/review/{ticket}-{artifact}.md`.
   Facts the critic cannot read itself (JIRA blocker status, labels) go into a short `FACTS` header at the top of the artifact file,
   stated as data (ticket keys + statuses), never as conclusions.
   For a code artifact that touches `services/`, also write the **impact bundle** (deterministic; which other
   services consume or call what changed, with the counterpart files):
   `python3 "${AGENTIC_SDLC:-.agentic-sdlc}/impact/impact.py" --repo . --base develop --cache ~/.cache/plumbline-impact --json .plumbline/review/{ticket}-impact.json --bundle .plumbline/review/{ticket}-impact.md`
   (in a working tree with uncommitted changes, commit to a scratch branch first or use `--base-dir`/`--head-dir`).
   Write this step's checklist to `.plumbline/review/{ticket}-rubric.md`: the item lines only, with any line naming the attempt
   number (e.g. `… — Attempt {attempt}`) removed. This file is the rubric the critic applies.
2. Invoke the `plumbline-critic` subagent with the Agent tool. Pass **only**: the artifact path, the rubric name, the rubric file path, rulebook paths (root `CLAUDE.md`, the service `CLAUDE.md`, and the domain pack — see *Domain pack* below), the impact bundle path when there is one, the **benchmark report** `.plumbline/review/{name}-benchmark.md` as `BENCHMARK`, and (from attempt 2) the prior finding ids with their locations. Never pass anything from `.plumbline/work/`.
   **Never pass** your reasoning, your earlier drafts, the attempt number, or what you think the verdict should be.
3. Check the critic's evidence before using it: for each `location` finding, confirm the quoted text exists at that path and line. Drop findings whose quote does not match, and note them as `discarded (evidence mismatch)` in the scorecard.
4. Use the critic's `items` as this step's PASS/GAP results and its `findings` as the attempt's gaps. Feed the optimizer only the findings (rule, location, fix), never the critic's free-text reasoning.
5. On the final attempt the critic runs again on the final artifact (verifier pass). The loop only passes if that run is PASS.

**Domain pack.** If `.agentic-sdlc/project.yaml` has `domain_pack:`, pass that path (or no pack when it says `none`).
Without a project.yaml, pass `${AGENTIC_SDLC:-.agentic-sdlc}/packs/domain-rules/rules.yaml` (the broker-dealer pack).
Never apply another domain's rules to this repository.
The categories below are the critic's rubric (`code-review 12-category`). Run the critic in a context that has never seen the Dev Eval Loop session for this ticket. This agent only verifies evidence and posts the review.

**Category 1 — Java Type Rules** (CLAUDE.md Section 13a)
- [ ] No `double` or `float` for monetary values — must be `BigDecimal`
- [ ] No `Long` or `Integer` as primary key type — must be `UUID`
- [ ] No `Date`, `Calendar`, or `long` for timestamps — must be `Instant` or `LocalDate`
- [ ] All enum fields annotated `@Enumerated(EnumType.STRING)` — never `ORDINAL`
- [ ] BigDecimal comparisons use `compareTo()` — never `equals()` (scale issue)
- [ ] BigDecimal constructed from String or `BigDecimal.valueOf()` — never from `double`

**Category 2 — Naming Conventions** (CLAUDE.md Section 13b)
- [ ] All class names: PascalCase with correct layer suffix
- [ ] All method and variable names: camelCase
- [ ] All constants and enum values: UPPER_SNAKE_CASE
- [ ] All DB table and column names in migrations: snake_case
- [ ] All REST paths: kebab-case plural nouns
- [ ] JSON fields: camelCase
- [ ] Test class name: ends with `Test`

**Category 3 — Lombok** (CLAUDE.md Section 13d)
- [ ] Entities have: `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- [ ] Services/Consumers/Producers have: `@RequiredArgsConstructor @Slf4j`
- [ ] Controllers have: `@RequiredArgsConstructor`
- [ ] Response DTOs have: `@Value @Builder` (immutable)
- [ ] Request DTOs have: `@Data`
- [ ] No `@Autowired` on any field

**Category 4 — Dependency Injection** (CLAUDE.md Section 13e)
- [ ] All dependencies injected via constructor (`@RequiredArgsConstructor`)
- [ ] No field injection
- [ ] No setter injection

**Category 5 — Architecture Boundaries** (CLAUDE.md Section 3)
- [ ] Controller contains zero business logic
- [ ] Service never returns JPA entities
- [ ] No direct access to another service's database schema
- [ ] No `ApplicationEvent` — Kafka only for async
- [ ] No `Mono`, `Flux`, `Publisher`, or any Reactor import
- [ ] No `CompletableFuture` chains to avoid blocking

**Category 6 — API Standards** (CLAUDE.md Section 12)
- [ ] All success responses: `{ "data": {...}, "meta": { "timestamp": "...", "requestId": "..." } }`
- [ ] All error responses: `{ "error": { "code": "...", "message": "..." }, "meta": {} }`
- [ ] All monetary values serialised as JSON String — never as JSON number
- [ ] All timestamps in JSON: ISO 8601 UTC
- [ ] Base path: `/api/v1/{resource}` — resources are plural nouns

**Category 7 — Entity Column Conventions** (CLAUDE.md Section 13f)
- [ ] All required fields: `@Column(nullable = false)`
- [ ] All enum fields: `@Enumerated(EnumType.STRING)`
- [ ] All BigDecimal fields: `@Column(precision = 19, scale = 4)`
- [ ] Entities with audit trail: `createdAt` (not updatable) and `updatedAt` present

**Category 8 — Logging** (CLAUDE.md Section 13h)
- [ ] All logging uses `@Slf4j`
- [ ] No passwords, tokens, or secrets in any log statement
- [ ] No full request/response bodies with client PII
- [ ] No BigDecimal monetary values logged at INFO or above

**Category 9 — Exception Handling** (CLAUDE.md Section 13i)
- [ ] Custom exceptions extend `RuntimeException`
- [ ] Custom exceptions carry a machine-readable `errorCode` String field
- [ ] `GlobalExceptionHandler` exists with `@RestControllerAdvice`
- [ ] No stack traces returned in API responses
- [ ] No `throw new RuntimeException("message")` from business logic

**Category 10 — Testing** (CLAUDE.md Section 15)
- [ ] Unit test exists for every public service method
- [ ] Controller test covers: happy path (200), not-found (404), validation error (400/422)
- [ ] Tests use `@ExtendWith(MockitoExtension.class)` or `@WebMvcTest`
- [ ] No production logic in test classes
- [ ] Test method names: camelCase, descriptive

**Category 11 — Security**
- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No stack traces returned in API responses
- [ ] No raw SQL with string concatenation
- [ ] JWT_SECRET read from environment variable — never from application.yml directly

**Category 12 — Flyway Migrations**
- [ ] Migration file: `V{n}__{description}.sql` (double underscore)
- [ ] Migration only modifies this service's own schema
- [ ] No `DROP TABLE` or `TRUNCATE` without explicit human approval
- [ ] Migration is idempotent where possible

---

## Phase 2 — Evaluate

Collect this round's findings:
```
current_findings = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
                 + [all FAIL items from categories 1–12]
                 + [prior violations still PRESENT (rounds 2+)]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition:** `current_findings` is empty (all 12 categories clean) **and** the Stage 2 benchmark verdict is PASS

Print scorecard:
```
CODE REVIEW SCORECARD — Round {round} / {max_rounds}
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/review/{name}-benchmark.md)
  Cat 1  Type Rules      : {PASS | FAIL — n violations}
  Cat 2  Naming          : {PASS | FAIL — n violations}
  Cat 3  Lombok          : {PASS | FAIL — n violations}
  Cat 4  DI              : {PASS | FAIL — n violations}
  Cat 5  Architecture    : {PASS | FAIL — n violations}
  Cat 6  API Standards   : {PASS | FAIL — n violations}
  Cat 7  Entity Cols     : {PASS | FAIL — n violations}
  Cat 8  Logging         : {PASS | FAIL — n violations}
  Cat 9  Exceptions      : {PASS | FAIL — n violations}
  Cat 10 Testing         : {PASS | FAIL — n violations}
  Cat 11 Security        : {PASS | FAIL — n violations}
  Cat 12 Migrations      : {PASS | FAIL — n violations}
  {if round > 1:
  Prior violations resolved : {n} / {total prior}}

  VERDICT : {APPROVED — all categories pass | REQUEST CHANGES — {n} violation(s)}
```

**If PASSED → go to Phase 3 (Approve)**

**If VIOLATIONS and round < max_rounds → go to Phase 4 (Request Changes)**

**If VIOLATIONS and round = max_rounds → go to Escalation**

---

## Phase 3 — Approve (reached only when 0 violations)

List each prior-round finding now resolved inside the review body below (section "Resolved since Round {prior-round}": file:line, category, status RESOLVED). Nothing is posted outside the single guarded review.

Apply the **GitHub Write Guard**, then post the verdict. The bot never approves a PR: it posts a review **comment** plus a
`plumbline/code-review` **status check** (success). Human CODEOWNERS approve and merge (see packs/governance/approval-matrix.md).
```bash
gh api repos/{owner}/{repo}/statuses/$REVIEWED_SHA \
  -f state=success -f context=plumbline/code-review -f description="All 12 categories pass (round {round})"
gh pr review {pr-number} --comment \
  --body "## Code Review Eval Loop — SCRUM-{n} — APPROVED

### Results by Category

| Category | Result | Notes |
|---|---|---|
| Type rules | PASS | |
| Naming | PASS | |
| Lombok | PASS | |
| DI | PASS | |
| Architecture | PASS | |
| API standards | PASS | |
| Entity conventions | PASS | |
| Logging | PASS | |
| Exception handling | PASS | |
| Testing | PASS | |
| Security | PASS | |
| Migrations | PASS | |

### Decision
APPROVED after {round} round(s) — all 12 categories pass.
{if round > 1: Violations resolved between rounds: {list}}

Generated by Code Review Eval Loop — Round {round} / {max_rounds}"
```

Add JIRA comment:
```
[plumbline:code-review pr=#{pr-number} round={round}/{max_rounds} verdict=APPROVED]
Code Review Eval Loop ({date}): PR #{pr-number} APPROVED — Round {round}/{max_rounds}.
All 12 categories passed. Ready for QA.
Run: /qa-eval-loop SCRUM-{n}
```

Apply the **JIRA Write Guard**, then add label `plumbline-code-review-approved` to the ticket.

---

## Phase 4 — Request Changes (violations found, round < max_rounds)

Include every FAIL finding inside the single review body below, one section each:
```
**{Category} violation** — {file}:{line}
Issue: {specific violation} · Fix: {what should be done instead} · Reference: CLAUDE.md Section {n} · Round {round}/{max_rounds}
```
Nothing is posted outside the single guarded review.

Apply the **GitHub Write Guard**, then post the verdict as a failing `plumbline/code-review` status check plus a review comment:
```bash
gh api repos/{owner}/{repo}/statuses/$REVIEWED_SHA \
  -f state=failure -f context=plumbline/code-review -f description="{n} violation(s), round {round}/{max_rounds}"
gh pr review {pr-number} --comment \
  --body "## Code Review Eval Loop — SCRUM-{n} — Round {round}/{max_rounds}

### Results by Category

| Category | Result | Violations |
|---|---|---|
{one row per category}

### Decision
REQUEST CHANGES — {n} violation(s) found. Each is listed above in this review.
Fix all violations on branch {branch-name} and re-run /code-review-eval-loop SCRUM-{n}.

This is Round {round} of {max_rounds}. Escalation to human required after Round {max_rounds}."
```

Add JIRA comment recording this round's violations:
```
[plumbline:code-review pr=#{pr-number} round={round}/{max_rounds} verdict=REQUEST_CHANGES]
Code Review Eval Loop ({date}): Round {round}/{max_rounds} — REQUEST CHANGES
PR #{pr-number} — {n} violation(s) found.

Violations:
{numbered list with file:line evidence}

Dev action: Fix violations on branch {branch-name} and re-run /code-review-eval-loop SCRUM-{n}.
```

Apply the **JIRA Write Guard**, then transition ticket: In Review → **In Progress**

---

## Phase 5 — Summary to User

First return to the repo root and remove the review worktree: `git worktree remove --force .plumbline/review/pr-{pr-number}`.

```
CODE REVIEW EVAL LOOP — SCRUM-{n} — Round {round}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR       : #{pr-number} — {pr-title}
Verdict  : {APPROVED | REQUEST CHANGES — {n} violation(s)}
Categories: {n} / 12 passed
Round    : {round} of {max_rounds}
{if violations: Top categories with issues: {comma-separated names}}

Next step: {/qa-eval-loop SCRUM-{n} | Fix violations and re-run /code-review-eval-loop SCRUM-{n}}

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

## Escalation — reached when violations persist after 3 rounds

```
CODE REVIEW EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCRUM-{n} has persistent code violations after {max_rounds} review rounds.

Violations still present after Round {max_rounds}:
{numbered list with file:line evidence}

Rounds summary:
  Round 1: {n} violations found
  Round 2: {n} violations found (prior: {resolved} resolved, {new} new)
  Round 3: {n} violations found (prior: {resolved} resolved, {new} new)

Human action required:
1. Review the persistent violations above
2. Determine if they are genuine violations or if CLAUDE.md needs updating
3. Either fix manually or update CLAUDE.md to reflect a new approved pattern
4. A human posts `[plumbline:code-review reset pr=#{pr-number}]` on the ticket (agents never do), then re-run /code-review-eval-loop SCRUM-{n}
```

Post to JIRA as a comment (informational — no approval needed under the Plumbline write policy; any label or transition that follows still needs the Write Guard):
```
[plumbline:code-review pr=#{pr-number} round={round}/{max_rounds} verdict=ESCALATED]
Code Review Eval Loop ESCALATED — SCRUM-{n}
Failed after 3 rounds. Persistent violations:
{violations list}
Human review required before any further action.
```

STOP.

---

## Hard Stops — always pause and ask the user

- A violation is ambiguous — unclear if it is intentional or an error
- A new pattern is used that is not covered by CLAUDE.md (may need CLAUDE.md update first)
- A security concern is found that goes beyond coding standards (credential exposure, injection risk)
- The PR diff cannot be fetched or the branch does not exist
