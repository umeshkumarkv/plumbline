# DevOps Eval Loop — Plumbline

Diagnose CI/CD pipeline failures, apply fixes, and verify the pipeline goes green — with retry.
Runs diagnose → fix → verify (local + CI) → retry on CI failure — max 3 attempts.
On persistent failure after 3 attempts, escalates to human with full log evidence.

## Usage
```
/devops-eval-loop pr:{n}              — fix a failing CI pipeline run
/devops-eval-loop check-pipeline      — check current pipeline state
/devops-eval-loop branch:{branch-name} — check a specific branch
/devops-eval-loop security-report     — sprint-close: Veracode + BlackDuck scan → Confluence
```

## How It Works

```
Attempt 1..3
  1 ORIGINATOR  diagnoses + fixes CI ◄────────────────────────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py devops (pipeline checks · CI green) ── FAIL  ┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · devops fix ── FAIL ─────────────────┘ then BOTH stages re-run
        ↓ PASS
  report FIXED
After attempt 3 without PASS → ESCALATE → human (with logs) (full attempt history, open + disputed items)
```

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: CI/CD pipeline health — diagnosing failures and auto-fixing CI issues.

This agent **NEVER**:
- Changes business logic or modifies service source code in ways that alter behaviour
- Bypasses test gates or reduces coverage thresholds to make builds pass
- Modifies Dockerfiles or docker-compose.yml without explicit human approval

Escalate to human if: pipeline failure is caused by a business logic bug (not a CI configuration issue).

---

## GitHub Write Guard — Human Approval Required

> **Plumbline write policy (applies to every agent).** JIRA *comments* are informational and need no approval.
> Always approval-gated: adding/removing labels, transitioning status, creating issues or Confluence pages,
> `git push`, `gh pr create`, `gh pr review` (approve / request-changes / overall comment), and any write to a CLAUDE.md file.

Before performing ANY of the following operations, STOP and request explicit user approval:
- `git push` to any remote branch
- Docker file changes (`Dockerfile`, `docker-compose.yml`)
- GitHub Actions workflow changes (`.github/workflows/`)

Approval format:
```
GITHUB ACTION — AWAITING YOUR APPROVAL
  Action  : {push fix commit to "{branch}" | modify Dockerfile | update workflow {file}}
  Branch  : {branch}
  Reason  : {one-line reason}

Proceed? (yes / no)
```
Do NOT execute until the user types "yes".

---

## Phase 0 — Fetch Pipeline State

Record the session start time before any work begins:
```bash
START_TIME=$(date +%s)
```

```bash
# If PR number provided
gh pr view {n} --json headRefName --jq '.headRefName'

# List recent runs for the branch
gh run list --branch {branch} --limit 5 --json databaseId,status,conclusion,name,createdAt

# Find the latest failed run
gh run list --branch {branch} --limit 5 --json databaseId,conclusion \
  | jq '[.[] | select(.conclusion == "failure")] | first'

# Fetch full failure logs
mkdir -p .plumbline/review && gh run view {run-id} --log-failed > .plumbline/review/{branch-slug}-ci.log   # the originator's input
```

---

## Eval Loop State

Initialize before the loop:
```
attempt        = 1
max_attempts   = 3
all_findings   = []   ← accumulated fix attempts and results across attempts
fix_findings   = []   ← this attempt's BENCH:/JUDGE: findings (reset every attempt)
loop_passed    = false
last_run_id    = {the failing run ID}
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

Print:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEVOPS EVAL LOOP — Attempt {attempt} / {max_attempts}
Branch : {branch}
Run    : {run-id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_findings` is not empty, print:
```
PRIOR ATTEMPTS — context for this attempt:
{numbered list of prior fix attempts and their results}
```

### Stage 1 — Originator: the `plumbline-devops-originator` agent (isolated)

The originator is a separate subagent with its own context. You are the orchestrator: you do **not** write the artifact.
1. **Inputs as files.** The originator has no JIRA, GitHub, Confluence or network tools, so save everything it needs first: the failing CI log in `.plumbline/review/{branch-slug}-ci.log`; earlier attempts and results in the brief
2. **Feedback file (attempt 2+).** Write `.plumbline/work/{branch-slug}-devops/feedback.md`, one line per item from the last attempt:
   `<BENCH:id | JUDGE:id | SCOPE:path> — <check or rule> — <location> — <required fix>`. Copy the items; never your opinion.
3. **Brief.** Write `.plumbline/work/{branch-slug}-devops/brief.md`: the task in one paragraph, the input file paths, the artifact
   `the fix in the working tree, uncommitted, and `.plumbline/review/{branch-slug}-diagnosis.md``, the rulebook paths, the attempt number and (attempt 2+) the feedback file and the previous artifact.
   Working files live in `.plumbline/work/`, which the judge never reads.
4. **Snapshot, call, scope check.**
   ```bash
   G=${AGENTIC_SDLC:-.agentic-sdlc}
   python3 "$G/bench/scope_check.py" snapshot --name {branch-slug}-devops --writable ".plumbline/review/{branch-slug}-diagnosis.md" --role devops
   ```
   It prints `SNAPSHOT <dir> <sha>` and a `CHECK: …` line. Keep that line in your context (never in a file).
   Call the Agent tool with `subagent_type: plumbline-devops-originator` and the prompt `Brief: .plumbline/work/{branch-slug}-devops/brief.md`.
   Pass nothing else: not your reasoning, not the judge's free text.
   Then run the `CHECK:` command **exactly as printed** (copy it; do not retype the sha). It verifies the sha of the
   snapshot and checker copy with Python (works on macOS and Linux) and runs the check; exit 1 = violations or tampering.
   `<dir>` holds the snapshot and a private copy of the checker outside the repository; the sha check proves neither
   was swapped while the originator ran.
   **Exit 1:** each `SCOPE:` line is a violation. Revert it (restore the file, delete what was added, reset a moved ref),
   carry the items into the feedback file, and count the attempt as failed. **Exit 0:** continue.


### Step C2 — Commit and push (orchestrator)

For a suggest-fix category, show the diagnosis file to the user first. If they approve, run Stage 1 again with
`approved_fix: true` in the brief (same attempt: approval does not use up an attempt); if not, record it as
unresolved in `all_findings` and escalate.
Then apply the **GitHub Write Guard** and commit only the files the scope check accepted.

**Why DevOps pushes before Stage 2 and 3:** the evidence is a CI run on the fix, so the fix must reach the branch
first. The push goes to the feature branch `{branch}` only, never `main` or `develop`, and nothing is merged. If
Stage 2 or 3 then fails, the next attempt pushes a follow-up commit on the same branch; after attempt 3 it escalates.
```bash
git add {files changed by the originator}
git commit -m "fix(ci): {failure_category} in {file} — attempt {attempt}/{max_attempts}

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

### Step D — Verify CI Green

After any push (auto-fix or approved suggest-fix):

Wait for the new CI run to start:
```bash
# Poll until a new run appears (newer than last_run_id)
gh run list --branch {branch} --limit 5 --json databaseId,status,conclusion,createdAt | jq .
```

Check the new run result:
```bash
gh run view {new-run-id} --json status,conclusion | jq .
```

- If `conclusion = "success"` → CI GREEN — record, then run Stage 2 and Stage 3 below (CI green alone does not pass the loop)
- If `conclusion = "failure"` → CI STILL FAILING — save the new log (`gh run view {new-run-id} --log-failed > .plumbline/review/{branch-slug}-ci.log`), record findings and continue loop
- If `status = "in_progress"` → wait up to 5 minutes, re-check

Record:
```
fix_result = {CI GREEN | CI STILL FAILING — {new failure category}}
```

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
python3 "$G/bench/run.py" devops --repo . --base {last-green-sha} --branch {branch} --name {branch-slug}-devops
```
- **Exit 1 (FAIL):** add every FAIL check to `fix_findings` as `BENCH:<id> — <detail>`, **skip Stage 3**, go to Step E.
- **Exit 0 (PASS):** continue to Stage 3; pass `.plumbline/review/{branch-slug}-devops-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: workflows parse, actions are pinned (not @main) and ideally to a SHA, nothing is piped from curl into a shell, downloads are checksum-verified, `permissions:` is declared, `pull_request_target` never runs PR code, no plaintext secrets, Docker bases are pinned, actionlint is clean (if installed), and the latest CI run on the branch is green.

### Stage 3 — Judge (isolated critic, rubric `devops fix`)

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
Artifact: `git diff {last-green-sha}..HEAD` of this fix, written to `.plumbline/review/{branch-slug}-devops.diff`. Rubric `devops fix`:
```
  [x/] The fix addresses the classified root cause (diagnosis file), not a symptom
  [x/] No test, gate, coverage threshold or scanner was skipped, disabled or loosened to get green
  [x/] The change is minimal: nothing unrelated to the failure
  [x/] Rollback is possible by reverting this commit alone
  [x/] No secret, credential or environment-specific value was introduced
```
Add every critic finding to `fix_findings` as `JUDGE:<id> — <fix>`.

### Step E — Decision

**PASS condition:** CI run conclusion = "success" **and** the Stage 2 benchmark verdict is PASS, and the Stage 3 judge verdict is PASS

Print verification scorecard:
```
DEVOPS EVAL SCORECARD — Attempt {attempt}
  Stage 2 benchmark : {PASS | FAIL — n checks}
  Stage 3 judge     : {PASS | FAIL — n findings | NOT RUN}
  Failure category    : {category}
  Fix applied         : {description of fix}
  Local mvn test      : {PASS | FAIL | SKIPPED (suggest-fix)}
  CI run              : #{new-run-id} — {success | failure}
  New failure (if any): {category + detail}

  VERDICT : {PASSED — CI green, benchmark and judge PASS | NOT PASSED — {n} issues remain}
```

**If the PASS condition holds** (CI green, benchmark PASS, judge PASS):
- Set `loop_passed = true`
- Exit the loop → go to Phase 1

**If CI STILL FAILING, or `fix_findings` is not empty, and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `{ attempt, failure_category, fix_applied, fix_result, fix_findings }` to `all_findings`; reset `fix_findings = []`
- Increment `attempt`
- Update `last_run_id` to the new failing run ID
- Return to LOOP start (Step A)

**If the PASS condition does not hold and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — Report to User (reached only when the PASS condition holds)

```
DEVOPS EVAL LOOP — FIXED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch    : {branch}
CI Run    : #{run-id} — SUCCESS
Eval Loop : Fixed on attempt {attempt} / {max_attempts}
{if attempt > 1: What changed between attempts: {list}}

FIX SUMMARY
  Original failure : {category — file:line}
  Fix applied      : {description}
  Commit           : {commit hash}

Next step : {CI is green — PR is ready for review | manually verify the PR}

Execution time : {END_TIME=$(date +%s); elapsed=$((END_TIME-START_TIME)); printf '%dm %ds' $((elapsed/60)) $((elapsed%60))}
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
```

---

## Escalation — reached when CI fails after 3 fix attempts

```
DEVOPS EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline for branch {branch} failed after {max_attempts} fix attempts.

Fix history:
  Attempt 1: {category} — {fix applied} — {result}
  Attempt 2: {category} — {fix applied} — {result}
  Attempt 3: {category} — {fix applied} — {result}

Current failing CI run: #{run-id}
Latest error:
{full log excerpt of the current failure}

Human action required:
1. Review the fix history above — the failure may require business logic changes
2. If business logic change is needed, assign to the relevant dev
3. Re-run /devops-eval-loop pr:{n} after the fix is applied
```

STOP — do not push any further commits.

---

## Hard Stops — always pause and ask the user

- Auto-fix requires changes to production business logic (not CI config, compilation, or tests)
- Flyway migration has already been applied to a shared environment
- Docker or docker-compose.yml changes are needed (always require GitHub Write Guard)
- `.github/workflows/` YAML changes are needed (always require GitHub Write Guard)
- Multiple failure categories present simultaneously — diagnose all, fix none without approval
- `mvn test` fails after the auto-fix attempt with a new error category

---

## Sprint Security Report — /devops-eval-loop security-report

Run at sprint close against the `develop` branch. No eval loop — single pass.
Produces one Veracode SAST report and one BlackDuck SCA report published to Confluence.

### Step 1 — Build all services
```bash
mvn package -DskipTests -q
```
If build fails — STOP. Fix with `/devops-eval-loop check-pipeline` first.

### Step 2 — Run Veracode SAST
```bash
# Pinned scanner: URL + SHA-256 come from security/tool-versions.env (reviewed in PRs like any dependency).
# Never download "LATEST" and never pipe a remote script into a shell.
source security/tool-versions.env   # defines VERACODE_PIPELINE_SCAN_URL, VERACODE_PIPELINE_SCAN_SHA256
curl -sSfL "$VERACODE_PIPELINE_SCAN_URL" -o pipeline-scan.zip
echo "$VERACODE_PIPELINE_SCAN_SHA256  pipeline-scan.zip" | sha256sum -c - || { echo "CHECKSUM MISMATCH — STOP"; exit 1; }
unzip -o pipeline-scan.zip pipeline-scan.jar
for service in order-service client-service risk-service execution-service marketdata-service auth-service audit-service notification-service api-gateway; do
  java -jar pipeline-scan.jar \
    --veracode_api_id "$VERACODE_API_ID" \
    --veracode_api_key "$VERACODE_API_KEY" \
    --file "services/${service}/target/${service}-*.jar" \
    --json_output true \
    --json_output_file "veracode-${service}.json"
done
```

### Step 3 — Run BlackDuck SCA
```bash
source security/tool-versions.env   # defines DETECT_JAR_URL, DETECT_JAR_SHA256 (pinned Detect release)
curl -sSfL "$DETECT_JAR_URL" -o detect.jar
echo "$DETECT_JAR_SHA256  detect.jar" | sha256sum -c - || { echo "CHECKSUM MISMATCH — STOP"; exit 1; }
java -jar detect.jar \
  --blackduck.url="$BLACKDUCK_URL" \
  --blackduck.api.token="$BLACKDUCK_API_TOKEN" \
  --detect.project.name="broker-dealer" \
  --detect.project.version.name="sprint-{n}" \
  --detect.tools=DETECTOR
```

### Step 4 — Publish Security Report to Confluence

Create the page with `createConfluencePage` (apply the Write Guard first):
```
Space  : SCRUM
Parent : Releases
Title  : Security Report — {sprint name} — {date}

h2. Summary
|| Scanner || Critical || High || Medium || Low ||
| Veracode SAST | {n} | {n} | {n} | {n} |
| BlackDuck SCA | {n} | {n} | {n} | {n} |

h2. Veracode SAST — Findings by Service
|| Service || Severity || CWE || File:Line || Title ||

h2. BlackDuck SCA — Vulnerable Components
|| Component || Version || CVE || Severity || Direct/Transitive || Fixed In ||

h2. Go/No-Go Input
Critical or High SAST findings: {none | list}
Critical CVEs in direct dependencies: {none | list}
```
Report the page URL to the user. Do not post a JIRA comment without a valid page URL.

### Hard Stops — sprint security report
- `VERACODE_API_ID`, `VERACODE_API_KEY`, `BLACKDUCK_URL`, or `BLACKDUCK_API_TOKEN` not set
- `security/tool-versions.env` missing, or any scanner checksum does not match — never fall back to an unpinned download
- Build fails — cannot scan without JARs
