---
agent: agent
description: Validate a story's acceptance criteria via curl, Playwright, DB and Kafka with retry (Plumbline QA)
---

# QA Eval Loop — Plumbline

Validate all acceptance criteria against the running system with automated retry.
Runs AC execution → evaluation → retry on failure — max 3 attempts.
On persistent failure after 3 attempts, escalates to human.

## Usage
```
/qa-eval-loop SCRUM-{n}
```

Target: ${input:target:SCRUM-n}

## How It Works

```
Classify ACs → REST | UI | BOTH
Attempt 1..3
  1 ORIGINATOR  runs the ACs, records evidence ◄──────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py qa (evidence · replay) ── FAIL ──────────┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · qa evidence ── FAIL ────────────────┘ then BOTH stages re-run
        ↓ PASS
  post JIRA report
After attempt 3 without PASS → ESCALATE → human (full attempt history, open + disputed items)
```

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

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: executing acceptance tests (curl and Playwright) against the running Docker system.

This agent **NEVER**:
- Modifies source code, configuration files, Dockerfiles, pom.xml, or any project file
- Makes architecture decisions or implementation choices
- Diagnoses root causes — not the class name, not the method, not the exception type, not the likely cause
- Suggests, implies, or hints at any code change or fix
- Explains WHY a failure happened beyond the observable HTTP evidence
- Names any internal implementation detail (exception handler, filter, bean, annotation, etc.)

### What a failure report contains — exactly this, nothing more

```
[FAIL] {AC text}
  curl command : {exact curl used}
  Expected     : HTTP {n}
  Actual       : HTTP {n}
  Response body: {full JSON response body}
```

Any text beyond these four fields is out of scope. Do not add "Root cause:", "Fix required:",
"This happens because:", or any other explanatory line.

### Design Gap Rule — HARD STOP

If an AC fails because of a design issue (e.g. wrong field used for ownership comparison,
incompatible UUID domains, RBAC misconfiguration, missing header propagation), the QA Agent MUST:

1. STOP immediately — do not touch any code
2. Post the failure evidence to JIRA using the four-field format above only
3. Escalate to human with message: "Design gap found — run /arch-eval-loop SCRUM-{n}"
4. Do NOT attempt to fix the issue, suggest a workaround, or retry with a code change

A test failure caused by a design problem is not a QA failure. It is an architecture failure.
The Arch Agent must update the design. The Dev Agent implements. QA re-runs only after both.

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
  Action : {transition to "In Review" | transition to "In Progress" | etc.}
  Reason : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute the JIRA write operation until the user types "yes".

---

## Phase 0 — Setup (Plumbline Gate — Code Review must be approved first)

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

1. Fetch the JIRA story: `getJiraIssue(SCRUM-{n})`
2. Extract every acceptance criterion line by line from the description
3. Identify the service and endpoint(s) under test

### Gate — Code Review Approved

```bash
gh pr list --search "SCRUM-{n}" --json number,title,reviewDecision,headRefName,headRefOid | jq .
# bot review status on the current head commit
gh api repos/{owner}/{repo}/commits/{headRefOid}/status \
  --jq '.statuses[] | select(.context=="plumbline/code-review") | .state'
```

- If the `plumbline/code-review` status on the PR's current head is not `success` — STOP: "Run /code-review-eval-loop SCRUM-{n} first."
- If `reviewDecision` is NOT `"APPROVED"` — STOP: "A human CODEOWNER must approve the PR (the bot never approves)."
- If no PR exists — STOP: "No PR found. Run /dev-eval-loop SCRUM-{n} first."

4. Verify required Docker services are running:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "api-gateway|client-service|order-service|auth-service"
```
If any required service is not running — STOP and tell the user.

5. Verify the frontend dev server is reachable:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```
- If returns `200` — frontend is running, proceed.
- If not reachable — note it; Playwright config will auto-start it via `npm run dev`
  (`reuseExistingServer: true` in `playwright.config.ts`). Do not manually start it.

6. Verify Playwright browsers are installed:
```bash
cd frontend && \
  npx playwright install chromium --dry-run 2>&1 | head -3
```
If browsers are missing: `npx playwright install chromium` — wait for completion.

7. Obtain JWT token for curl-based REST checks:
```bash
export TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$PLUMBLINE_DEMO_USER\",\"password\":\"$PLUMBLINE_DEMO_PASSWORD\"}" | jq -r '.data.token')
```
Verify the token is not null/empty before proceeding.

8. Verify PostgreSQL is reachable (needed for DB state verification):
```bash
docker exec postgres psql -U brokerdealer -d brokerdealer -c "SELECT 1" -q 2>&1
```
If this fails — note "DB verification unavailable" and skip all DB state checks; do NOT stop the eval loop.

Identify the service's schema name from `services/{service}/CLAUDE.md` or CLAUDE.md Section 3.
Common schemas: `order_schema`, `client_schema`, `execution_schema`, `audit_schema`.

9. Verify Kafka is reachable and identify the topics this story produces:
```bash
docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null | head -20
```
If Kafka is unreachable — note "Kafka verification unavailable" and skip all Kafka checks; do NOT stop the eval loop.

From the ticket's tech constraints and CLAUDE.md Section 7, identify:
- Which Kafka topics the story's endpoint(s) produce (e.g. `order.state.changed`, `execution.completed`)
- If none — mark Kafka verification as N/A for this story

> **POC vs QA environment behaviour**
>
> The current "skip if unavailable" rule for DB (step 8) and Kafka (step 9) is a
> local Docker accommodation for the POC — infrastructure is not always up.
>
> When this pipeline is promoted to a dedicated Dev or SQA environment where DB
> and Kafka are always-on services, change the failure behaviour of steps 8 and 9
> from **skip** to **STOP**: if either check fails, halt the eval loop immediately
> and tell the user to fix the infrastructure before retrying. A QA pass in a
> dedicated environment must include DB state and Kafka event evidence — a story
> that cannot prove persistence and event publication has not been validated.

---

## Phase 0b — AC Classification

Before entering the loop, classify every AC from the JIRA ticket on two axes:

**Axis 1 — Test layer**

| Label  | When to use                                                                          |
|--------|--------------------------------------------------------------------------------------|
| `REST` | AC describes HTTP status, JSON response body, envelope structure, or a field value   |
| `UI`   | AC describes what the user sees — form renders, button state, toast, navigation, label, error message displayed |
| `BOTH` | AC is a submit flow — test both the API response AND the resulting UI feedback       |

**Axis 2 — Mutation type** (applies only to REST and BOTH ACs)

| Label      | When to use                                                                        |
|------------|------------------------------------------------------------------------------------|
| `MUTATING` | AC exercises POST, PATCH, PUT, or DELETE — creates or modifies persisted state     |
| `READ`     | AC exercises GET — reads existing state, nothing is written                        |

`MUTATING` ACs get DB state verification + Kafka event verification in Step C.
`READ` ACs skip Step C (no write → nothing new to confirm in DB or Kafka).

Print the classification table before entering the loop:
```
AC CLASSIFICATION — SCRUM-{n}
  AC-1 [REST][MUTATING] : POST /api/v1/orders returns 202 with orderId
  AC-2 [UI]             : Order Entry form shows Limit Price field when LIMIT is selected
  AC-3 [BOTH][MUTATING] : Submitting a valid order shows success toast and navigates to blotter
  AC-4 [REST][READ]     : GET /api/v1/orders/{id} returns order with correct status
  ...
```

`REST` ACs → executed by the originator in Step B1 (curl).
`UI` and `BOTH` ACs → executed by the originator in Step B2 (Playwright).
`BOTH` ACs are also covered in Step B1 for the API assertion.
`MUTATING` ACs (REST or BOTH) → also executed in Step C (DB + Kafka).

**Save the plan for the originator** (it cannot read your context). Write `.plumbline/review/{ticket}-story.md` (the
ticket's summary, description and ACs as fetched) and `.plumbline/review/{ticket}-qa-plan.json`:
```json
{"ticket": "SCRUM-{n}", "acs": [{"id": "AC-1", "text": "…", "layer": "REST", "mutation": "MUTATING"}],
 "urls": {"gateway": "http://localhost:8080", "frontend": "http://localhost:5173"},
 "db": {"available": true, "schema": "order_schema"}, "kafka": {"available": true, "topics": ["order.state.changed"]},
 "login_env": ["PLUMBLINE_DEMO_USER", "PLUMBLINE_DEMO_PASSWORD"]}
```
Never write a credential value or a token into either file.

---

## Eval Loop State

Initialize before the loop:
```
attempt        = 1
max_attempts   = 3
failed_acs     = []   ← ACs that failed in current attempt (REST or UI)
all_failures   = {}   ← map of AC → failure evidence across attempts
loop_passed    = false
spec_file      = "frontend/e2e/qa-scrum-{n}-attempt-{attempt}.spec.ts"
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QA EVAL LOOP — Attempt {attempt} / {max_attempts}
Story  : SCRUM-{n} — {summary}
Layers : REST (curl) + UI (Playwright/Chromium) + DB State (psql) + Kafka Events
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_failures` is not empty, print:
```
PREVIOUSLY FAILED — watch these specifically this attempt:
{list of previously failed ACs and their failure reason}
```

---

### Stage 1 — Originator: the `plumbline-qa-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the story in `.plumbline/review/{ticket}-story.md`; the test plan in `.plumbline/review/{ticket}-qa-plan.json` (AC classification, stack URLs, which of Postgres/Kafka are reachable, the names of the login env vars — never their values)
2. **Feedback file (attempt 2+).** Write `.plumbline/work/{ticket}-qa/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/work/{ticket}-qa/brief.md`: the task in one paragraph, the input file paths, the artifact
   `.plumbline/review/{ticket}-qa-results.json and screenshots under frontend/test-results/`, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${AGENTIC_SDLC:-.agentic-sdlc}
   python3 "$G/bench/scope_check.py" snapshot --name {ticket}-qa --writable ".plumbline/review/{ticket}-qa-results.json" --role qa
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Run the **`plumbline-qa-originator`** subagent (`#agent/runSubagent`, agent name `plumbline-qa-originator`, defined in `.github/agents/plumbline-qa-originator.agent.md`) with the prompt `Brief: .plumbline/work/{ticket}-qa/brief.md`. It starts with a clean context and only read, search, edit, terminal tools. If this VS Code cannot run subagents, stop and tell the user: update VS Code / enable the Run Subagent tool (never do the originator's work in this chat).
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
python3 "$G/bench/run.py" qa --results .plumbline/review/{ticket}-qa-results.json --story .plumbline/review/{ticket}-story.md --repo . --replay --name {ticket}-qa
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_failures` as `BENCH:<id> — <detail>`, **skip Stage 3**, go to Step E.
- **Exit 0 (PASS):** continue to Stage 3; pass `.plumbline/review/{ticket}-qa-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: every story AC has a result; every REST result has a command, status and full body; recorded verdicts agree with expected vs actual status; 2xx bodies use the envelope; money is a JSON string; UI screenshots exist; the 4 mandatory edge cases are recorded; recorded GETs reproduce on replay (mutating calls are never replayed).

### Stage 3 — Judge (isolated critic, rubric `qa evidence`)

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
2. Run the **`plumbline-critic`** subagent (`#agent/runSubagent`, agent name `plumbline-critic`, defined in
   `.github/agents/plumbline-critic.agent.md`: clean context, read and search tools only). Pass **only**: the artifact path,
   the rubric name, the rubric file path, rulebook paths (root `CLAUDE.md`, the service `CLAUDE.md`, and
   the domain pack — see *Domain pack* below), the impact bundle path when there is one, the
   **benchmark report** `.plumbline/review/{name}-benchmark.md` as `BENCHMARK`, and (from attempt 2) the prior finding ids with
   their locations. Never pass anything from `.plumbline/work/`, your reasoning, drafts, the attempt number or a verdict to aim for.
   - **If this VS Code cannot run subagents:** ask the user to open a **new** Copilot chat and run `/plumbline-critic` with
     the same inputs, then paste back its JSON. A review done in this same chat is **self-attested**: label it so in every
     JIRA/PR comment; it cannot satisfy a gate.
   - **Additionally, for PR code:** the `plumbline-critic` CI job (`gates/ci/critic.yml`) re-reviews the pushed PR diff.
3. Check the critic's evidence before using it: for each `location` finding, confirm the quoted text exists at that path and line. Drop findings whose quote does not match, and note them as `discarded (evidence mismatch)` in the scorecard.
4. Use the critic's `items` as this step's PASS/GAP results and its `findings` as the attempt's gaps. Feed the optimizer only the findings (rule, location, fix), never the critic's free-text reasoning.
5. On the final attempt the critic runs again on the final artifact (verifier pass). The loop only passes if that run is PASS.

**Domain pack.** If `.agentic-sdlc/project.yaml` has `domain_pack:`, pass that path (or no pack when it says `none`).
Without a project.yaml, pass `${AGENTIC_SDLC:-.agentic-sdlc}/packs/domain-rules/rules.yaml` (the broker-dealer pack).
Never apply another domain's rules to this repository.
Artifact: `.plumbline/review/{ticket}-qa-results.json`. Rubric `qa evidence`:
```
  [x/] Each AC is proven by an assertion on the field and value the AC names, not only by the status code
  [x/] MUTATING ACs: the DB row and Kafka event shown match what the AC changes (entity id, new state, payload fields)
  [x/] Edge-case evidence exercises the real condition (e.g. 401 sent with no token, not a bad URL)
  [x/] No AC was marked SKIP or N/A without a stated infrastructure reason
  [x/] UI assertions check the behaviour the AC describes, not only that the element exists
```
Add every critic finding to `attempt_failures` as `JUDGE:<id> — <fix>`.

### Step E — Evaluate

Collect this attempt's failures:
```
rest_failures   = [REST/BOTH ACs that failed curl + failed REST edge cases]
ui_failures     = [UI/BOTH ACs that failed Playwright + failed UI edge cases]
db_failures     = [MUTATING ACs where DB state verification failed — wrong state or row missing]
kafka_failures  = [MUTATING ACs where Kafka event was not found on the expected topic]
attempt_failures = [every Stage 2 benchmark FAIL check, as BENCH:<id>] + [every Stage 3 judge finding, as JUDGE:<id>]
                 + rest_failures + ui_failures + db_failures + kafka_failures
```

**PASS condition:** `attempt_failures` is empty (zero failures across all four layers) **and** the Stage 2 benchmark verdict is PASS, and the Stage 3 judge verdict is PASS

Note: `db_failures` and `kafka_failures` only apply when the infrastructure was available in Phase 0.
If DB/Kafka was marked "unavailable", those layers are excluded from the PASS condition for this run.

Print scorecard:
```
QA EVAL SCORECARD — Attempt {attempt}
  Stage 2 benchmark : {PASS | FAIL — n checks}
  Stage 3 judge     : {PASS | FAIL — n findings | NOT RUN (benchmark FAIL)}
  REST AC Results:
    [PASS] {AC text}
           curl    : {exact curl command}
           HTTP    : {status}
           Response: {full JSON response body — do not truncate}
           DB state: {psql row — or "N/A (READ)" or "SKIP (unavailable)"}
           Kafka   : {topic} → {full message JSON — or "N/A" or "SKIP (unavailable)"}
    [FAIL] {AC text}
           curl    : {exact curl command}
           Expected: HTTP {n}
           Actual  : HTTP {n}
           Response: {full JSON response body}
           DB state: {psql output or failure reason}
           Kafka   : {output or "No message found for entity {id}"}

  UI AC Results:
    [PASS] {AC text}
           Assertion  : {playwright assertion text}
           Screenshot : test-results/qa-scrum-{n}-attempt-{attempt}/{ac-slug}.png
    [FAIL] {AC text}
           Error      : {playwright error message}
           Screenshot : test-results/qa-scrum-{n}-attempt-{attempt}/{ac-slug}.png

  REST Edge Cases:
    [PASS/FAIL] Unknown ID → 404
                curl    : {exact curl}
                Response: {full body}
    [PASS/FAIL] Missing auth → 401
                curl    : {exact curl}
                Response: {full body}
    [PASS/FAIL] Response envelope structure
                Fields present: data={yes/no}, meta.timestamp={yes/no}, meta.requestId={yes/no}
    [PASS/FAIL] Monetary values as Strings
                Field checked: {field name} = {raw JSON value}

  UI Edge Cases:
    [PASS/FAIL/SKIP] Unauthenticated → login redirect
    [PASS/FAIL/SKIP] Incomplete form → submit disabled
    [PASS/FAIL/SKIP] Sidebar navigation → correct route
    [PASS/FAIL/SKIP] Role restriction → element hidden

  SUMMARY : {n} passed / {total} total ({rest_n} REST + {ui_n} UI + {db_n} DB + {k_n} Kafka)
  VERDICT : {ALL PASSED | FAILED — {n} failures ({r} REST, {u} UI, {d} DB, {k} Kafka)}
```

**If ALL PASSED:**
- Set `loop_passed = true`
- Delete the generated spec file: `rm frontend/e2e/qa-scrum-{n}-attempt-{attempt}.spec.ts`
- Exit the loop → go to Phase 1 (Post Report)

**If FAILED and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Merge `attempt_failures` into `all_failures`
- Increment `attempt` and update `spec_file` to use new attempt number
- Add JIRA comment: "QA Eval Loop attempt {prev} FAILED — {n} ACs failed ({r} REST, {u} UI). Starting attempt {attempt}."
- Wait 5 seconds, then return to LOOP start (Step A)
- The new spec file for attempt N replaces the previous one — delete the old spec before writing:
  `rm -f frontend/e2e/qa-scrum-{n}-attempt-{prev}.spec.ts`

**If FAILED and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — Post JIRA Report (reached only on PASS)

Compile full report:
```
QA Eval Loop Report — SCRUM-{n}
Date      : {ISO 8601 timestamp}
Service   : {service-name}
Eval Loop : Passed on attempt {attempt} / {max_attempts}

REST AC RESULTS
---------------
[PASS] {AC text}
       curl    : {exact curl command}
       HTTP    : {status}
       Response: {full JSON response body — do not truncate}
       DB state: {full psql row — or "N/A (READ-only AC)" or "SKIP (DB unavailable)"}
       Kafka   : {topic} → {full message JSON — or "N/A (no events)" or "SKIP (Kafka unavailable)"}
...

UI AC RESULTS
-------------
[PASS] {AC text}
       Assertion : {playwright assertion text}
       Screenshot: test-results/qa-scrum-{n}-attempt-{attempt}/{ac-slug}.png
         (screenshot has annotated banner at top showing AC text + assertion)
...

REST EDGE CASES
---------------
[PASS] Unknown ID → 404
       curl    : {exact curl}
       Response: {full body with error.code={RESOURCE}_NOT_FOUND}
[PASS] Missing auth → 401
       curl    : {exact curl}
       Response: {full body}
[PASS] Response envelope: data + meta present
       Fields  : data=yes, meta.timestamp=yes, meta.requestId=yes
[PASS] Monetary values: all Strings
       Field   : {field name} = "{value}" (String confirmed)

UI EDGE CASES
-------------
[PASS] Unauthenticated → redirected to /login
       Screenshot: test-results/qa-scrum-{n}-attempt-{attempt}/ui-edge-unauth.png
[PASS] Incomplete form → PLACE ORDER disabled
       Screenshot: test-results/qa-scrum-{n}-attempt-{attempt}/ui-edge-incomplete.png
[PASS] Sidebar navigation → reached /{route}
       Screenshot: test-results/qa-scrum-{n}-attempt-{attempt}/ui-edge-nav.png
[PASS/SKIP] Role restriction: {note}
       Screenshot: test-results/qa-scrum-{n}-attempt-{attempt}/ui-edge-role.png

SUMMARY: {n} passed / {n} total ({r} REST + {u} UI + {d} DB + {k} Kafka) — ALL PASSED

QA PASSED — {total}/{total} checks verified. Ready to merge.
```

Add JIRA comment with the full report.

The ticket is already **In Review** (set by Dev Eval Loop when the PR was raised).
Do NOT transition the status — it is correct as-is.
The SM Agent will transition In Review → Done after the PR is merged and DoD is verified.

Post execution audit comment on SCRUM-{n} (no Write Guard required — informational only):
```
END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME))
```
Comment body:
```
⏱ QA Eval Loop Execution Audit ({ISO 8601 timestamp})
  Execution time : {printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
  Attempts used  : {attempt} / {max_attempts}
  REST ACs       : {n} / {n} passed
  UI ACs         : {n} / {n} passed
  Outcome        : ALL ACs PASSED — ready for SM Agent merge gate
```

---

## Phase 2 — Summary to User

```
QA EVAL LOOP — SCRUM-{n} COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story        : {summary}
JIRA         : In Review
REST ACs     : {n} / {n} passed
UI ACs       : {n} / {n} passed
REST Edges   : 4 / 4 passed
UI Edges     : {n} / 4 passed (or SKIP noted)
Eval Loop    : Passed on attempt {attempt} / {max_attempts}
Screenshots  : frontend/test-results/qa-scrum-{n}-attempt-{attempt}/
{if attempt > 1: What changed between attempts: {list}}

Next step  : Merge PR → run /sm-eval-loop to close sprint gate

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
```

---

## Escalation — reached when all 3 attempts fail

```
QA EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCRUM-{n} failed QA after {max_attempts} attempts.

PERSISTENTLY FAILING — REST ACs:
{for each REST AC in all_failures:
  AC       : {ac text}
  Attempts : {n}
  Last curl: {full response body}
  Expected : {expected}
  Actual   : {actual}
}

PERSISTENTLY FAILING — UI ACs:
{for each UI AC in all_failures:
  AC         : {ac text}
  Attempts   : {n}
  Last error : {playwright error message — includes expected vs actual}
  Screenshot : test-results/qa-scrum-{n}-attempt-3/{ac-slug}.png
}
```

Post to JIRA as a comment (informational — no approval needed) — use ONLY the four-field evidence format below.
Do NOT add root cause analysis, class names, fix suggestions, or explanatory text of any kind.

```
QA Eval Loop ESCALATED — SCRUM-{n}
Failed after {max_attempts} attempts.

FAILING REST ACs:
{for each REST AC in all_failures — four fields only:}
  AC           : {ac text}
  curl command : {exact curl used}
  Expected     : HTTP {n}
  Actual       : HTTP {n}
  Response body: {full JSON response body}

FAILING UI ACs:
{for each UI AC in all_failures — three fields only:}
  AC         : {ac text}
  Expected   : {playwright assertion text}
  Actual     : {playwright error — expected vs received values only}
  Screenshot : test-results/qa-scrum-{n}-attempt-{max_attempts}/{ac-slug}.png
```

Apply JIRA Write Guard, then transition ticket: In Review → **In Progress**, and remove label `plumbline-code-review-approved` (the next push must be re-reviewed)

STOP — do not post passing report.

---

## Hard Stops — always pause and ask the user

- Required Docker services are not running and cannot be started
- JWT token cannot be obtained (auth-service down)
- An AC is ambiguous and cannot be mapped to a testable curl or Playwright assertion
- A FAIL appears caused by infrastructure (Docker networking, port conflict) — report observable evidence only, do not diagnose
- Playwright cannot find an element and the locator strategy is ambiguous — stop and ask what the correct selector is rather than guessing
- The generated spec file causes a TypeScript compilation error — fix the spec before running, do not `--ignore-errors`

**On any failure (including 500s):** report the four-field evidence format and stop.
Do not explain why the status code is wrong. Do not name what component caused it.
The Dev Agent owns diagnosis. The QA Agent owns evidence collection.