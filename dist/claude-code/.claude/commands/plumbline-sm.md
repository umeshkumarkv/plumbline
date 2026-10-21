# SM Eval Loop — Plumbline

Run a sprint health check with automated report completeness validation and retry.
Runs health checks → completeness evaluation → retry on incomplete data — max 3 attempts.
Escalates to human for unresolved blockers or DoD gate failures.

## Usage
```
/plumbline-sm                — daily standup health check
/plumbline-sm SCRUM-{n}      — single-ticket health check + DoD gate
/plumbline-sm release-notes  — sprint-close: Release Notes → Confluence + Go/No-Go pack
```

## How It Works (daily mode)

```
Attempt 1..3
  1 ORIGINATOR  builds the standup report ◄───────────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py sm (recomputed from JIRA) ── FAIL ───────┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · sm report ── FAIL ──────────────────┘ then BOTH stages re-run
        ↓ PASS
  post report + JIRA comments
After attempt 3 without PASS → ESCALATE → human (unresolved flags) (full attempt history, open + disputed items)
```

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: sprint health monitoring, velocity tracking, blocker detection, and DoD gate enforcement.

This agent **NEVER**:
- Modifies source code, design docs, or JIRA story descriptions
- Makes architecture or implementation decisions
- Closes a ticket without verifying DoD criteria: QA passed + PR merged + CI green

Escalate to human if: a ticket cannot be closed because DoD criteria are unmet.

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
  Action : {transition to "Done" | add label | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the JIRA write operation until the user types "yes".

---

## Daily Mode — /plumbline-sm

### Phase 0 — Fetch Sprint State

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

```
searchJiraIssuesUsingJql(
  "project = SCRUM AND sprint in openSprints() ORDER BY status ASC",
  fields: ["summary", "status", "assignee", "created", "updated", "blockedBy", "acceptanceCriteria", "labels"]
)
```

Group tickets by status: Done | In Review | In Progress | To Do

Fetch the previous sprint's Done count for velocity comparison.

For every In Review ticket, fetch its PR state from GitHub (the originator has no GitHub access):
```bash
gh pr list --search "SCRUM-{n}" --json number,reviewDecision,headRefOid,mergedAt,state
gh api repos/{owner}/{repo}/commits/{headRefOid}/status --jq '[.statuses[]|select(.context=="plumbline/code-review")|.state][0]'
```
Write all of it, **unedited**, to `.plumbline/run/review/sprint-{sprint}-facts.json`. This file is the originator's only input
and the benchmark's ground truth:
```json
{"today": "YYYY-MM-DD", "previous_done": 0, "issues": {"SCRUM-1": {"status": "In Progress", "assignee": null,
  "updated": "YYYY-MM-DD", "points": 3, "has_ac": true, "blocked_by": ["SCRUM-0"], "pr": 42,
  "pr_state": {"reviewDecision": "APPROVED", "code_review_status": "success", "merged": false}}}}
```

---

### Eval Loop State

Initialize before the loop:
```
attempt      = 1
max_attempts = 3
incomplete   = []   ← checks that returned incomplete or errored data
loop_passed  = false
```

---

### LOOP — repeat until loop_passed = true or attempt > max_attempts

#### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SM EVAL LOOP — Attempt {attempt} / {max_attempts}
Date : {YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `incomplete` is not empty, print:
```
INCOMPLETE FROM PRIOR ATTEMPT — retry these checks:
{list of incomplete checks}
```

### Stage 1 — Originator: the `plumbline-sm-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the raw sprint export in `.plumbline/run/review/sprint-{sprint}-facts.json` (Phase 0)
2. **Feedback file (attempt 2+).** Write `.plumbline/run/work/sprint-{sprint}/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/run/work/sprint-{sprint}/brief.md`: the task in one paragraph, the input file paths, the artifact
   `.plumbline/run/review/sprint-{sprint}-standup.md`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/run/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${PLUMBLINE_HOME:-.plumbline}
   python3 "$G/bench/scope_check.py" snapshot --name sprint-{sprint} --writable ".plumbline/run/review/sprint-{sprint}-standup.md" --role sm
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-sm-originator` and the prompt `Brief: .plumbline/run/work/sprint-{sprint}/brief.md`.
   Pass nothing else: not your reasoning, not the judge's free text.
   Then run the `CHECK:` command **exactly as printed** (copy it; do not retype the sha). It verifies the sha of the
   snapshot and checker copy with Python (works on macOS and Linux) and runs the check; exit 1 = violations or tampering.
   `<dir>` holds the snapshot and a private copy of the checker outside the repository; the sha check proves neither
   was swapped while the originator ran.
   **Exit 1:** each `SCOPE:` line is a violation. Revert it (restore the file, delete what was added, reset a moved ref),
   carry the items into the feedback file, and count the attempt as failed. **Exit 0:** continue.


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
python3 "$G/bench/run.py" sm --artifact .plumbline/run/review/sprint-{sprint}-standup.md --facts .plumbline/run/review/sprint-{sprint}-facts.json --name sprint-{sprint}
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_incomplete` as `BENCH:<id> — <detail>`, **skip Stage 3**, go to Step D.
- **Exit 0 (PASS):** continue to Stage 3; pass `.plumbline/run/review/sprint-{sprint}-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: the 6 sections; Done, In Review, At Risk and Blocked list exactly the tickets the data implies; unassigned and no-AC tickets are flagged; velocity numbers equal the data; DoD for In Review tickets is checked on GitHub (human approval plus `plumbline/code-review` on the head).

#### Stage 3 — Judge (isolated critic, rubric `sm report`)

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
Artifact: the standup report. Rubric `sm report`:
```
  [x/] Every flagged ticket states why and who must act
  [x/] Risks are ordered by impact on the sprint goal
  [x/] Comments to be posted are factual (no blame, no guesses presented as facts)
  [x/] Nothing in the narrative contradicts the facts file
```

#### Step D — Decision

Collect this attempt's incomplete items:
```
attempt_incomplete = [every Stage 2 benchmark FAIL check, as BENCH:<id>]
                   + [all report completeness items marked INCOMPLETE]
```
_If Stage 2 failed, the judge did not run: show every rubric row as `NOT RUN (benchmark FAIL)`. The verdict is GAPS._


**PASS condition:** `attempt_incomplete` is empty (all 8 completeness items met) **and** the Stage 2 benchmark verdict is PASS, and the Stage 3 judge verdict is PASS

Print completeness scorecard:
```
REPORT COMPLETENESS — Attempt {attempt}
  Sprint data fetched          : {COMPLETE | INCOMPLETE}
  All 7 checks executed        : {COMPLETE | INCOMPLETE}
  AT RISK comments ready       : {COMPLETE | INCOMPLETE — {n} tickets}
  BLOCKED comments ready       : {COMPLETE | INCOMPLETE — {n} tickets}
  UNASSIGNED comments ready    : {COMPLETE | INCOMPLETE — {n} tickets}
  DoD gate ran for all In Review : {COMPLETE | INCOMPLETE — {n} tickets}
  Velocity calculated          : {COMPLETE | INCOMPLETE}
  Standup covers all 6 sections: {COMPLETE | INCOMPLETE}

  VERDICT : {ALL COMPLETE — proceed to report | INCOMPLETE — {n} items}
```

**If ALL COMPLETE:**
- Set `loop_passed = true`
- Exit the loop → go to Phase 1

**If INCOMPLETE and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_incomplete` to `incomplete`
- Increment `attempt`
- Re-fetch data for the specific incomplete checks
- Return to LOOP start (Step A)

**If INCOMPLETE and attempt = max_attempts:**
- Go to Escalation (post report with incomplete items flagged)

---

### Phase 1 — Post Standup Report and JIRA Comments

Post `.plumbline/run/review/sprint-{sprint}-standup.md` **verbatim**: it is the report that passed Stage 2 and Stage 3. Do not
regenerate, reword or re-count it. Apply the **JIRA Write Guard** once for the batch, then:

1. Post the standup report (the file's report section) where the team reads it (sprint JIRA comment / channel).
2. Post each ticket comment listed in the file's `COMMENTS` section, exactly as written, to its ticket.
3. DoD transitions come from the facts file, not from the report text:

For In Review tickets where DoD PASSED:
- Add JIRA comment: "SM Eval Loop ({date}): DoD PASSED — all 7 gates verified. Closing as Done."
- Apply the **JIRA Write Guard**, then transition: In Review → **Done**

For In Review tickets where DoD FAILED:
- Add JIRA comment: "SM Eval Loop ({date}): DoD FAILED. Missing: {list items}. Cannot close as Done."
- Do NOT transition

---

### Phase 2 — Report to User

Print full standup summary.
List all JIRA comments posted.
Highlight the most urgent item needing human action today.

```
Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

### Escalation — incomplete report after 3 attempts

```
SM EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sprint health check could not be completed after {max_attempts} attempts.

Incomplete items:
{numbered list with reasons}

Root cause: Sprint data is unavailable or a ticket has a state the agent cannot resolve.

Human action required:
{list specific items: which tickets have DoD failures, which data is missing}

Note: Partial standup report posted below with INCOMPLETE items flagged.
```

Print the partial standup report with INCOMPLETE items clearly marked.

---

## Hard Stops — daily mode

- JIRA API returns an error fetching sprint data
- Cannot determine which sprint is active (multiple open sprints)
- A blocker chain creates a circular dependency (A blocks B blocks A)

---

## Single-Ticket Mode — /plumbline-sm SCRUM-{n}

Runs checks 1–6 against one specific ticket. No eval loop — single pass only (velocity requires sprint-wide data).

### Phase 0 — Fetch Ticket

```
getJiraIssue(issueIdOrKey: "SCRUM-{n}", fields: [...])
```

### Phase 1 — Run Applicable Checks

| Check | Applies when |
|-------|-------------|
| 1. Stuck In Progress (> 2 days) | status = In Progress |
| 2. Stuck In Review (> 1 day) | status = In Review |
| 3. Blocked | ticket has "is blocked by" issuelinks |
| 4. Unassigned | status = To Do and no assignee |
| 5. Missing ACs | description has no "Acceptance Criteria" section |
| 6. DoD Gate | status = In Review |

For DoD gate, run the full 7-item verification (same as daily mode Check 6).

### Phase 2 — Single-Ticket Report

```
SM Eval Loop — SCRUM-{n} — {YYYY-MM-DD}

Ticket  : SCRUM-{n} {summary}
Status  : {status}
Assignee: {name or UNASSIGNED}
Age     : {n} day(s) in current status

CHECKS
  Stuck In Progress  : {OK | AT RISK — {n} days | N/A}
  Stuck In Review    : {OK | NEEDS ATTENTION — {n} days | N/A}
  Blocked            : {None | BLOCKED by SCRUM-{x} ({blocker status})}
  Assignee           : {OK | UNASSIGNED}
  Acceptance Criteria: {Present | MISSING}
  DoD Gate           : {PASSED | FAILED — missing: [...] | N/A (not In Review)}
  Velocity           : N/A (sprint-wide metric — run /plumbline-sm for full sprint)

ACTIONS TAKEN
  {List each JIRA comment posted or transition applied, or "No action needed"}
```

---

## Sprint Close Mode — /plumbline-sm release-notes

Run at sprint close after every story has a QA Eval Loop report (`/plumbline-qa SCRUM-{n}`) and after `/plumbline-devops security-report`.
Assembles the full release pack for the Go/No-Go meeting. Decision is made by humans.

### Step 1 — Verify sprint is complete
```
searchJiraIssuesUsingJql(
  "project = SCRUM AND sprint in openSprints() AND status != Done AND status != 'In Review'"
)
```
If any story is In Progress or To Do — STOP.

### Step 2 — Collect all sprint stories and release artifacts from Confluence.

Search for:
- Sprint Test Plan
- Sprint Test Results
- Security Report

### Step 3 — Publish Release Notes to Confluence
```
createConfluencePage(
  spaceKey: "SCRUM",
  parentPageTitle: "Releases",
  title: "Release Notes — {sprint name} — {date}",
  body: {see template below}
)
```

Release Notes template:
```
h2. {Sprint Name} · {start date} → {end date}
Published: {ISO 8601 date}
Prepared by: SM Eval Loop · Human sign-off required before deployment

h2. What's New — Stories Delivered
|| Story || Summary || Service || Status ||
| SCRUM-{n} | {summary} | {service} | Done |

h2. Defects Fixed
{Stories tagged as bug-fix, or "None"}

h2. Known Issues / Deferred
{Stories moved out of sprint or not completed, or "None"}

h2. Release Artifacts
|| Document || Link || Status ||
| Sprint Test Plan | {url} | {Available / Missing} |
| Sprint Test Results | {url} | {Available / Missing} |
| Security Report | {url} | {Available / Missing} |

h2. Go/No-Go Checklist — For Human Meeting
|| # || Gate || Source || Status ||
| 1 | All sprint ACs validated and passed | Sprint Test Results | [ ] Confirmed |
| 2 | Regression suite: 0 failures | Sprint Test Results | [ ] Confirmed |
| 3 | Veracode SAST: no Critical or High findings | Security Report | [ ] Confirmed |
| 4 | BlackDuck SCA: no Critical CVEs | Security Report | [ ] Confirmed |
| 5 | JaCoCo ≥ 80% on all services — CI green | GitHub Actions | [ ] Confirmed |
| 6 | All sprint PRs merged to develop | GitHub | [ ] Confirmed |
| 7 | No open P1/P2 defects from QA | JIRA | [ ] Confirmed |
| 8 | Stakeholder sign-off received | Meeting | [ ] Confirmed |

h2. Decision
_To be completed in the Go/No-Go meeting._
GO [ ]  ·  NO-GO [ ]
Reason: _______________
Approved by: _______________
```

### Step 4 — Report to user
```
SM Eval Loop — Release Pack Complete
Sprint : {sprint name}
Stories: {n} delivered

Release Notes  : {confluence-url}
Test Plan      : {url or MISSING}
Test Results   : {url or MISSING}
Security Report: {url or MISSING}

NEXT STEP: Schedule Go/No-Go meeting.
```

## Hard Stops — release-notes mode

- Stories still In Progress — cannot produce release pack
- Confluence page creation fails — do not post JIRA comment without a valid page URL
