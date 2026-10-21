<!-- @copilot -->
---
agent: agent
description: Onboard a brownfield service: discovery, Confluence spec, service CLAUDE.md, critic (Plumbline Onboard)
---

<!-- @end -->
# Onboard Eval Loop — Plumbline Brownfield

Onboard an existing service into the Plumbline pipeline by producing a Confluence spec page,
a service CLAUDE.md, validating both with an adversarial critic, and syncing any drift
found in root CLAUDE.md (Kafka topics, Redis keys, service table, ports).
Runs: Discovery → BA (Confluence) → Arch (CLAUDE.md) → Critic → Cross-consistency → Root CLAUDE.md Sync.
Max 3 attempts on the service docs loop. Gate: `plumbline-onboard-approved` label on the JIRA story.

## Usage
```
/plumbline-onboard {{JIRA_KEY}}-{n}           ← JIRA story describes the service to onboard
/plumbline-onboard service:{name}      ← direct service name, no JIRA story
/plumbline-onboard service:all         ← auto-discover all modules, run per-module CLAUDE.md
                                          generation for each, then run global consistency check
```

<!-- @copilot -->
Target: ${input:target:{{JIRA_KEY}}-n | service:name | service:all}

<!-- @end -->
**Output:** the unit's CLAUDE.md — `services/{name}/CLAUDE.md`, `{name}/CLAUDE.md`, or `src/CLAUDE.md` for an app at the repository root — merged, never overwritten. The root CLAUDE.md is the master file.

---

<!-- @claude -->
## Setup — Required on Every Fresh Clone
<!-- @end -->
<!-- @copilot -->
## Setup — Copilot Terminal Approvals
<!-- @end -->

<!-- @claude -->
Before running this skill on a newly cloned repo, create `.claude/settings.local.json`
at the repo root with the following content. Without it, Claude Code will prompt for
approval on every individual scan command, interrupting the automated discovery phase.

```json
{
  "permissions": {
    "allow": [
      "Bash(find:*)",
      "Bash(grep:*)",
      "Bash(xargs:*)",
      "Bash(sed:*)",
      "Bash(sort:*)",
      "Bash(wc:*)",
      "Bash(cat:*)",
      "Bash(echo:*)",
      "Bash(node:*)",
      "Bash(npx:*)"
    ]
  }
}
```

**What each permission covers:**

| Permission | Used by |
|------------|---------|
| `Bash(find:*)` | Module discovery (build.gradle, pom.xml, package.json), entity/migration scans |
| `Bash(grep:*)` | Endpoint, Kafka, Redis, REST call, tech debt scans |
| `Bash(xargs:*)` | Piped grep over file lists (entity detection, changelog filtering) |
| `Bash(sed:*)` | Path trimming in module discovery output |
| `Bash(sort:*)` | Deduplication of discovered paths and endpoint lists |
| `Bash(wc:*)` | TypeScript `any` count (R6), changelog file count |
| `Bash(cat:*)` | Reading individual entity/config files |
| `Bash(echo:*)` | Section headers in scan output |
| `Bash(node:*)` | React dependency scan (R9) |
| `Bash(npx:*)` | Test coverage scan (R7 — vitest/jest) |
<!-- @end -->
<!-- @copilot -->
Copilot asks for approval before each terminal command. The discovery phase runs many
read-only scans (`find`, `grep`, `xargs`, `sed`, `sort`, `wc`, `cat`, `echo`, `node`, `npx`),
so you may want to auto-approve those in your IDE's Copilot terminal auto-approve setting.
<!-- @end -->

**Notes:**
- Auto-approve read-only commands only. Never auto-approve `git push`, `gh pr`, `rm`, or `mvn deploy`.
- Write Guard prompts (the "Proceed? yes/no" gates before writing any CLAUDE.md) are
<!-- @claude -->
  enforced by the skill itself — these permissions do NOT bypass them.
- For polyrepo architectures, create this file in each service's repo root.
- JIRA/Confluence MCP integration requires separate configuration in
  `~/.claude/settings.json` — see your team's MCP setup guide.
- Do NOT commit API tokens or credentials to `settings.local.json`.
  Use environment variables or a secrets manager for JIRA_API_TOKEN etc.
<!-- @end -->
<!-- @copilot -->
  enforced by this prompt itself — terminal auto-approval does NOT bypass them.
- For polyrepo architectures, run this prompt from each service's repo root.
- The Atlassian MCP server must be configured in Copilot's own mcp.json (see team setup guide).
- Never put API tokens or credentials in mcp.json or any committed file.
<!-- @end -->

---

## How It Works

```
Phase 0: DISCOVERY (automated scan — no LLM)
Attempt 1..3
  1 ORIGINATOR  BA + Arch draft Confluence + CLAUDE.md ◄──────────────┐
        ↓                                                             │ feedback: failing checks +
  2 BENCHMARK   bench/run.py onboard (every claim vs code) ── FAIL ───┤ findings (rule · location · fix)
        ↓ PASS                                                        │ originator fixes each, logs it,
  3 JUDGE       isolated critic · onboard critic + cross-consistency ── FAIL  ┘ then BOTH stages re-run
        ↓ PASS
  Write Guard → commit
After attempt 3 without PASS → ESCALATE → human + JIRA comment (full attempt history, open + disputed items)
```

Max attempts: 3 (service docs loop only). The critic runs on EVERY attempt in a fresh context (the isolated `plumbline-critic` subagent in both Claude Code and Copilot — see Step D).
Root CLAUDE.md sync always runs after the loop passes — it is not retried.
<!-- @copilot -->

---

## Copilot Runtime Conventions — read before anything else

- **Mode:** run in Copilot Chat **Agent** mode. Ask/Edit modes cannot call tools.
- **Subagents:** Stage 1 (originator) and Stage 3 (judge) run as isolated subagents from `.github/agents/`. They need a VS Code with custom-agent subagents and the **Run Subagent** tool (`agent/runSubagent`) enabled in this chat's tool picker. If it is missing, STOP before Stage 1 and tell the user (never do the originator's work in this chat); the judge has a new-chat fallback (`/plumbline-critic`).
- **Arguments:** use the value of `target` above (or text typed after the command) wherever this spec says `{{JIRA_KEY}}-{n}`, `pr:{n}`, etc.
- **Atlassian tools:** before the first JIRA or Confluence call, call `getAccessibleAtlassianResources` once, keep the `cloudId`, and pass it on every Atlassian call. Tool names may carry a server prefix (e.g. `atlassian_getJiraIssue`) — use the tool whose name ends with the name written in this spec.
- **Approval gates:** wherever this spec says "Write Guard", print the approval block, then END YOUR TURN and wait for the user's next message. Only an explicit "yes" from the user counts. Copilot's own tool-confirmation dialog is NOT the approval.
- **Project rules:** Copilot does not load `CLAUDE.md` automatically. When this spec says read `CLAUDE.md` or `services/{service}/CLAUDE.md`, open and read the file.
- **Terminal:** run shell commands with the terminal tool from the repo root. Pre-flight once per session: `gh auth status` (if the spec uses `gh`) and `java -version` if the spec uses `mvn` or Gradle: the JDK must match the Java version the build declares (`<java.version>` / `maven.compiler.release` / `<release>` in pom.xml, or the Gradle toolchain), e.g. 17 or 21. A newer JDK is acceptable only if `./mvnw -q -DskipTests compile` (or `mvn …`) succeeds with it; on macOS a matching JDK can be selected with `export JAVA_HOME=$(/usr/libexec/java_home -v <version>)`. Onboarding reads code and only needs the JDK for the optional coverage scan (J8): if no suitable JDK is available, skip J8 and record it, do not stop. If `gh auth status` fails, or another loop has no suitable JDK, STOP and tell the user.
- **Reporting:** report execution time as written. Token counts are not available in Copilot — omit them.
<!-- @end -->

---

## Agent Scope — Absolute Boundaries. No Exceptions.

This agent **OWNS**: producing `services/{name}/CLAUDE.md` (the file all other Plumbline agents
read) and a Confluence page draft for a brownfield service, validated to be internally
consistent and compliant with root CLAUDE.md standards.

**Output target:** the unit's CLAUDE.md (see the pattern below) and, in Phase 2, the master block of the root CLAUDE.md.

**The CLAUDE.md pattern: one master file at the root, one file per unit.**
- **Root `CLAUDE.md` — the master:** the whole solution and its architecture (what the system is for, its units and
  how they connect, shared rules), plus anything people keep there (runbooks, conventions).
- **One CLAUDE.md per unit** (`python3 "$G/impact/layout.py" .`): `services/<name>/CLAUDE.md`, `<module>/CLAUDE.md`,
  `ui/CLAUDE.md`; for an app at the repository root it is **`src/CLAUDE.md`** (Claude Code loads it when working in
  `src/`). Never put a unit's document into the root file.
- **Merge, never overwrite.** Generated content lives between `<!-- plumbline:begin <id> -->` and
  `<!-- plumbline:end <id> -->` (`onboard` in a unit file, `solution` in the root file). Writes go through
  `python3 "$G/bench/claude_merge.py"`, which replaces only that block or appends it, keeps every other line, and prints
  the diff for the Write Guard. Never hand-edit or rewrite a whole CLAUDE.md.
- Every write, new file or existing, goes through the Write Guard (Phase 1) with the merge diff.

This agent **ALSO OWNS**: patching root CLAUDE.md Sections 3, 7, and 8 when the onboarded
service reveals drift (wrong port, missing Kafka topic, stale or missing Redis key).

This agent **NEVER**:
- Modifies production source code
- Creates JIRA stories or Epics (it works FROM a story, not to create them)
- Invents behavior not evidenced in the actual codebase
- Skips the discovery phase — all outputs must be grounded in scanned facts
- Modifies root CLAUDE.md Sections 5, 6, 9, 10, 11 (state machine, validation rules,
  risk rules, domain rules, concurrency) — those require Principal Architect approval

---

## JIRA Write Guard — Human Approval Required

<!-- @include shared/write-policy.md -->
Before performing ANY of the following operations, STOP and request explicit user approval:
- Adding a label to a JIRA ticket
- Creating or updating a Confluence page
- Editing root CLAUDE.md (one approval per section changed)

Approval format:
```
ONBOARD ACTION — AWAITING YOUR APPROVAL
  Target : {JIRA ticket / Confluence page / root CLAUDE.md Section {n}}
  Action : {add label | post comment | create page | patch root CLAUDE.md}
  Change : {what exactly is being added / removed / corrected}
  Evidence: {file:line that proves the change}

Proceed? (yes / no)
```
Do NOT execute until the user types "yes".
For root CLAUDE.md: one approval per section — do NOT batch multiple sections.

---

## Phase 0 — Discovery (Automated Scan)

Record session start time:
```bash
START_TIME=$(date +%s)
```

**Step 0 — Find the unit and its stack (always runs first)**

```bash
python3 "${PLUMBLINE_HOME:-.plumbline}/impact/layout.py" .    # every unit: name, path, kind (service|frontend), build
```
Pick the unit named `{name}`. If it is not listed, STOP and show the list: the benchmark can only check a unit the
layout knows. A repo with another layout declares its units in `.plumbline/project.yaml` (a human edit; see
`.plumbline/README.md`). Set `DIR` to the unit's `path`. **Everywhere below, `services/{name}/` and `{name}/` mean
`$DIR/`**: for an app at the repository root `DIR` is `.`, its code is `./src/`, and its own CLAUDE.md is
`src/CLAUDE.md` (the root `CLAUDE.md` is the master file — see the CLAUDE.md pattern). Then set `STACK`:
```bash
[ -f "$DIR/pom.xml" ] || ls "$DIR"/build.gradle* >/dev/null 2>&1 && echo "STACK=java"
[ -f "$DIR/package.json" ]       && echo "STACK=react"     # any TypeScript SPA: React, Angular, Vue
[ -f "$DIR/angular.json" ]       && echo "FLAVOR=angular"  # use the Angular variants noted in the React scans
[ -f "$DIR/go.mod" ]             && echo "STACK=go"
[ -f "$DIR/requirements.txt" ]   && echo "STACK=python"
# If no marker found: STACK=unknown — stop and report to user before proceeding
```

Set `STACK` from the result above. Run only the matching scan block below, then always run the Universal scans.

---

### Java/Spring Boot Scans — run when STACK=java

```bash
# J1. Endpoints
find services/{name}/src -name "*Controller*" \
  -exec grep -h "@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping\|@RequestMapping" {} \;

# J2. Kafka consumers
grep -r "@KafkaListener" services/{name}/src --include="*.java" -A3

# J3. Kafka producers
grep -r "kafkaTemplate.send\|KafkaTemplate" services/{name}/src --include="*.java" -h | grep "send("

# J4. Entities
find services/{name}/src -name "*.java" -path "*/domain/*" | xargs grep -l "@Entity"

# J5. DB migrations (in order)
find services/{name}/src -name "V*.sql" | sort

# J6. Redis usage
grep -r "@Cacheable\|@CachePut\|@CacheEvict\|redisTemplate\|StringRedisTemplate" \
  services/{name}/src/main --include="*.java" -l

# J7. External REST calls
grep -r "RestTemplate\|WebClient" services/{name}/src/main --include="*.java" -l

# J8. Test coverage
mvn -f services/{name}/pom.xml test jacoco:report -q 2>/dev/null | tail -5 || echo "Coverage: run separately"

# J9. Application port
grep -r "server.port\|SERVER_PORT" services/{name}/src/main/resources/ 2>/dev/null | head -3
```

---

### React/TypeScript Scans — run when STACK=react

**Angular (`FLAVOR=angular`):** same template and sections; adapt the scans: routes come from `*routing*.ts` /
`app.routes.ts` (`Routes` arrays: `path:`, `component:`, `loadChildren`), API calls from services that inject
`HttpClient` (`this.http.get|post|put|patch|delete(`, base URLs from `environment*.ts`), state from services /
NgRx stores, the dev port from `angular.json` (`serve.options.port`, default 4200), and set Framework to Angular.
The benchmark reads API calls the same way for both (see `impact/depmap.py`).

```bash
# R1. Pages and route definitions
grep -r "path=" {name}/src --include="*.tsx" --include="*.ts" -h \
  | grep -E "Route|createBrowserRouter|path:" | sort -u
# Also check Next.js pages/ or app/ directory if present
find {name}/src/pages {name}/src/app -name "*.tsx" 2>/dev/null | sort

# R2. All API calls — collect every backend path called
grep -r "http\.\|axios\.\|fetch(" {name}/src --include="*.ts" --include="*.tsx" -h \
  | grep -oE "'[/a-zA-Z0-9_{}/$-]+'" | grep "api\|/" | sort -u
# Also check dedicated API client files
find {name}/src/api {name}/src/services {name}/src/lib -name "*.ts" 2>/dev/null | xargs ls -1 2>/dev/null

# R3. State management
grep -r "createSlice\|createStore\|useReducer\|create(" {name}/src --include="*.ts" --include="*.tsx" -l 2>/dev/null
grep -r "useQuery\|useMutation\|QueryClient" {name}/src --include="*.ts" --include="*.tsx" -l 2>/dev/null

# R4. Key components and pages
find {name}/src/components {name}/src/pages -name "*.tsx" 2>/dev/null | sort

# R5. Environment variables
find {name} -name ".env*" -not -path "*/node_modules/*" | xargs grep -h "VITE_\|REACT_APP_\|NEXT_PUBLIC_" 2>/dev/null | sort -u
grep -r "import.meta.env\|process.env" {name}/src --include="*.ts" --include="*.tsx" -h \
  | grep -oE "(VITE|REACT_APP|NEXT_PUBLIC)_[A-Z_]+" | sort -u

# R6. TypeScript compliance — any types in production code
grep -r ": any\|as any" {name}/src --include="*.ts" --include="*.tsx" -h \
  | grep -v "test\|spec\|\.test\." | wc -l

# R7. Test coverage
cd {name} && npx vitest run --coverage 2>/dev/null | tail -10 \
  || npx jest --coverage --passWithNoTests 2>/dev/null | tail -10 \
  || echo "Coverage: run separately"

# R8. Port / dev server
grep -E "port|proxy" {name}/vite.config.ts {name}/vite.config.js 2>/dev/null | head -5
grep '"dev"\|"start"' {name}/package.json | head -3

# R9. Dependencies (runtime only — no devDependencies)
node -e "const p=require('./{name}/package.json'); console.log(Object.keys(p.dependencies||{}).join('\n'))" 2>/dev/null \
  || grep -A50 '"dependencies"' {name}/package.json | grep -v "devDep" | head -30

# R10. Console.log in production code (tech debt marker)
grep -r "console\.log\|console\.warn\|console\.error" {name}/src --include="*.ts" --include="*.tsx" -l \
  | grep -v "test\|spec" | head -10
```

---

### Universal Scans — run for ALL stacks

```bash
# U1. Tech debt markers
grep -r "TODO\|FIXME\|HACK\|XXX" {name}/src --include="*.java" --include="*.ts" --include="*.tsx" -h \
  | head -20

# U2. OpenAPI spec — endpoint list
find services/{name} {name} -name "openapi.yaml" \
  -exec grep -E "^  /" {} \; 2>/dev/null | sort \
  || echo "openapi.yaml: not found"

# U3. Frontend API calls — verify route coverage (Java services only — skip for STACK=react)
grep -r "api/v1" frontend/src --include="*.ts" --include="*.tsx" -h 2>/dev/null \
  | grep -oE "/api/v1/[a-zA-Z0-9/_-]+" | sort -u \
  || echo "Frontend: not found or no matches"
```

Produce a **Discovery Report** using the template for the detected stack:

**Java/Spring Boot (STACK=java):**
```
DISCOVERY REPORT — {service-name} [Java/Spring Boot]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stack            : Java {version from pom.xml / Gradle} / Spring Boot {version}
Port             : {number from J9}
Endpoints        : {list from J1}
OpenAPI Gaps     : {diff J1 vs U2 — or "MATCH" / "spec not found"}
Kafka Consumed   : {topic → group-id from J2}
Kafka Produced   : {topic → trigger from J3}
Entities         : {list from J4}
DB Schema        : {schema, tables, migrations from J5}
Redis            : {configured / used / not used — from J6}
External Calls   : {service → endpoint → purpose from J7}
Frontend Routes  : {/api/v1 paths from U3 that target this service}
Tech Debt        : {from J1-J9 + U1 — or "None found"}
```

**React/TypeScript (STACK=react):**
```
DISCOVERY REPORT — {service-name} [React/TypeScript]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stack            : {React version, routing lib, state lib, test runner from R9}
Port / Dev URL   : {from R8}
Pages / Routes   : {list from R1}
API Calls        : {all backend paths from R2}
API Client Files : {from R2 file list}
State Mgmt       : {slices / stores / query hooks from R3}
Key Components   : {from R4}
Env Variables    : {from R5}
TypeScript any   : {count from R6 — flag if > 0 in production code}
Console.logs     : {files from R10 — flag all}
OpenAPI Gaps     : {diff R2 paths vs U2 — or "spec not found"}
Tech Debt        : {from R6 + R10 + U1 — or "None found"}
```

**Save it for the originator.** Write the full Discovery Report, followed by the raw output of every scan you ran
(J1–J9 or R1–R10, and U1–U3), to `.plumbline/run/review/{service-name}-discovery.md`. `{service-name}` is the module's
directory name (the same value as `{name}` above, e.g. `order-service` or `frontend`, never a path with `/`).
The originator drafts only from this file.

---

## Eval Loop State

```
attempt      = 1
max_attempts = 3
all_gaps     = []
critic_findings = []   ← refreshed by the isolated critic every attempt; prior list used only to verify resolution
loop_passed  = false
```

---

## LOOP — repeat until loop_passed = true or attempt > max_attempts

### Step A — Announce Attempt

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ONBOARD EVAL LOOP — {service-name} — Attempt {attempt} / {max_attempts}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If `all_gaps` or `critic_findings` are not empty, they go to the originator through the feedback file (Stage 1,
step 2): every item must be addressed before any output is produced.

---

<!-- @originator role=onboard name={service-name}-onboard writable=".plumbline/run/review/{service-name}-confluence.md .plumbline/run/review/{service-name}-CLAUDE.md" tools=Read,Grep,Glob,Write artifact=".plumbline/run/review/{service-name}-confluence.md and .plumbline/run/review/{service-name}-CLAUDE.md" inputs="the Phase 0 discovery results in `.plumbline/run/review/{service-name}-discovery.md`" -->
### Step B — BA Phase: Confluence Page

Write the Confluence page draft to `.plumbline/run/review/{service-name}-confluence.md` (the orchestrator publishes it in Phase 1, after approval), covering:

#### 1. Service Overview
- What this service does in business terms (one paragraph)
- Who consumes its outputs (other services, UI, external)
- What it must never do (business constraints)

#### 2. Existing Behavior — Endpoint Catalog
For each endpoint found in discovery:
```
{METHOD} {path}
  Auth required : {yes/no} | Roles: {list}
  Input         : {path vars, query params, request body fields}
  Output        : {response fields and their meaning}
  Business rule : {what business logic runs here}
  Error cases   : {error code → HTTP status → condition}
```

#### 3. Event Catalog
```
Produces: {topic} → when → payload summary
Consumes: {topic} → what it does on receive → idempotency check
```

#### 4. Business Rules
Numbered list of all business rules evidenced in the code.
Each rule must trace to a specific class or migration (e.g. "Rule 3: {{JIRA_KEY}}-48, MarketDataClient").

#### 5. Out of Scope
What this service explicitly does NOT do, per CLAUDE.md Section 18 or domain boundaries.

#### 6. Known Tech Debt
From discovery Phase 0 — flag explicitly, do not hide.

---

### Step C — Arch Phase: Service CLAUDE.md (Stage 1 originator)

Write the draft to `.plumbline/run/review/{service-name}-CLAUDE.md`. Never write `services/{service-name}/CLAUDE.md` before Phase 1 (Write Guard). Stage 2 and the critic review the draft.

Use the template matching the detected stack.

**Output:** the unit's CLAUDE.md — `services/{name}/CLAUDE.md`, `{name}/CLAUDE.md`, or `src/CLAUDE.md` for an app at the repository root — merged, never overwritten. The root CLAUDE.md is the master file.

**If STACK=react — use the React template below. If STACK=java — use the Java template further below.**

**Keep it concise (≤ 30 KB, benchmark OB-14).** Every agent loads this file. Catalog what agents act on (endpoints,
entities with key fields, topics, rules, must-nevers); for debt give counts and the top locations; put long inventories
in Confluence or leave them to the scans. A critic request for more detail than the rubric item asks for is answered by
pointing at the item, not by growing the file.

---

#### React/TypeScript Template

```markdown
# CLAUDE.md — {app-name}
# Part of {project name}
# Generated by /plumbline-onboard — Brownfield Onboarding

---

## 1. App Purpose
{2-3 sentences: what this frontend does, who uses it, what it renders}

---

## 2. Tech Stack

| Concern | Library | Version |
|---------|---------|---------|
| Framework | React | {from package.json} |
| Language | TypeScript | {from package.json} |
| Build | Vite / Next.js / CRA | {detected} |
| Routing | React Router / Next.js | {detected} |
| State | Redux Toolkit / Zustand / React Query | {detected} |
| UI | {component library if any} | {version} |
| HTTP | {axios / fetch / custom http client} | {version} |
| Testing | Vitest / Jest + RTL | {version} |

---

## 3. Port / Dev URL

{port from vite.config.ts or package.json dev script}
Proxy target: {backend base URL from vite proxy config}

---

## 4. Page / Route Catalog

| Path | Component | Auth Required | Role | Description |
|------|-----------|--------------|------|-------------|
| {route path} | {PageComponent} | {yes/no} | {roles} | {purpose} |

---

## 5. API Surface — All Backend Calls

List every backend endpoint the frontend calls, with the source file.

| Method | Path | Called From | Purpose |
|--------|------|------------|---------|
| {GET/POST/...} | {/api/v1/...} | {file:line} | {purpose} |

Every path comes from the code (the benchmark compares both ways: every call documented, nothing documented that the
code never calls). Calls that no backend endpoint serves keep their row with Purpose `no matching endpoint` (and a
Known Tech Debt line) — never invent what they do. Routes of this app (pages) belong in Section 4, not here.

---

## 6. State Management

{Describe the state approach: Redux slices / Zustand stores / React Query keys}

| Store / Slice / Query | Purpose | Persisted |
|-----------------------|---------|-----------|
| {name} | {what it holds} | {yes/no} |

---

## 7. Environment Variables

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| {VITE_API_URL} | Yes | Backend base URL | {{API_URL}} |

---

## 8. What This App Must NEVER Do

- Never call backend services directly (bypass the API gateway)
- Never store JWT or sensitive data in localStorage — use sessionStorage or memory
- Never hardcode API base URLs — always use environment variables
- Never commit .env files with real credentials

---

## 9. Key UX / Business Rules

{numbered list of UI-level business rules evidenced in components}
{e.g. "TRADER role sees only own orders — enforced by backend but also by route guard"}

---

## 10. Known Tech Debt

{R6: `any` count + top files (≤10); R10: console-call file count + up to 10 files; U1: TODO/FIXME — or "None"}

---

## 11. Compliance Notes

{TypeScript any count, console.log count, missing env var docs, missing test coverage}
```

---

#### Java/Spring Boot Template — use when STACK=java

Produce `services/{name}/CLAUDE.md` using this exact template:

```markdown
# CLAUDE.md — {service-name}
# Part of {project name}
# Read root CLAUDE.md first. This file adds service-specific detail.

---

## 1. Service Purpose
{2-3 sentences: what it does, what it owns, what triggers it}

---

## 2. Port
{number}

---

## 3. Database Schema
{schema name}

### Tables
| Table | Key Columns | Notes |
|-------|-------------|-------|
| {name} | {col: type} | {constraint or purpose} |

### Migrations Applied
| Version | Description |
|---------|-------------|
| V1 | {description} |
| V{n} | {description} |

---

## 4. Kafka Topics Produced
| Topic | Trigger | Payload |
|-------|---------|---------|

---

## 5. Kafka Topics Consumed
| Topic | Consumer Group ID | Action on Receive |
|-------|-------------------|-------------------|

Idempotency: {how this service avoids double-processing}

---

## 6. Redis Cache Keys Owned
{table of key → TTL → invalidation, or "None — Redis not used"}
Note if Redis is configured but unused.

---

## 7. REST Endpoints Exposed
See openapi.yaml for full schema.
| Method | Path | Auth Required | Role | Description |

---

## 8. REST Endpoints Called (Downstream Dependencies)
| Service | Method | Path | Purpose |
Client type: {RestTemplate / WebClient}
Failure handling: {circuit breaker / log+skip / retry}

---

## 9. Entities Owned
For each entity: list every field with type, nullability, and constraint.
Flag fields added by later migrations explicitly.

---

## 10. What This Service Must NEVER Do
{bullet list — one per boundary}

---

## 11. Key Business Rules
{numbered list — each traceable to code or migration}

---

## 12. Known Tech Debt
{list from discovery, or "None"}

---

## 13. CLAUDE.md Compliance Notes
{any deviations from root CLAUDE.md standards found during onboarding}
```

---
<!-- @end-originator -->

### Stage 2 — Benchmark (deterministic, no LLM)

<!-- @include shared/three-stage.md -->
```bash
G=${PLUMBLINE_HOME:-.plumbline}
python3 "$G/bench/run.py" onboard --artifact .plumbline/run/review/{service-name}-CLAUDE.md --repo . --service {service-name} --name {service-name}-onboard
```
- **Exit 1 (FAIL):** add every FAIL check to `attempt_gaps` as `BENCH:<id> — <detail>`, **skip Step D**, go to Step F.
- **Exit 0 (PASS):** continue to Step D; pass `.plumbline/run/review/{service-name}-onboard-benchmark.md` to the critic as `BENCHMARK`.
- **Exit 2:** your command or input file is wrong. Fix it and re-run; it is not a gap.
- Measured here, so the judge takes them as facts: all 11 sections; port and schema vs the code; endpoints, produced and consumed topics, downstream services, @Entity classes, migration tables and Redis prefixes are both documented (coverage) and real (no invented facts); TODO/FIXME markers are acknowledged.

### Step D — Stage 3 Judge: Critic Phase (every attempt, isolated)

The critic independently reads: actual source code + BA's Confluence draft + Arch's CLAUDE.md draft.
The critic does NOT produce either document — it only challenges them.

<!-- @include shared/isolated-critic.md -->
Rubric `onboard critic` (12 items for Java, 20 for React — listed below).

Critic checklist (check ALL, flag any that fail).

**What onboarding judges.** These documents *describe an existing system*. The question for every item is "does the
document state the truth about the code, at the level of detail asked for?" — never "is the code clean?". Pre-existing
debt (`any` types, console calls, localStorage tokens, missing tests) is a fact to RECORD in Tech Debt / Compliance
Notes; recorded accurately, it is a PASS. An item that does not apply to this unit (no entities, no migrations, no
Kafka in a frontend) is `N/A`, never a finding. CLAUDE.md is context for agents: counts, the top locations and pointers
beat exhaustive inventories — never demand a full list where the item asks for a count.

```
CRITIC REPORT — {service-name} — Attempt {attempt}

  [x/] Code vs Confluence: every endpoint in code appears in Confluence
       {gap if missed}

  [x/] Code vs CLAUDE.md: every entity appears in CLAUDE.md Section 9 with its key fields — id, foreign keys,
       status/enum fields, money and date fields, unique constraints (a full column list is NOT required)
       {gap if missed}

  [x/] Code vs CLAUDE.md: every table the migrations/SQL scripts create is in the schema section, and changes that
       alter meaning (dropped/renamed columns, new NOT NULL, changed constraints) are noted
       {gap if missed}

  [x/] Redis: actual usage matches what both docs claim
       (configured-but-unused is a valid finding — must be documented, not ignored)
       {gap if missed}

  [x/] Kafka: every @KafkaListener topic matches CLAUDE.md Section 5
       {gap if missed}

  [x/] External calls: every RestTemplate/WebClient call matches CLAUDE.md Section 8
       {gap if missed}

  [x/] Root CLAUDE.md compliance: service does not violate any "Must Never" rule
       (Section 3, Section 10, Section 11 — check all)
       {gap if missed}

  [x/] Tech debt: all TODO/FIXME/HACK markers documented in Section 12
       {gap if missed}

  [x/] No invented facts: every claim in Confluence and CLAUDE.md is traceable
       to actual code, a migration, or an explicit business rule in root CLAUDE.md
       {gap if missed}

  [x/] Brownfield-specific: schema evolution that changes an assumption a developer would make (ALTER TABLE,
       dropped constraints, DEFAULT added to NOT NULL columns) is called out — a one-line note each, not a column diff
       {gap if missed}

  [x/] OpenAPI spec: every endpoint in CLAUDE.md Section 7 appears in openapi.yaml
       and every path in openapi.yaml appears in CLAUDE.md (if spec exists)
       {gap if missed}

  [x/] Frontend coverage: any frontend API calls to this service's paths are
       reflected in CLAUDE.md Section 7 (no undocumented routes consumed by UI)
       {gap if missed}

--- React/TypeScript additional items (STACK=react only) ---

  [x/] Every page/route in the router appears in CLAUDE.md Section 4 (route catalog)
       {gap if missed}

  [x/] Every API call in the codebase (R2) appears in CLAUDE.md Section 5 (API surface)
       Verify each path resolves to a documented backend endpoint
       {gap if missed}

  [x/] No hardcoded API base URLs — all backend calls go through the configured http client
       or use environment variables; grep for "localhost", "8080", "8081" etc. in src/
       {gap if missed}

  [x/] TypeScript `any`: Tech Debt states the production count from R6 (matching the scan) and the files with the
       most occurrences (up to 10). A count above zero is debt to record, not a FAIL
       {gap if missed}

  [x/] console.log / console.warn: Tech Debt states the number of production files from R10 (matching the scan) and
       up to 10 of them. Their presence is debt to record, not a FAIL
       {gap if missed}

  [x/] All environment variables (R5) are documented in CLAUDE.md Section 7
       and a .env.example exists or defaults are documented
       {gap if missed}

  [x/] Auth token storage is documented as found (memory / sessionStorage / cookie / localStorage); if localStorage,
       it is recorded under Compliance Notes with file:line
       {gap if missed}

  [x/] Route guards: protected routes enforce role — check that UI-level role gates
       match what the backend enforces (no role shown in UI that backend rejects)
       {gap if missed}
```

Store all critic findings in `critic_findings`. These become mandatory constraints
for BA + Arch on every subsequent attempt.

---

### Step E — Cross-Consistency Checklist (every attempt)

Run by the **same isolated critic call as Step D** (rubric `onboard critic + cross-consistency`). The drafting agent does not mark these items.

```
CROSS-CONSISTENCY CHECK — {service-name} — Attempt {attempt}

  [x/] Every business rule in Confluence has a technical mapping in CLAUDE.md
       {gap if missed}

  [x/] Every endpoint in CLAUDE.md Section 7 has a corresponding entry in Confluence Section 2
       {gap if missed}

  [x/] Terminology consistent — same concept uses same name in both docs
       {gap if missed}

  [x/] State transitions (if any) described identically in both docs
       {gap if missed}

  [x/] Error cases in Confluence match error handling in CLAUDE.md
       {gap if missed}

  [x/] Kafka payload fields described consistently in both docs
       {gap if missed}

  [x/] Downstream dependencies listed identically in both docs
       {gap if missed}

  [x/] "Must Never" constraints appear in both docs
       {gap if missed}

  [x/] Critic findings (if any) are addressed or explicitly accepted with rationale
       {gap if missed}

  [x/] DB schema in CLAUDE.md reflects the migrations (tables, and changes that alter meaning) — N/A without a database
       {gap if missed}
```

---

### Step F — Decision

Collect gaps from the Stage 2 benchmark and Steps D and E:
```
attempt_gaps = [BENCH:* FAIL checks] + [all items marked GAP from Critic + Checklist]
```
**PASS condition:** `attempt_gaps` is empty **and** the Stage 2 benchmark verdict is PASS.

Print scorecard:
```
ONBOARD SCORECARD — {service-name} — Attempt {attempt}
  Stage 2 benchmark: {PASS | FAIL — n checks}
  Critic: {n}/12 passed (Java) | {n}/20 passed (React)
  Cross-consistency (critic): {n}/10 passed
  VERDICT: {ALL PASSED | GAPS — {n} items}
```

**If ALL PASSED:**
- Set `loop_passed = true`
- Exit loop → proceed to Phase 1 (Write Guard + commit outputs)

**If GAPS and attempt < max_attempts:**
- **Feedback loop** (see *Three stages*): write the failing checks and findings to the feedback file and run Stage 1 again (the originator fixes them and writes its fix log), then re-run Stage 2 and a fresh Stage 3 judge with `PRIOR_FINDINGS`
- Append `attempt_gaps` to `all_gaps`
- Increment `attempt`
- Return to LOOP start (Step A)
- Note: the critic RE-RUNS on the revised drafts (fresh context). It receives the prior `critic_findings` only to verify each is resolved — never the drafting agent's reasoning or attempt history.

**If GAPS and attempt = max_attempts:**
- Go to Escalation

---

## Phase 1 — Write Outputs (reached only on PASS)

**Output path** (`TARGET`): the unit's CLAUDE.md — `$DIR/CLAUDE.md`, or `src/CLAUDE.md` when `DIR` is `.`.
Never the root CLAUDE.md: that is the master file (Phase 2).

Write exactly the draft that passed Stage 2 and the critic, merged into `TARGET` (never re-generated, never overwrite):
```bash
python3 "$G/bench/claude_merge.py" --target "$TARGET" --block onboard --from .plumbline/run/review/{service-name}-CLAUDE.md \
  --title "Service reference — {service-name}"            # prints the diff; nothing is written yet
```

**Always apply Write Guard before writing — whether the file is new or already exists:**
```
ONBOARD ACTION — AWAITING YOUR APPROVAL
  Target : {TARGET}
  Action : {create new file | add the onboarding block | replace the onboarding block} — every other line is kept
  Diff   : {the claude_merge diff; for a long diff, its summary line and the changed headings}
  Evidence: discovery scan of {DIR}/src/, benchmark PASS, critic PASS

Proceed? (yes / no)
```
Do NOT write until the user types "yes". On yes, run the same command with `--write`. Never silently create or change
any CLAUDE.md, and never remove a line outside the `onboard` block.

**Steps:**
1. Apply Write Guard → on approval write the output file on branch `docs/onboard-{service}` commit, and raise a PR (GitHub Write Guard for push and PR). CLAUDE.md is a protected path: the PR passes the guardrails check only after the service tech lead adds the `plumbline-policy-change` label and approves it as CODEOWNER
2. Apply JIRA Write Guard, then create/update the Confluence page under space `BD-POC`
3. Post JIRA comment (informational — comments need no approval under the Plumbline write policy):
   ```
   Brownfield onboarding complete.
   Confluence: {page URL}
   CLAUDE.md: {TARGET} committed on branch {branch}
   Eval loop: {attempt}/{max_attempts} attempts
   ```
4. Apply JIRA Write Guard, then add label `plumbline-onboard-approved`

---

## Phase 2 — Root CLAUDE.md (master) Sync

The root CLAUDE.md is the master file: the solution and its architecture. Keep everything people wrote there; the
generated part is the `solution` block.

**If the root CLAUDE.md already defines the solution** (a service/unit table, the topics, the cache strategy), check drift for this unit only:
- Unit row: port, "owns" (unit CLAUDE.md purpose) and "must never" match the unit's CLAUDE.md.
- Kafka topics this unit produces/consumes are in the topic table, with correct producer/consumer; nothing stale.
- Redis keys this unit owns are in the cache table, with TTL and invalidation; nothing stale.
Print the drift report (MATCH / DRIFT / MISSING / STALE per section) and patch each drift item through the Write Guard.

**Otherwise** (no solution description yet — e.g. the root file is a runbook) write a master `solution` block **once**
(in `service:all`, after all units) with:
1. **Solution** — what the system is for, in one paragraph (from the units' purposes).
2. **Architecture** — a table of units: name, path, kind, stack, port, link to its CLAUDE.md; how they connect
   (frontend → backend REST, service → service REST, Kafka topics, shared databases) from the dependency map
   (`python3 "$G/impact/depmap.py" .`); external systems (e.g. Salesforce, SSO).
3. **Shared rules and known cross-cutting findings** (security findings, unmatched calls) with links to the unit files.
```bash
python3 "$G/bench/claude_merge.py" --target CLAUDE.md --block solution --from .plumbline/run/review/solution-CLAUDE.md \
  --title "Solution and architecture"                     # diff for the Write Guard; --write after "yes"
```
Never remove or rewrite what is outside the block (runbooks, conventions, human notes).

---

## Phase 3 — Summary to User

```
ONBOARD EVAL LOOP — COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service        : {name} (port {port})
Eval Loop      : {attempt}/{max_attempts} attempts

Outputs
  Confluence   : {page title} — {URL or "pending approval"}
  CLAUDE.md    : services/{name}/CLAUDE.md
  JIRA label   : plumbline-onboard-approved

Root CLAUDE.md Sync
  Section 3    : {MATCH | {n} patches applied}
  Section 7    : {MATCH | {n} patches applied}
  Section 8    : {MATCH | {n} patches applied}

Critic Findings Resolved
  {numbered list — or "None"}

Gaps Carried to Retries
  {numbered list — or "None"}

Known Tech Debt Documented
  {list — or "None"}

Next Step
  Run /plumbline-ba {{JIRA_KEY}}-{n} to begin story decomposition now that the service is documented.

Execution time : {elapsed}
```

---

## service:all mode — Full Onboarding for All Modules + Global Consistency Check

Triggered when called as `/plumbline-onboard service:all`.

### Step 0 — Auto-Discover All Modules

```bash
python3 "${PLUMBLINE_HOME:-.plumbline}/impact/layout.py" .
```
`MODULE_LIST` is every unit this prints, backends and frontends: `services/<name>/`, top-level modules, **an app at the
repository root** (path `.`) and frontends such as `ui/`. These are exactly the units the benchmark, scope check and gates
can check. If a module you expect is missing, STOP and show the list: a human declares it in
`.plumbline/project.yaml`. Onboard backends before the frontends that call them, so the frontend's API section can be
checked against a documented backend.

**Polyrepo note:** `service:all` only works within a single git repository root. For polyrepo
architectures (each service in its own repo), run `/plumbline-onboard service:{name}` from
within each repo root instead.

If `MODULE_LIST` is empty, stop and report to user.

Print discovery summary:
```
service:all — discovered {n} modules: {comma-separated list}
Will run per-module onboarding eval loop for each, then global consistency check.
```

### Step 1 — Per-Module Onboarding Loop

For each module in `MODULE_LIST`:
- Run the full eval loop (Phase 0 → Discovery → Stage 1 originator (Steps B–C) → Stage 2 benchmark → Step D Critic →
  Step E Cross-Consistency → Step F Decision) exactly as if called with `service:{name}`
- On pass: Phase 1 for that module — merge into its own CLAUDE.md (`{module}/CLAUDE.md`, or `src/CLAUDE.md` for an
  app at the root) with `claude_merge.py`, Write Guard with the diff, write only after "yes". Never overwrite.
- On user "no": skip writing for this module, record as SKIPPED, continue to next
- On escalation (3 attempts failed): record module name in `ESCALATED_MODULES`, continue to next module — do NOT stop the entire run
- Print per-module status line after each:
  ```
  [{i}/{n}] {module} — PASS + WRITTEN | PASS + SKIPPED (user declined) | ESCALATED
  ```

### Step 2 — Build Kafka Consistency Matrix

Runs after all per-module loops complete. No JIRA writes. No `.onboard.md` files.

```bash
# All topics produced (across all services)
grep -r "kafkaTemplate.send" services/*/src/main --include="*.java" -h \
  | grep -oE '"[a-z.A-Z]+"' | sort -u

# All topics consumed (across all services)
grep -r "@KafkaListener" services/*/src/main --include="*.java" -A3 \
  | grep "topics" | grep -oE '"[a-z.A-Z]+"' | sort -u

# Consumer group IDs
grep -r "groupId" services/*/src/main --include="*.java" -h \
  | grep -oE '"[a-z-.]+-group"' | sort -u
```

Produce this matrix (the rows are an illustration from an order-management system — list this repository's topics):

```
KAFKA CONSISTENCY MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Topic                      | Producer        | Consumers (from code)              | Root §7 match
order.state.changed        | order-service   | audit, client, notification        | MATCH / GAP
risk.evaluation.requested  | order-service   | risk-service                       | MATCH / GAP
risk.evaluation.result     | risk-service    | order-service, notification        | MATCH / GAP
order.execution.requested  | order-service   | execution-service                  | MATCH / GAP
execution.completed        | execution-service | order, client, audit, notification | MATCH / GAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Orphan check:
  Produced but no consumer found : {list or "None"}
  Consumed but no producer found : {list or "None"}
  Consumer group ID violates naming convention: {list or "None"}
```

### Step 3 — Build OpenAPI Consistency Matrix

```bash
# Find all openapi.yaml files and extract paths
find services -name "openapi.yaml" | while read f; do
  svc=$(echo $f | cut -d/ -f2)
  echo "=== $svc ===" && grep -E "^  /" "$f" | sort
done

# Controller endpoints for comparison
grep -r "@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping\|@RequestMapping" \
  services/*/src/main --include="*.java" -h | sort -u
```

Produce this matrix:

```
OPENAPI CONSISTENCY MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service            | In Code | In openapi.yaml | Verdict
{service-name}     | {n}     | {n}             | MATCH / {n} gaps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Gaps (in code but not in spec):
  {service} : {path}

Gaps (in spec but not in code):
  {service} : {path}
```

### Step 4 — Frontend Route Coverage

```bash
# All /api/v1 paths called by the frontend
grep -r "api/v1" frontend/src --include="*.ts" --include="*.tsx" -h 2>/dev/null \
  | grep -oE "/api/v1/[a-zA-Z0-9/_-]+" | sort -u
```

Cross-reference each frontend path against the service CLAUDE.md route tables (example row shown).

```
FRONTEND ROUTE COVERAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frontend path                  | Service        | In CLAUDE.md
/api/v1/orders                 | order-service  | MATCH / GAP
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Undocumented routes (in frontend, not in any CLAUDE.md) : {list or "None"}
Dead routes (in CLAUDE.md, never called by frontend)    : {list — expected for ops-only routes}
```

### Step 5 — Global Summary

```
service:all — COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Per-Module Onboarding
  Total modules   : {n}
  WRITTEN         : {n} — CLAUDE.md written (user approved)
  SKIPPED         : {n} — eval passed but user declined write
  ESCALATED       : {n} — {list of module names, or "None"}

Kafka matrix     : {n} topics — {n} gaps / orphans
OpenAPI matrix   : {n} services — {n} gaps
Frontend routes  : {n} paths — {n} undocumented

Action items (if any):
  {numbered list of specific gaps with service + path + recommended fix}
  or "None — all checks passed"
```

---

## Escalation — reached when gaps persist after 3 attempts

```
ONBOARD EVAL LOOP — ESCALATION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service: {name}
The onboarding documents could not be made consistent after {max_attempts} attempts.
Human review is required.

Persistent gaps:
{numbered list of all_gaps with specific reason}

Critic findings not resolved:
{list}

Recommended action:
1. Review the persistent gaps above manually
2. Update the service code or root CLAUDE.md as needed
3. Re-run /plumbline-onboard after the underlying issue is resolved

Do NOT apply plumbline-onboard-approved label. Post this escalation as a JIRA comment.
```

Post the escalation as a JIRA comment (informational — no approval needed).

---

## Hard Stops — always pause and ask the user

Onboarding **documents what exists**. It stops only when it cannot document honestly:
- `impact/layout.py` does not list the unit (the benchmark cannot check it) — show the list; a human edits `project.yaml`
- Stack detection returns STACK=unknown — do not guess; ask the user to confirm the tech stack
- The unit has no source code (skeleton only — nothing to onboard)

## Findings — record them, do not stop

These are problems in the code, not reasons to stop. Put each in the unit's CLAUDE.md (**Known Tech Debt**, and
**Compliance Notes** for security items) with file:line evidence, list them in the Phase 2 summary and the PR body, and
continue. Never fix code during onboarding; a fix is a separate story (PM → Dev loops).
- Auth or session token stored in `localStorage` (JWT, an MSAL/OIDC cache with `cacheLocation: localStorage`, etc.):
  **security** — readable by any script in the page (XSS). Record the setting and file:line; recommend memory or
  `sessionStorage` (MSAL `BrowserCacheLocation.SessionStorage`/`MemoryStorage`) or an httpOnly cookie.
- Frontend calls a backend path that no endpoint serves (the benchmark lists them): record each call with file:line as
  "no matching endpoint" — never invent what it does.
- No API base URL configured (env, proxy, `environment*.ts`): record how the frontend reaches the backend, or that it can't.
- Backend reads another unit's schema, or uses WebFlux/Reactor where the root CLAUDE.md forbids it: record as a
  rulebook violation.
- The unit is not described in the root CLAUDE.md: record it; the root sync step (Write Guard) proposes the addition.
