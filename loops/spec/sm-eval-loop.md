<!-- @copilot -->
---
agent: agent
description: Sprint health check, DoD gate and release notes with completeness check (Plumbline Scrum Master)
---

<!-- @end -->
# SM Eval Loop — Plumbline

Run a sprint health check with automated report completeness validation and retry.
Runs health checks → completeness evaluation → retry on incomplete data — max 3 attempts.
Escalates to human for unresolved blockers or DoD gate failures.

## Usage
```
/sm-eval-loop                — daily standup health check
/sm-eval-loop SCRUM-{n}      — single-ticket health check + DoD gate
/sm-eval-loop release-notes  — sprint-close: Release Notes → Confluence + Go/No-Go pack
```

<!-- @copilot -->
Target: ${input:target:daily | SCRUM-n | release-notes}

<!-- @end -->
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
- **Reporting:** report execution time as written. Token counts are not available in Copilot — omit them.
<!-- @end -->

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

<!-- @include shared/write-policy.md -->
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

## Daily Mode — /sm-eval-loop

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
Write all of it, **unedited**, to `.plumbline/review/sprint-{sprint}-facts.json`. This file is the originator's only input
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

<!-- @originator role=sm name=sprint-{sprint} writable=".plumbline/review/sprint-{sprint}-standup.md" tools=Read,Grep,Glob,Write artifact=".plumbline/review/sprint-{sprint}-standup.md" inputs="the raw sprint export in `.plumbline/review/sprint-{sprint}-facts.json` (Phase 0)" -->
#### Step B — Run 7 Health Checks

Run every check below. A ticket that fails a check is "flagged".

**Check 1: Stuck In Progress (> 2 days)**
- For each In Progress ticket: calculate `today - updatedAt`
- If > 2 days: flag as AT RISK

**Check 2: Stuck In Review (> 1 day)**
- For each In Review ticket: calculate `today - updatedAt`
- If > 1 day: flag as NEEDS ATTENTION

**Check 3: Blocked Tickets**
- For each ticket with blocked-by links: check if the blocker ticket is Done
- If blocker is NOT Done: flag as BLOCKED
- Build the full blocker chain

**Check 4: Unassigned To Do Tickets**
- For each To Do ticket with no assignee: flag

**Check 5: Stories Without Acceptance Criteria**
- For each ticket where description contains no "Acceptance Criteria" section: flag

**Check 6: Definition of Done Gate**
For every In Review ticket, verify all 7 DoD items:
```
DEFINITION OF DONE — SCRUM-{n}
  [x] All ACs pass (QA Eval Loop report: PASSED)
  [x] PR approved by a human CODEOWNER (reviewDecision = APPROVED) AND `plumbline/code-review` status = success on the current head SHA
  [x] mvn test passes (0 failures on CI)
  [x] JaCoCo >= 80%
  [x] PR merged to develop
  [x] JIRA ticket in In Review (not skipped from In Progress)
  [x] No open follow-up bugs from QA
```

Verify each item from the ticket's `pr` and `pr_state` in the facts file (fetched by the orchestrator in Phase 0).

**Check 7: Sprint Velocity**
- Count Done tickets and story points this sprint
- Compare to previous sprint Done count
- Calculate: On track / Ahead / Behind

#### Step C — Originator pre-flight (8 items, does not gate)

> Run this before Stage 2, to confirm the work was done. It does not decide anything: the Stage 2 benchmark recomputes
> every list and count from the facts file, and the Stage 3 judge rates the narrative. Any INCOMPLETE item here means
> fix the report first.

Check every item. Mark COMPLETE or INCOMPLETE with reason.

```
REPORT COMPLETENESS CHECK — Attempt {attempt}

  [x/] Sprint data fetched — no JIRA API errors, all tickets returned
       {incomplete reason if failed}

  [x/] All 7 health checks executed — no check skipped due to data error
       {incomplete reason if failed}

  [x/] Every AT RISK ticket has a flagged comment ready to post
       {incomplete reason if failed}

  [x/] Every BLOCKED ticket has a flagged comment ready to post
       {incomplete reason if failed}

  [x/] Every UNASSIGNED ticket has a flagged comment ready to post
       {incomplete reason if failed}

  [x/] DoD gate ran for every In Review ticket
       {incomplete reason if failed}

  [x/] Velocity metric calculated (current + previous sprint counts)
       {incomplete reason if failed}

  [x/] Standup summary covers all 6 sections: Done, In Review, In Progress, Blocked, At Risk, Velocity
       {incomplete reason if failed}
```

#### Step C0 — Write the report (Stage 1 output)

Write `.plumbline/review/sprint-{sprint}-standup.md` in this format (the orchestrator posts it verbatim in Phase 1):
```
Sprint Health — {YYYY-MM-DD}
Generated by SM Eval Loop — Attempt {attempt}/{max_attempts}

DONE
{List each Done ticket: - SCRUM-{n}: {summary}}
{If none: (none completed yet this sprint)}

IN REVIEW (awaiting merge)
{List each In Review ticket: - SCRUM-{n}: {summary} — PR open {n}h}
{If none: (none)}

IN PROGRESS
{List each In Progress ticket: - SCRUM-{n}: {summary} — {n} day(s)}
{If none: (none)}

BLOCKED
{List each blocked ticket: - SCRUM-{n}: {summary} — blocked by SCRUM-{x} ({blocker status})}
{If none: (none)}

AT RISK
{List stuck tickets: - SCRUM-{n}: {summary} — In Progress {n} days, no update}
{If none: (none)}

UNASSIGNED
{List: - SCRUM-{n}: {summary}}
{If none: (none)}

VELOCITY
  This sprint : {n} tickets Done
  Last sprint : {n} tickets Done
  Trend       : {On track | Ahead | Behind}

FLAGS FOR ACTION
{Summarise what needs human attention today}
{If any DoD check failed: list ticket + missing DoD items}
```

Then a `COMMENTS` section, one block per flagged ticket: `SCRUM-{n}:` followed by the comment text.
Comment text by flag:
- AT RISK: "SM Eval Loop ({date}): In Progress for {n} days without update. Is there a blocker?"
- BLOCKED: "SM Eval Loop ({date}): Blocked by SCRUM-{x} ({status}). Chain: {full chain}."
- UNASSIGNED: "SM Eval Loop ({date}): No assignee. Please assign before next sprint check."
- NO ACS: "SM Eval Loop ({date}): No ACs found. BA or Architect must add ACs."

Never edit the facts file.
<!-- @end-originator -->

#### Stage 2 — Benchmark (deterministic, no LLM)

<!-- @include shared/three-stage.md -->
```bash
G=${AGENTIC_SDLC:-.agentic-sdlc}
python3 "$G/bench/run.py" sm --artifact .plumbline/review/sprint-{sprint}-standup.md --facts .plumbline/review/sprint-{sprint}-facts.json --name sprint-{sprint}
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_incomplete` as `BENCH:<id> — <detail>`, **skip Stage 3**, go to Step D.
- **Exit 0 (PASS):** continue to Stage 3; pass `.plumbline/review/sprint-{sprint}-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: the 6 sections; Done, In Review, At Risk and Blocked list exactly the tickets the data implies; unassigned and no-AC tickets are flagged; velocity numbers equal the data; DoD for In Review tickets is checked on GitHub (human approval plus `plumbline/code-review` on the head).

#### Stage 3 — Judge (isolated critic, rubric `sm report`)

<!-- @include shared/isolated-critic.md -->
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

Post `.plumbline/review/sprint-{sprint}-standup.md` **verbatim**: it is the report that passed Stage 2 and Stage 3. Do not
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
<!-- @claude -->
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
<!-- @end -->
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

## Single-Ticket Mode — /sm-eval-loop SCRUM-{n}

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
  Velocity           : N/A (sprint-wide metric — run /sm-eval-loop for full sprint)

ACTIONS TAKEN
  {List each JIRA comment posted or transition applied, or "No action needed"}
```

---

## Sprint Close Mode — /sm-eval-loop release-notes

Run at sprint close after every story has a QA Eval Loop report (`/qa-eval-loop SCRUM-{n}`) and after `/devops-eval-loop security-report`.
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
