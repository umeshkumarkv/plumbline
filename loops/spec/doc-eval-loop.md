<!-- @copilot -->
---
agent: agent
description: Sync openapi.yaml and service CLAUDE.md after a merged PR, raise a docs PR (Plumbline Docs)
---

<!-- @end -->
# Doc Eval Loop — Plumbline

Read a merged PR, update openapi.yaml and service CLAUDE.md, then validate completeness with retry.
Runs diff analysis → doc update → completeness check → retry on gaps — max 3 attempts.
On persistent gaps after 3 attempts, escalates to human for API contract review.
Always raises a docs PR — never commits directly to develop.

## Usage
```
/plumbline-doc SCRUM-{n}
/plumbline-doc pr:{n}
```

<!-- @copilot -->
Target: ${input:target:SCRUM-n | pr:n}

<!-- @end -->
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

This agent **OWNS**: updating `openapi.yaml` and service `CLAUDE.md` to reflect what was merged.

This agent **NEVER**:
- Modifies Java source files, SQL migrations, pom.xml, or Docker configuration
- Raises PRs for code changes — only documentation PRs
- Commits directly to `develop` or `main` — always via a docs PR

Escalate to human if: the merged code contradicts the existing API contract in a way that requires architectural review.

---

## GitHub Write Guard — Human Approval Required

<!-- @include shared/write-policy.md -->
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

<!-- @originator role=doc name={ticket}-doc tools=Read,Grep,Glob,Write,Edit artifact="services/{service}/openapi.yaml and the unit's CLAUDE.md (src/CLAUDE.md for a root app; root CLAUDE.md only if the architecture changed)" inputs="the merged PR diff in `.plumbline/run/review/{ticket}-pr.diff`; its title and body in `.plumbline/run/review/{ticket}-pr.md`" -->
### Step B — Update openapi.yaml

File: `services/{service}/openapi.yaml`

For each new or changed endpoint in the diff:

1. Check if the path already exists in openapi.yaml
2. **If missing — add the full path entry:**
   ```yaml
   /api/v1/{resource}/{id}:
     get:
       summary: {Brief description}
       operationId: {operationId in camelCase}
       security:
         - bearerAuth: []
       parameters:
         - name: {id}
           in: path
           required: true
           schema:
             type: string
             format: uuid
       responses:
         '200':
           description: Success
           content:
             application/json:
               schema:
                 $ref: '#/components/schemas/{ResponseSchema}'
         '404':
           description: Not Found
           content:
             application/json:
               schema:
                 $ref: '#/components/schemas/ErrorResponse'
   ```
3. **If changed — update the existing entry** to match the actual implementation
4. For each new Response DTO field: add to the corresponding component schema
5. For each new error code: add a response entry with the error code documented

openapi.yaml field type rules (non-negotiable):
- Monetary fields: `type: string` (NEVER `type: number`)
- UUID fields: `type: string, format: uuid`
- Timestamps: `type: string, format: date-time`
- All response schemas reference `#/components/schemas/...`
- All endpoints require `security: - bearerAuth: []`

### Step C — Update Service CLAUDE.md

File: the unit's own CLAUDE.md — `services/{service}/CLAUDE.md`, or `src/CLAUDE.md` for an app at the repository root
(the root CLAUDE.md is the master file; Step D). Edit only the affected rows: add or correct entries, never rewrite or
drop sections. Inside an `<!-- plumbline:begin onboard -->` block, keep its markers.

Add entries for everything new found in the diff:

- **New endpoint:** add to Endpoints section
  `| {METHOD} /api/v1/{resource}/{id} | {description} | {status codes} |`

- **New Kafka topic (produced or consumed):** add to Kafka Topics section
  `| {topic.name} | Producer/Consumer | {description} |`

- **New Redis cache key:** add to Redis Cache Keys section
  `| {domain}:{entity}:{id} | {TTL} | {invalidation trigger} |`

- **New Maven dependency:** add to Dependencies section
  `| {groupId}:{artifactId} | {version} | {purpose} |`

- **New environment variable:** add to Environment Variables section
  `| {VAR_NAME} | {description} | required/optional |`

### Step D — Root CLAUDE.md (only if architecture changed)

Only modify root `CLAUDE.md` if the PR introduced ONE of:
- A brand new microservice
- A new Kafka topic not previously in Section 7
- A new architectural pattern not previously described
- A change to the order lifecycle state machine (Section 5)

If none of the above: leave root `CLAUDE.md` completely unchanged.
<!-- @end-originator -->

### Stage 2 — Benchmark (deterministic, no LLM)

<!-- @include shared/three-stage.md -->
```bash
G=${PLUMBLINE_HOME:-.plumbline}
MERGE_SHA=$(gh pr view {pr-number} --json mergeCommit --jq .mergeCommit.oid)
python3 "$G/bench/run.py" doc --repo . --base "$MERGE_SHA^1" --service {service} --name {ticket}-doc   # touched = what the merged PR changed
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_gaps` as `BENCH:<id> — <detail>`, **skip Step E**, go to Step F.
- **Exit 0 (PASS):** continue to Step E; pass `.plumbline/run/review/{ticket}-doc-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: openapi.yaml parses, every endpoint this change added or modified is in openapi.yaml (older gaps are reported as debt), BigDecimal fields are `type: string`, every Kafka topic and env var is in the service CLAUDE.md, new Maven dependencies are documented, relative links resolve.

### Step E — Stage 3 Judge: Completeness Check (8 items, isolated critic)

<!-- @include shared/isolated-critic.md -->
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
  Stage 2 benchmark   : {PASS | FAIL — n checks}   (.plumbline/run/review/{name}-benchmark.md)
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

{{ai_attribution}}
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
<!-- @claude -->
Tokens consumed: {session input + output tokens from the Claude Code usage counter if visible}
<!-- @end -->
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
2. If the merged code changes an existing API contract — run /plumbline-arch SCRUM-{n}
3. Re-run /plumbline-doc SCRUM-{n} after the contract is clarified
```

STOP — do not raise a partial docs PR.

---

## Hard Stops — always pause and ask the user

- A new microservice appears in the diff — root CLAUDE.md Section 3 needs human review first
- The diff includes Kafka topic changes affecting multiple services' CLAUDE.md files
- openapi.yaml has a schema conflict with an existing definition
- A new Maven dependency was added without a corresponding CLAUDE.md Section 2 update (Tech Stack)
- The merged code contradicts the existing openapi.yaml spec in a way that cannot be auto-resolved
