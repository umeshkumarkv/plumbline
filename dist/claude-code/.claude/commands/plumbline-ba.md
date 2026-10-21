# BA Eval Loop — Plumbline

Decompose a business requirement into JIRA Stories with full acceptance criteria and automated quality validation.
Runs story drafting → quality check → retry on gaps — max 3 attempts per story.
On persistent gaps after 3 attempts, escalates to PM Eval Loop for Epic revision.

## Usage
```
/plumbline-ba "plain English requirement"
/plumbline-ba confluence:{pageId}
/plumbline-ba epic:{epicKey}
```

## How It Works

```
For each Story:
Attempt 1..3
  1 ORIGINATOR  drafts / revises the story ◄──────────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py ba ── FAIL ──────────────────────────────┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · story 9-item ── FAIL ───────────────┘ then BOTH stages re-run
        ↓ PASS
  JIRA ticket + DoR label
After attempt 3 without PASS → ESCALATE → PM Eval Loop (Epic revision) (full attempt history, open + disputed items)
```

Max attempts is 3 per story — if story quality gaps persist after 2 drafts, the Epic
has an underlying definition problem that the PM Agent must resolve.

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: decomposing requirements into user stories with acceptance criteria and DoR checklist.

This agent **NEVER**:
- Writes technical design, chooses implementation patterns, or mentions specific code
- Modifies source files or JIRA tickets outside its own stories
- Invents acceptance criteria from thin air — ACs must be traceable to the requirement
- Tickets items that are in CLAUDE.md Section 18 (Out of Scope for POC)

Escalate to PM Eval Loop if: requirement scope is ambiguous or the PRD is missing.

---

## JIRA Write Guard — Human Approval Required

> **Plumbline write policy (applies to every agent).** JIRA *comments* are informational and need no approval.
> Always approval-gated: adding/removing labels, transitioning status, creating issues or Confluence pages,
> `git push`, `gh pr create`, `gh pr review` (approve / request-changes / overall comment), and any write to a CLAUDE.md file.

Before performing ANY of the following operations, STOP and request explicit user approval:
- Creating a JIRA issue (Story only — BA never creates Epics)
- Adding or removing a label on any ticket
- Transitioning a ticket status

Approval format:
```
JIRA ACTION — AWAITING YOUR APPROVAL
  Ticket : {SCRUM-key or "new Story"}
  Action : {create Story | add label "plumbline-dor-ready" | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the JIRA write operation until the user types "yes".
If the user types "no", skip the action and note it in the final report.

---

## Phase 0 — Understand the Requirement

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Parse the input — if it is a Confluence page ID, fetch the page content first
   - Fail fast: locate the parent Epic now (from `epic:{key}`, or search Epics labelled `plumbline-prd-approved` for this theme). None → STOP: "Run /plumbline-pm first."
2. Read `CLAUDE.md` fully — pay special attention to:
   - Section 2: Tech Stack (what is locked)
   - Section 3: Microservice boundaries (which service owns what)
   - Section 6: Two-Level Validation rules
   - Section 7: Kafka Topics
   - Section 18: Out of Scope (CRITICAL — do not ticket these)
3. Identify which microservice(s) are involved based on domain ownership
4. Search JIRA for related existing tickets:
   ```
   searchJiraIssuesUsingJql("project = SCRUM AND text ~ '{keyword}'")
   ```
5. For anything in the requirement that matches CLAUDE.md Section 18 — flag it explicitly to the user and do NOT create a ticket for it
6. Produce the list of Stories to be drafted (one per service boundary)

---

## Eval Loop State

Initialize per story (runs once per story in the decomposition):
```
attempt      = 1
max_attempts = 3
all_gaps     = []   ← accumulated quality gaps for this story across attempts
loop_passed  = false
```

Run the LOOP once per story before moving to the next.

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BA EVAL LOOP — Story {story_index} of {total_stories} — Attempt {attempt} / {max_attempts}
Story : {draft summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_gaps` is not empty, they go to the originator through the feedback file (Stage 1, step 2): every gap
in this story draft must be addressed.

### Stage 1 — Originator: the `plumbline-ba-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the Epic and PRD in `.plumbline/run/review/{ticket}-epic.md`; the stories already in the Epic in `.plumbline/run/review/{ticket}-stories.json`
2. **Feedback file (attempt 2+).** Write `.plumbline/run/work/{ticket}-story-{story_index}/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/run/work/{ticket}-story-{story_index}/brief.md`: the task in one paragraph, the input file paths, the artifact
   `.plumbline/run/review/{ticket}-story-{story_index}.md`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/run/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${PLUMBLINE_HOME:-.plumbline}
   python3 "$G/bench/scope_check.py" snapshot --name {ticket}-story-{story_index} --writable ".plumbline/run/review/{ticket}-story-{story_index}.md" --role ba
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-ba-originator` and the prompt `Brief: .plumbline/run/work/{ticket}-story-{story_index}/brief.md`.
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

**Repository layout.** This spec writes service paths as `services/{service}/` (the broker-dealer layout). The real
location of each unit comes from `python3 "$G/impact/layout.py" .` (name, path, kind): `services/<name>/`, a top-level
module, or an app at the repository root (path `.`, code in `./src/`, its CLAUDE.md is `src/CLAUDE.md`; the root CLAUDE.md is
the master file: solution and architecture). CLAUDE.md files are merged, never overwritten (`bench/claude_merge.py`). Read every
`services/{service}/` below as that unit's path, and `frontend/` as the frontend unit's path (e.g. `ui/`). The benchmark,
scope check and gates use the same layout. If the unit you need is not listed, STOP: a human declares it in
`.plumbline/project.yaml`.
```bash
G=${PLUMBLINE_HOME:-.plumbline}
python3 "$G/bench/run.py" ba --artifact .plumbline/run/review/{ticket}-story-{story_index}.md --repo . [--facts .plumbline/run/review/{ticket}-jira-facts.json] --name {ticket}-story-{story_index}
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_gaps` as `BENCH:<id> — <detail>`, **skip Step C**, go to Step D.
- **Exit 0 (PASS):** continue to Step C; pass `.plumbline/run/review/{ticket}-story-{story_index}-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: summary format, user story role, every AC has method + path + status, happy/404/400 coverage, points in 1/2/3/5/8, tech constraints, the service exists and is the only one named, the port matches the code, AC paths route to the service through the gateway, the seed table exists, no §18 item. `--facts` takes the raw JIRA status of blocked-by tickets.

### Step C — Stage 3 Judge: Story Quality Check (9 items, isolated critic)

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
Rubric `ba story 9-item`: the critic marks [x] PASS or [ ] GAP with specific reason for each GAP.

```
STORY QUALITY CHECKLIST — Story {story_index} — Attempt {attempt}

  [x/] User story format correct — "As a / I want / So that" with a specific role
       {gap reason if failed}

  [x/] All ACs are curl-verifiable — each specifies HTTP method, path, status code,
       response field name, and expected value or error code
       {gap reason if failed}

  [x/] Single service boundary — story lives entirely within one microservice
       {gap reason if failed}

  [x/] Story points estimated — one of: 1 / 2 / 3 / 5 / 8 (not 0, not 13+)
       {gap reason if failed}

  [x/] Blocked-by links set — or explicitly confirmed none
       {gap reason if failed}

  [x/] No Section 18 items anywhere in the story description or ACs
       {gap reason if failed}

  [x/] Tech constraints complete — service, port, branch pattern, PR target,
       CLAUDE.md read instruction all present
       {gap reason if failed}

  [x/] Seed / test data identified — table name or synthetic values described
       so the Dev Agent knows what data to use for testing
       {gap reason if failed}

  [x/] AI Context section complete — service name, port, call path,
       response field sources, and external calls all named
       {gap reason if failed}
```

### Step D — Decision

Collect this attempt's gaps:
```
attempt_gaps = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
             + [all Story Quality items marked as GAP]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition:** `attempt_gaps` is empty (all 9 items checked) **and** the Stage 2 benchmark verdict is PASS

Print quality scorecard:
```
STORY QUALITY SCORECARD — Story {story_index} — Attempt {attempt}
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/run/review/{name}-benchmark.md)
  User story format           : {PASS | GAP}
  ACs curl-verifiable         : {PASS | GAP}
  Single service boundary     : {PASS | GAP}
  Story points estimated      : {PASS | GAP}
  Blocked-by set              : {PASS | GAP}
  No Section 18 items         : {PASS | GAP}
  Tech constraints complete   : {PASS | GAP}
  Seed data identified        : {PASS | GAP}
  AI Context complete         : {PASS | GAP}

  VERDICT : {ALL PASSED — story approved | GAPS — {n} items incomplete}
```

**If ALL PASSED:**
- Set `loop_passed = true`
- Exit the loop for this story → proceed to Phase 1 (Create in JIRA)

**If GAPS and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_gaps` to `all_gaps`
- Increment `attempt`
- Return to LOOP start (Step A) — next attempt will address all gaps

**If GAPS and attempt = max_attempts:**
- Go to Escalation for this story — flag it in the final report

---

## Phase 1 — Create in JIRA (reached only on PASS)

For each story that passed:

1. Resolve the parent Epic. The Epic must already exist and carry label `plumbline-prd-approved` (created by the PM Eval Loop).
   If the input was plain English or a Confluence page and no approved Epic exists, STOP: "Run /plumbline-pm first — BA never creates Epics."
2. Apply the JIRA Write Guard, then create the story linked to the Epic:
   `createJiraIssue(issueTypeName: "Story", parent: {epicKey}, ...)`
3. Set blocked-by links using `createIssueLink` where dependencies exist
4. Assign to the Principal Architect (accountId: 712020:a0088ae5-186b-4263-bf8d-41ed37df1f95)

---

## Phase 2 — DoR Checklist + Label

For every story created, output the DoR checklist. A story is NOT ready for development
until ALL items are checked.

```
DEFINITION OF READY — SCRUM-{n}
  [x] User story written (As a / I want / So that)
  [x] Acceptance criteria present and curl-verifiable
  [x] Single microservice boundary — no cross-service DB access
  [x] Story points estimated (1/2/3/5/8)
  [x] Blocked-by links set (or confirmed none)
  [x] No out-of-scope items per CLAUDE.md Section 18
  [x] Tech constraints section complete (service, port, branch, PR target)
  [x] Seed data or test data identified
  [ ] Architect design doc approved (label: plumbline-arch-approved) ← run /plumbline-arch SCRUM-{n}
```

Apply the JIRA Write Guard, then add label `plumbline-dor-ready` to each story that passed.

---

## Phase 3 — Summary to User

```
BA EVAL LOOP — DECOMPOSITION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Epic
  {SCRUM-key}: {epic summary}

Stories Created
  {SCRUM-key}: {story summary} [{points} pts] — Eval Loop: {attempt}/{max} attempts — DoR: 8/8 checks (arch pending)
  ...

Stories Escalated (require PM Eval Loop revision)
  {story summary} — persistent gaps: {list}

Blocked-By Links
  {SCRUM-key} blocked by {SCRUM-key}

Out of Scope (flagged, not ticketed)
  - {item}: reason per CLAUDE.md Section 18

Next Step
  Run /plumbline-arch SCRUM-{n} for each story before development begins.

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

## Escalation — reached when a story has persistent gaps after 3 attempts

```
BA EVAL LOOP — STORY ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story "{summary}" has quality gaps that could not be resolved in {max_attempts} draft attempts.
This indicates the Epic or requirement needs revision at the PM level.

Persistent gaps:
{numbered list of all_gaps with specific reason for each}

Root cause: The story cannot be written correctly because the requirement
is incomplete or contradictory. The PM Eval Loop must revise the Epic first.

Recommended action:
1. Run /plumbline-pm epic:{epic-key} to revisit the PRD
2. Specifically address: {list of gap areas}
3. Re-run /plumbline-ba epic:{epic-key} after the PRD is updated
```

Do NOT create a JIRA ticket for an escalated story. Flag it in the Phase 3 report.

---

## Hard Stops — always pause and ask the user

- Requirement mentions anything in CLAUDE.md Section 18 (Out of Scope for POC)
- Cannot determine which microservice owns a domain concept
- Requirement would require cross-service database access
- Requirement would require a new microservice not in CLAUDE.md Section 3
- Story points estimate is 13+ after both attempts (story too large — needs splitting)
