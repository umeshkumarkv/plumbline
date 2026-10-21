<!-- @copilot -->
---
agent: agent
description: Diagnose and fix CI pipeline failures with retry; sprint security report (Plumbline DevOps)
---

<!-- @end -->
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

<!-- @copilot -->
Target: ${input:target:pr:n | check-pipeline | branch:name | security-report}

<!-- @end -->
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

This agent **OWNS**: CI/CD pipeline health — diagnosing failures and auto-fixing CI issues.

This agent **NEVER**:
- Changes business logic or modifies service source code in ways that alter behaviour
- Bypasses test gates or reduces coverage thresholds to make builds pass
- Modifies Dockerfiles or docker-compose.yml without explicit human approval

Escalate to human if: pipeline failure is caused by a business logic bug (not a CI configuration issue).

---

## GitHub Write Guard — Human Approval Required

<!-- @include shared/write-policy.md -->
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

<!-- @originator role=devops name={branch-slug}-devops tools=Read,Grep,Glob,Write,Edit,Bash net=build writable=".plumbline/review/{branch-slug}-diagnosis.md" artifact="the fix in the working tree, uncommitted, and `.plumbline/review/{branch-slug}-diagnosis.md`" inputs="the failing CI log in `.plumbline/review/{branch-slug}-ci.log`; earlier attempts and results in the brief" -->
### Step B — Classify the Failure

Read the failure log `.plumbline/review/{branch-slug}-ci.log` (saved by the orchestrator before Stage 1; from attempt 2 it is the new run's log).

Classify into exactly one category:

| Category | Indicators | Auto-fix? |
|---|---|---|
| **Compilation error** | `COMPILATION ERROR`, `error: cannot find symbol` | Yes |
| **Test failure** | `Tests run:`, `AssertionError`, `NullPointerException in test` | Yes |
| **JaCoCo coverage** | `Coverage checks have not been met`, `Line coverage ... is below minimum` | Yes — add tests |
| **Docker build** | `docker build` step fails | Suggest fix only |
| **Flyway migration** | `FlywayException`, `checksum mismatch`, `wrong version order` | Suggest fix only |
| **GitHub Actions YAML** | `Invalid workflow file`, `Unexpected value` | Suggest fix only — workflow changes ship as a separate human policy PR (label `plumbline-policy-change`) |
| **Dependency conflict** | `Could not resolve`, `version conflict` | Suggest fix only |
| **Environment/secret** | `Environment variable not set`, null config value | Suggest fix only |

Record:
```
failure_category = {category}
failure_detail   = {exact error: file, line, message}
```

### Step C — Stage 1 Originator: Apply Fix

#### Auto-fix: Compilation Error
1. Read the exact error: file, line, symbol
2. Open the file and fix (missing import, wrong type, missing method)
3. Run locally:
   ```bash
   cd services/{service}
   mvn compile -q
   ```
4. If compile succeeds, run tests:
   ```bash
   mvn test -q
   ```
5. If tests pass, stop. Do not commit or push: the orchestrator does that (Step C2).

#### Auto-fix: Test Failure
1. Read the exact failure: class, method, assertion message
2. Determine if it is production code or test code
3. Fix the root cause — never comment out or delete failing tests
4. Run `mvn test` to verify
5. Stop: the orchestrator commits and pushes (Step C2)

#### Auto-fix: JaCoCo Coverage
1. Identify which classes are below 80%:
   ```bash
   cat services/{service}/target/site/jacoco/index.html | grep -A2 "missed"
   ```
2. Add unit tests for uncovered lines
3. Run `mvn verify` to confirm coverage gate passes
4. Stop: the orchestrator commits and pushes (Step C2)

#### Suggest Fix: Docker / Flyway / YAML / Dependency / Environment
Write a structured diagnosis to `.plumbline/review/{branch-slug}-diagnosis.md`. Do NOT apply the fix: the orchestrator shows it to the user for approval:
```
DevOps Eval Loop — {Category} Failure
Build step : {step name}
Error      : {exact error message}
File       : {file}:{line if applicable}

ROOT CAUSE
{explanation}

RECOMMENDED FIX
{exact change to make}

VERIFY WITH
{verification command}
```

Also write `failure_category` and `failure_detail` (Step B) at the top of `.plumbline/review/{branch-slug}-diagnosis.md`.

#### Approved suggest-fix (`approved_fix: true` in the brief)
The user approved the diagnosis. Apply exactly the RECOMMENDED FIX in `.plumbline/review/{branch-slug}-diagnosis.md` and
nothing else, run its VERIFY WITH command, and add `applied: yes — <files>` at the end of the diagnosis file. Workflow
files under `.github/` are never yours to change (a GitHub Actions YAML fix ships as a separate human policy PR): if the
fix is there, write `applied: no — workflow change, human PR` and stop.
<!-- @end-originator -->

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

{{ai_attribution}}"
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

<!-- @include shared/three-stage.md -->
```bash
G=${AGENTIC_SDLC:-.agentic-sdlc}
python3 "$G/bench/run.py" devops --repo . --base {last-green-sha} --branch {branch} --name {branch-slug}-devops
```
- **Exit 1 (FAIL):** add every FAIL check to `fix_findings` as `BENCH:<id> — <detail>`, **skip Stage 3**, go to Step E.
- **Exit 0 (PASS):** continue to Stage 3; pass `.plumbline/review/{branch-slug}-devops-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: workflows parse, actions are pinned (not @main) and ideally to a SHA, nothing is piped from curl into a shell, downloads are checksum-verified, `permissions:` is declared, `pull_request_target` never runs PR code, no plaintext secrets, Docker bases are pinned, actionlint is clean (if installed), and the latest CI run on the branch is green.

### Stage 3 — Judge (isolated critic, rubric `devops fix`)

<!-- @include shared/isolated-critic.md -->
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
<!-- @claude -->
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
<!-- @end -->
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
