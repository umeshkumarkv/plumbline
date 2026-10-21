# Arch Eval Loop — Plumbline

Produce a technical design for a JIRA story with automated DoR validation and retry.
Runs design → DoR check → retry on gaps — max 3 attempts.
On persistent gaps after 3 attempts, escalates to BA Agent.

## Usage
```
/plumbline-arch {{JIRA_KEY}}-{n}
```

## How It Works

```
Attempt 1..3
  1 ORIGINATOR  writes / revises the design ◄─────────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py arch ── FAIL ────────────────────────────┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · DoR 15-item ── FAIL ────────────────┘ then BOTH stages re-run
        ↓ PASS
  plumbline-arch-approved + post JIRA
After attempt 3 without PASS → ESCALATE → BA Agent (full attempt history, open + disputed items)
```

Max attempts is 3 — if gaps persist after 3 design iterations the story
has an underlying BA-level problem, not a design problem.

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: producing a complete technical design for the JIRA story — endpoint,
DB schema, service logic, Kafka/Redis plan, test strategy — posted as a JIRA comment.

This agent **NEVER**:
- Writes production code or modifies any source file
- Runs tests or builds
- Invents acceptance criteria — ACs come from the BA Agent's story only
- Guesses at missing information — missing information is a gap that escalates to BA Agent

### Design Completeness Rule — HARD STOP

The arch design posted to JIRA is the sole contract for the Dev Agent.
It MUST explicitly cover every field the Dev Agent will need:
- Exact field names used for ownership/identity checks (e.g. `order.createdBy` not `order.clientId`)
- Exact UUID domain of each identifier (auth userId vs trading clientId)
- RBAC rules per role for every endpoint — who is allowed, who is blocked
- Header names forwarded by the gateway and their payload semantics

If any of these are ambiguous or missing after 2 design attempts, escalate to BA Agent.

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
  Ticket : {{JIRA_KEY}}-{n}
  Action : {add label "plumbline-arch-approved" | add label "plumbline-arch-blocked" | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the JIRA write operation until the user types "yes".

---

## Phase 0 — Pre-flight

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Fetch the JIRA story: `getJiraIssue({{JIRA_KEY}}-{n})`
2. Verify the story has label `plumbline-dor-ready` or that ACs exist — if neither, STOP: "Run /plumbline-ba first."
3. Read root `CLAUDE.md` fully (all sections)
4. Identify the service from the ticket
5. Read `services/{service}/CLAUDE.md` fully
6. Read `services/{service}/openapi.yaml` — note existing endpoints, schemas, components
7. Check blocked-by tickets — if any is not Done, STOP and list open blockers

---

## Eval Loop State

Initialize before the loop:
```
attempt      = 1
max_attempts = 3
all_gaps     = []   ← accumulated DoR gaps across attempts
loop_passed  = false
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCH EVAL LOOP — Attempt {attempt} / {max_attempts}
Story : {{JIRA_KEY}}-{n} — {summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_gaps` is not empty, they go to the originator through the feedback file (Stage 1, step 2): every gap
in this design must be addressed.

### Stage 1 — Originator: the `plumbline-arch-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the story in `.plumbline/run/review/{ticket}-story.md`; blocker statuses in `.plumbline/run/review/{ticket}-jira-facts.json`
2. **Feedback file (attempt 2+).** Write `.plumbline/run/work/{ticket}-arch/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/run/work/{ticket}-arch/brief.md`: the task in one paragraph, the input file paths, the artifact
   `.plumbline/run/review/{ticket}-design.md`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/run/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${PLUMBLINE_HOME:-.plumbline}
   python3 "$G/bench/scope_check.py" snapshot --name {ticket}-arch --writable ".plumbline/run/review/{ticket}-design.md" --role arch
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-arch-originator` and the prompt `Brief: .plumbline/run/work/{ticket}-arch/brief.md`.
   Pass nothing else: not your reasoning, not the judge's free text.
   Then run the `CHECK:` command **exactly as printed** (copy it; do not retype the sha). It verifies the sha of the
   snapshot and checker copy with Python (works on macOS and Linux) and runs the check; exit 1 = violations or tampering.
   `<dir>` holds the snapshot and a private copy of the checker outside the repository; the sha check proves neither
   was swapped while the originator ran.
   **Exit 1:** each `SCOPE:` line is a violation. Revert it (restore the file, delete what was added, reset a moved ref),
   carry the items into the feedback file, and count the attempt as failed. **Exit 0:** continue.


### Stage 2 — Benchmark (deterministic, no LLM)

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

**Repository layout.** This spec writes service paths as `services/{service}/` (the default layout). The real
location of each unit comes from `python3 "$G/impact/layout.py" .` (name, path, kind): `services/<name>/`, a top-level
module, or an app at the repository root (path `.`, code in `./src/`, its CLAUDE.md is `src/CLAUDE.md`; the root CLAUDE.md is
the master file: solution and architecture). CLAUDE.md files are merged, never overwritten (`bench/claude_merge.py`). Read every
`services/{service}/` below as that unit's path, and `frontend/` as the frontend unit's path (e.g. `ui/`). The benchmark,
scope check and gates use the same layout. If the unit you need is not listed, STOP: a human declares it in
`.plumbline/project.yaml`.
```bash
G=${PLUMBLINE_HOME:-.plumbline}
python3 "$G/bench/run.py" arch --artifact .plumbline/run/review/{ticket}-design.md --story .plumbline/run/review/{ticket}-story.md --repo . --name {ticket}-arch
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_gaps` as `BENCH:<id> — <detail>`, **skip Step C**, go to Step D.
- **Exit 0 (PASS):** continue to Step C; pass `.plumbline/run/review/{ticket}-arch-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: all 9 design blocks, endpoint/service/port vs the code, own schema, gateway route, next free migration version, external calls hit real endpoints, consumed topics have a producer, every AC error status has an error code, >= 3 tests per layer, RBAC roles, forwarded headers, no placeholders.

### Step C — Stage 3 Judge: DoR Validation (15-item checklist, isolated critic)

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
Without a project.yaml, the domain pack is `none`.
Never apply another domain's rules to this repository.
Rubric `arch DoR 15-item`: the critic marks [x] PASS or [ ] GAP with specific reason for each GAP.

```
DEFINITION OF READY CHECKLIST — Attempt {attempt}

  [x/] Story has a clear user story (As a / I want / So that)
       {gap reason if failed}

  [x/] All acceptance criteria are curl-verifiable (each AC maps to an HTTP assertion)
       {gap reason if failed}

  [x/] Service boundary is clear — story touches exactly one service
       {gap reason if failed}

  [x/] No blocked-by tickets are open
       {gap reason if failed}

  [x/] No dependency on CLAUDE.md Section 18 (Out of Scope)
       {gap reason if failed}

  [x/] Endpoint path and HTTP verb confirmed
       {gap reason if failed}

  [x/] Response shape designed — all fields named and typed
       {gap reason if failed}

  [x/] Error codes defined for every failure path in the ACs
       {gap reason if failed}

  [x/] DB migration scoped — or explicitly confirmed not needed
       {gap reason if failed}

  [x/] External service calls identified — Resilience4j circuit breaker planned
       {gap reason if failed}

  [x/] Test strategy written — >= 3 unit test cases per layer (service + controller)
       {gap reason if failed}

  --- Design Completeness Rule (HARD STOP items) ---

  [x/] Ownership/identity fields named exactly (e.g. `order.createdBy`, not `order.clientId`)
       {gap reason if failed}

  [x/] UUID domain stated for every identifier (auth userId vs trading clientId) and comparisons are same-domain
       {gap reason if failed}

  [x/] RBAC per role for every endpoint — who is allowed, who is blocked (TRADER / OPERATIONS / ADMIN)
       {gap reason if failed}

  [x/] Gateway-forwarded header names and payload semantics listed (e.g. X-User-Id, X-User-Role)
       {gap reason if failed}
```

### Step D — Decision

Collect this attempt's gaps:
```
attempt_gaps = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
             + [all DoR items marked as GAP]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition:** `attempt_gaps` is empty (all 15 items checked) **and** the Stage 2 benchmark verdict is PASS

Print DoR scorecard:
```
DoR SCORECARD — Attempt {attempt}
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/run/review/{name}-benchmark.md)
  User story clear             : {PASS | GAP}
  ACs curl-verifiable          : {PASS | GAP}
  Service boundary clear       : {PASS | GAP}
  No open blockers             : {PASS | GAP}
  Not out of scope             : {PASS | GAP}
  Endpoint path + verb         : {PASS | GAP}
  Response shape designed      : {PASS | GAP}
  Error codes defined          : {PASS | GAP}
  DB migration scoped          : {PASS | GAP}
  External calls + Resilience4j: {PASS | GAP}
  Test strategy written        : {PASS | GAP}
  Identity fields exact        : {PASS | GAP}
  UUID domains consistent      : {PASS | GAP}
  RBAC per role per endpoint   : {PASS | GAP}
  Gateway headers specified    : {PASS | GAP}

  VERDICT : {ALL PASSED — design approved | GAPS — {n} items incomplete}
```

**If ALL PASSED:**
- Set `loop_passed = true`
- Exit the loop → go to Phase 1 (JIRA Update)

**If GAPS and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_gaps` to `all_gaps`
- Increment `attempt`
- Return to LOOP start (Step A) — next attempt will address all gaps

**If GAPS and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — JIRA Update (reached only on PASS)

1. Post full technical design as a JIRA comment on {{JIRA_KEY}}-{n}:
```
Arch Eval Loop ({date}): Technical design complete — passed DoR on attempt {attempt}/{max_attempts}.

{paste the approved design from `.plumbline/run/review/{ticket}-design.md`}

DEFINITION OF READY: ALL 15 CHECKS PASSED
Story is ready for development. Run: /plumbline-dev {{JIRA_KEY}}-{n}
```

2. Apply the JIRA Write Guard, then add label `plumbline-arch-approved` to the ticket.

---

## Phase 2 — Summary to User

```
ARCH EVAL LOOP — {{JIRA_KEY}}-{n} COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story      : {summary}
Service    : {service-name}
Eval Loop  : Passed on attempt {attempt} / {max_attempts}
{if attempt > 1: Gaps resolved: {list what changed}}

DESIGN COMPLETE
  Endpoint   : {METHOD} {path}
  DB change  : {yes — V{n}__migration.sql | no}
  Kafka      : {produces X | consumes Y | none}
  Redis      : {new key | none}
  Ext calls  : {service list | none}
  Tests      : {n} unit test cases planned

DoR STATUS : APPROVED (label: plumbline-arch-approved)

Next step  : /plumbline-dev {{JIRA_KEY}}-{n}

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

## Escalation — reached when all 3 attempts have gaps

```
ARCH EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{JIRA_KEY}}-{n} has DoR gaps that could not be resolved in {max_attempts} design attempts.
This indicates a story-level problem, not a design problem.

Persistent gaps:
{numbered list of all_gaps with specific reason for each}

Root cause: The story as written by BA Agent is missing information
that the Architect cannot invent. A BA Agent revision is required.

Recommended action:
1. Run /plumbline-ba epic:{epic-key} to revisit the story
2. Specifically address: {list of gap areas}
3. Re-run /plumbline-arch {{JIRA_KEY}}-{n} after story is updated
```

Post to JIRA as a comment (informational — no approval needed under the Plumbline write policy; any label or transition that follows still needs the Write Guard):
- Add comment with the escalation block above
- Apply JIRA Write Guard, then add label `plumbline-arch-blocked`

STOP.

---

## Hard Stops — always pause and ask the user

- Story has no acceptance criteria — cannot design without them
- Blocked-by tickets are not Done
- Feature requires cross-service database access (violates CLAUDE.md Section 3)
- Feature requires a new microservice not listed in CLAUDE.md Section 3
- Feature is in CLAUDE.md Section 18 (Out of Scope for POC)
- Design requires a new Maven dependency — CLAUDE.md must be updated first
