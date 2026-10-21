# Doc Eval Loop — Plumbline

Read a merged PR, update openapi.yaml and service CLAUDE.md, then validate completeness with retry.
Runs diff analysis → doc update → completeness check → retry on gaps — max 3 attempts.
On persistent gaps after 3 attempts, escalates to human for API contract review.
Always raises a docs PR — never commits directly to develop.

## Usage
```
/doc-eval-loop SCRUM-{n}
/doc-eval-loop pr:{n}
```

## How It Works

```
Attempt 1..3
  1 ORIGINATOR  updates openapi.yaml + CLAUDE.md ◄────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py doc ── FAIL ─────────────────────────────┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · doc completeness 8-item ── FAIL ────┘ then BOTH stages re-run
        ↓ PASS
  raise docs PR
After attempt 3 without PASS → ESCALATE → human (API contract review) (full attempt history, open + disputed items)
```

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: updating `openapi.yaml` and service `CLAUDE.md` to reflect what was merged.

This agent **NEVER**:
- Modifies Java source files, SQL migrations, pom.xml, or Docker configuration
- Raises PRs for code changes — only documentation PRs
- Commits directly to `develop` or `main` — always via a docs PR

Escalate to human if: the merged code contradicts the existing API contract in a way that requires architectural review.

---

## GitHub Write Guard — Human Approval Required

> **Plumbline write policy (applies to every agent).** JIRA *comments* are informational and need no approval.
> Always approval-gated: adding/removing labels, transitioning status, creating issues or Confluence pages,
> `git push`, `gh pr create`, `gh pr review` (approve / request-changes / overall comment), and any write to a CLAUDE.md file.

Before performing ANY of the following operations, STOP and request explicit user approval:
- `git push` — pushing the docs branch to origin
- `gh pr create` — raising the documentation PR

Approval format:
```
GITHUB ACTION — AWAITING YOUR APPROVAL
  Action  : {push branch "docs/SCRUM-{n}-update-docs" | create PR → develop}
  Branch  : docs/SCRUM-{n}-update-docs
  Reason  : {one-line reason}

Proceed? (yes / no)
```

---

## Phase 0 — Read the PR

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Find the PR for this ticket:
   ```bash
   gh pr list --search "SCRUM-{n}" --json number,title,headRefName,mergedAt
   ```
2. Fetch PR metadata and full diff:
   ```bash
   gh pr view {pr-number} --json title,body,files,headRefName,mergedAt
   gh pr diff {pr-number}
   ```
3. Fetch the linked JIRA story: `getJiraIssue(SCRUM-{n})`
4. Read `services/{service}/openapi.yaml` — note all existing paths and component schemas
5. Read `services/{service}/CLAUDE.md` — note current state of all sections

Analyse the diff and identify all of the following that changed:
- New REST endpoints (`@GetMapping`, `@PostMapping`, `@PatchMapping`, etc.)
- Changed response DTO fields
- New or changed HTTP error codes in GlobalExceptionHandler
- New custom exception classes (new error codes)
- New Kafka topics produced or consumed
- New Redis cache key patterns
- New Flyway migrations (schema changes)
- New Maven dependencies in pom.xml
- New environment variables

---

## Eval Loop State

Initialize before the loop:
```
attempt      = 1
max_attempts = 3
all_gaps     = []   ← accumulated completeness gaps across attempts
loop_passed  = false
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC EVAL LOOP — Attempt {attempt} / {max_attempts}
PR     : #{pr-number} — {pr-title}
Story  : SCRUM-{n}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_gaps` is not empty, they go to the originator through the feedback file (Stage 1, step 2): every gap
in this doc update must be addressed.

### Stage 1 — Originator: the `plumbline-doc-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the merged PR diff in `.plumbline/review/{ticket}-pr.diff`; its title and body in `.plumbline/review/{ticket}-pr.md`
2. **Feedback file (attempt 2+).** Write `.plumbline/work/{ticket}-doc/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/work/{ticket}-doc/brief.md`: the task in one paragraph, the input file paths, the artifact
   `services/{service}/openapi.yaml and the unit's CLAUDE.md (src/CLAUDE.md for a root app; root CLAUDE.md only if the architecture changed)`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${AGENTIC_SDLC:-.agentic-sdlc}
   python3 "$G/bench/scope_check.py" snapshot --name {ticket}-doc --writable "" --role doc
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-doc-originator` and the prompt `Brief: .plumbline/work/{ticket}-doc/brief.md`.
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
MERGE_SHA=$(gh pr view {pr-number} --json mergeCommit --jq .mergeCommit.oid)
python3 "$G/bench/run.py" doc --repo . --base "$MERGE_SHA^1" --service {service} --name {ticket}-doc   # touched = what the merged PR changed
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_gaps` as `BENCH:<id> — <detail>`, **skip Step E**, go to Step F.
- **Exit 0 (PASS):** continue to Step E; pass `.plumbline/review/{ticket}-doc-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: openapi.yaml parses, every endpoint this change added or modified is in openapi.yaml (older gaps are reported as debt), BigDecimal fields are `type: string`, every Kafka topic and env var is in the service CLAUDE.md, new Maven dependencies are documented, relative links resolve.

### Step E — Stage 3 Judge: Completeness Check (8 items, isolated critic)

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
Rubric `doc completeness 8-item`: the critic marks [x] COMPLETE or [ ] GAP with specific reason for each GAP.

```
DOC COMPLETENESS CHECKLIST — Attempt {attempt}

  [x/] Every new @GetMapping/@PostMapping/@PatchMapping in the diff has an openapi.yaml path entry
       {gap reason: list missing endpoints}

  [x/] Every new Response DTO field appears in the corresponding openapi.yaml component schema
       {gap reason: list missing fields}

  [x/] Every new HTTP error code (GlobalExceptionHandler additions) has an openapi.yaml response entry
       {gap reason: list missing error codes}

  [x/] Every new Kafka topic (produced or consumed) is documented in service CLAUDE.md
       {gap reason: list missing topics}

  [x/] Every new Redis cache key pattern is documented in service CLAUDE.md
       {gap reason: list missing keys}

  [x/] Every new environment variable is documented in service CLAUDE.md
       {gap reason: list missing vars}

  [x/] Every new Maven dependency is documented in service CLAUDE.md dependencies section
       {gap reason: list missing dependencies}

  [x/] openapi.yaml field types are correct — monetary = string, UUID = string+format:uuid,
       timestamp = string+format:date-time (no monetary fields as type: number)
       {gap reason: list incorrect field types}
```

### Step F — Decision

Collect this attempt's gaps:
```
attempt_gaps = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
             + [all completeness items marked as GAP]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition:** `attempt_gaps` is empty (all 8 completeness items met) **and** the Stage 2 benchmark verdict is PASS

Print completeness scorecard:
```
DOC COMPLETENESS SCORECARD — Attempt {attempt}
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/review/{name}-benchmark.md)
  New endpoints documented        : {COMPLETE | GAP — {n} missing}
  New DTO fields in schema        : {COMPLETE | GAP — {n} missing}
  New error codes documented      : {COMPLETE | GAP — {n} missing}
  New Kafka topics in CLAUDE.md   : {COMPLETE | GAP — {n} missing}
  New Redis keys in CLAUDE.md     : {COMPLETE | GAP — {n} missing}
  New env vars in CLAUDE.md       : {COMPLETE | GAP — {n} missing}
  New dependencies in CLAUDE.md   : {COMPLETE | GAP — {n} missing}
  openapi.yaml field types correct: {COMPLETE | GAP — {n} incorrect}

  VERDICT : {ALL COMPLETE — raise docs PR | GAPS — {n} items incomplete}
```

**If ALL COMPLETE:**
- Set `loop_passed = true`
- Exit the loop → go to Phase 1 (Raise Docs PR)

**If GAPS and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_gaps` to `all_gaps`
- Increment `attempt`
- Return to LOOP start (Step A) — next attempt will fill all gaps

**If GAPS and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — Create Docs Branch and PR (reached only on PASS)

> CLAUDE.md is a protected path (gates/checks/protected_paths.py). This PR passes the guardrails check only after the service tech lead adds the `plumbline-policy-change` label and approves it as CODEOWNER. Say so in the PR body.

```bash
git checkout develop
git pull origin develop
git checkout -b docs/SCRUM-{n}-update-docs

git add services/{service}/openapi.yaml
git add services/{service}/CLAUDE.md
# Add CLAUDE.md (root) only if it was changed in Step D

git commit -m "$(cat <<'EOF'
docs({service}): update openapi.yaml and CLAUDE.md for SCRUM-{n}

- {bullet: what was added to openapi.yaml}
- {bullet: what was added to CLAUDE.md}
- Doc Eval Loop: passed on attempt {attempt}/{max_attempts}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

The originator edited `openapi.yaml` and `CLAUDE.md` in the working tree only; nothing leaves the machine until this
approval. If the user says no, restore both files (`git checkout -- <files>`).

Apply the **GitHub Write Guard**, then push:
```bash
git push -u origin docs/SCRUM-{n}-update-docs
```

Apply the **GitHub Write Guard**, then create PR:
```bash
gh pr create \
  --title "docs({service}): sync openapi.yaml and CLAUDE.md for SCRUM-{n}" \
  --base develop \
  --body "$(cat <<'EOF'
## Documentation sync for SCRUM-{n}

Updates openapi.yaml and service CLAUDE.md to reflect the implementation merged in PR #{n}.
Doc Eval Loop: passed on attempt {attempt}/{max_attempts}.

### Changes
- openapi.yaml: {what was added/updated}
- CLAUDE.md: {what was added/updated}

### Completeness verified
All 8 doc completeness checks passed.

Generated by Doc Eval Loop
EOF
)"
```

---

## Phase 2 — Summary to User

```
DOC EVAL LOOP — SCRUM-{n} COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Eval Loop  : Passed on attempt {attempt} / {max_attempts}
{if attempt > 1: Gaps resolved: {list}}

FILES UPDATED
  services/{service}/openapi.yaml  — {n} endpoint(s) + {n} schema(s) added/updated
  services/{service}/CLAUDE.md     — {what sections updated}
  {CLAUDE.md (root) updated: {what} | CLAUDE.md (root): no changes}

DOCS PR
  {pr-url}

NO CHANGES NEEDED
  {list any files checked but needing no update}

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

## Escalation — reached when gaps persist after 3 attempts

```
DOC EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Documentation for SCRUM-{n} has completeness gaps that could not be resolved in {max_attempts} attempts.
This may indicate a conflict with the existing API contract that requires architectural review.

Persistent gaps:
{numbered list of all_gaps with specific items missing}

Root cause: The merged code may contradict the existing API contract, or the diff contains
patterns that need clarification before documentation can be written accurately.

Recommended action:
1. Review the persistent gaps above
2. If the merged code changes an existing API contract — run /arch-eval-loop SCRUM-{n}
3. Re-run /doc-eval-loop SCRUM-{n} after the contract is clarified
```

STOP — do not raise a partial docs PR.

---

## Hard Stops — always pause and ask the user

- A new microservice appears in the diff — root CLAUDE.md Section 3 needs human review first
- The diff includes Kafka topic changes affecting multiple services' CLAUDE.md files
- openapi.yaml has a schema conflict with an existing definition
- A new Maven dependency was added without a corresponding CLAUDE.md Section 2 update (Tech Stack)
- The merged code contradicts the existing openapi.yaml spec in a way that cannot be auto-resolved
