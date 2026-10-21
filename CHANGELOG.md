# Changelog

## 1.10.1 — 2026-10-21

- **Install from the repository:** `git clone https://github.com/umeshkumarkv/plumbline ~/plumbline`, then
  `~/plumbline/install.sh` inside any project. Fresh install or upgrade (including from `.agentic-sdlc/`) is detected;
  init.py flags pass through. No tarball needed.
- **Fix: `init.py` could hang** on `semgrep --version` (Semgrep's online update check). Tool probes now time out (60 s),
  the update check and metrics are off, and every subprocess has a timeout.
- **Fix: upgrade kept the shipped broker-dealer baseline** in a non-broker-dealer repository (e.g. migrating from
  `.agentic-sdlc/` 1.8), so `--check` failed. Upgrade now rebuilds only that shipped baseline; a repository's own
  baseline is kept.
- README: Quickstart is three commands.

## 1.10.0 — 2026-10-21

### One folder in the project: `.plumbline/`
- **Everything Plumbline owns is in `.plumbline/`:** the framework (was `.agentic-sdlc/`), `project.yaml`, the gate
  baseline, and the loop working files in `.plumbline/run/` (were `.plumbline/review|work` at the root), ignored by
  `.plumbline/.gitignore`. The root `.gitignore` is no longer touched. Override variable: `PLUMBLINE_HOME`.
- **Entry files are all `plumbline-*`:** commands `/plumbline-onboard`, `/plumbline-pm`, `/plumbline-ba`,
  `/plumbline-arch`, `/plumbline-dev`, `/plumbline-code-review`, `/plumbline-qa`, `/plumbline-doc`, `/plumbline-devops`,
  `/plumbline-sm`, `/plumbline-jira-ping` (were `/<role>-eval-loop`); agents `plumbline-*`; workflows
  `plumbline-guardrails.yml`, `plumbline-critic.yml`, `plumbline-impact-cache.yml`.
- **CI is opt-in:** `init.py --ci` installs the workflows; plain `init.py` leaves `.github/workflows` alone.
- **`init.py --uninstall [--yes]`** lists, then removes, every Plumbline file; the project's CLAUDE.md files stay.
- **Migration from 1.9** (`init.py --upgrade`): moves `project.yaml` and the baseline from `.agentic-sdlc/`, keeps the
  loop drafts (`run/`), removes `.agentic-sdlc/`, takes the `.plumbline/` line out of the root `.gitignore`, and lists
  old entry files to `git rm`. Bootstrap: `tar -xzf plumbline-<v>.tar.gz .plumbline/init.py` then `--upgrade`.
- **CLAUDE.md markers** are `<!-- plumbline:begin|end <id> -->`; `claude_merge.py` adopts and renames the older ones.
- **Fixes found in this pass:** the critic workflow deleted the base framework it had just unpacked
  (`rm -rf .plumbline` → `rm -rf .plumbline/run`); the scope check's framework hash now excludes `run/`; a nested
  f-string in `claude_merge.py` that Python 3.10 cannot parse.
- `selftest/init_selftest.py` 23/23 (adds footprint, `--ci`, `--uninstall`, 1.9 migration).

## 1.9.0 — 2026-10-21

### Plumbline: its own repository, one-step install
- **Name:** the framework is Plumbline (`umeshkumarkv/plumbline`). Agents are `plumbline-<role>-originator` and
  `plumbline-critic`; labels `plumbline-*`; loop working files in `.plumbline/`; spec sources in `loops/`; the
  folder in each repository stays `.agentic-sdlc/` (`AGENTIC_SDLC`). Existing JIRA labels with the previous prefix, the demo login
  variables and old generated files need a one-time rename where they are already in use.
- **`init.py`** (shipped as `.agentic-sdlc/init.py`): detects units, Java version (also from a parent pom), frontend
  framework and base branch; writes `project.yaml` (never overwrites it); installs the generated agent files and
  workflows; writes this repository's gate baseline; checks prerequisites (python3, PyYAML, Semgrep, JDK, node, CRLF or
  non-executable `mvnw`); prints a doctor report (units, endpoints, API calls, unresolved calls, calls with no endpoint,
  CLAUDE.md locations, gates). `--doctor`, `--check` (CI: stale generated files, undeclared units, missing or foreign
  baseline), `--upgrade <tarball>` (keeps project.yaml and the baseline), `--domain none|broker-dealer`.
- **Gates per project:** `project.yaml` `gates: {semgrep: [...], checks: [...]}`, read from the trusted copy (in CI the
  base branch's), never the pull request's; units for the gates come from the same trusted file. Semgrep rules split:
  `java-generic.yml` (15 rules: money arithmetic, BigDecimal, legacy dates, field injection, controller → repository,
  secrets in logs/code/config, SQL concatenation, stack traces, System.out) for any Spring project, and `oms-rules.yml`
  (14 broker-dealer conventions). Without a `gates:` section every pack runs (broker-dealer: 26 findings, 0 NEW, unchanged).
- **Dependency map:** records frontend calls whose URL cannot be resolved (for the doctor); cache version 8.
- **Base branch** comes from `project.yaml` (`base_branch`).
- **Self-tests:** `selftest/init_selftest.py` 15/15 on a fixture shaped like candidate-review-system; all others pass.

## 1.8.0 — 2026-10-21

### CLAUDE.md pattern: one master file at the root, one file per unit — merged, never overwritten
- **Root `CLAUDE.md` is the master file:** the whole solution and its architecture, plus whatever people keep there
  (runbooks, conventions). **Each unit has its own CLAUDE.md:** `services/<name>/`, `<module>/`, `ui/`, and
  **`src/CLAUDE.md` for an app at the repository root** (was: the root file, which made onboarding offer to overwrite
  candidate-review-system's local-development runbook).
- **New `bench/claude_merge.py`** (deterministic): generated content lives between
  `<!-- agentic-sdlc:begin <id> -->` / `end` markers (`onboard` in unit files, `solution` in the root). It replaces only
  its block or appends it, keeps every other line, prints the diff for the Write Guard, writes only with `--write`, and
  refuses unbalanced markers.
- **Onboard Phase 1** merges the approved draft into the unit's CLAUDE.md with the diff in the Write Guard.
  **Phase 2** checks drift when the root already describes the solution (broker-dealer), and otherwise writes a master
  `solution` block once (solution, architecture table with links to every unit's CLAUDE.md, how units connect, shared
  findings). **Doc loop** edits only affected rows of the unit's CLAUDE.md.
- Scope check and benchmark use the new locations (`layout.claude_md()`, `Repo.claude_md()`).
- `selftest/layout_selftest.py` 28/28 (adds CLAUDE.md locations and claude_merge behaviour).

## 1.7.2 — 2026-10-21

- **Every run starts at attempt 1.** The third candidate-review-system run read "attempt 3/3" from the previous run's
  brief and escalated without trying. Earlier `.plumbline/work/<name>/` is now archived to `previous-<timestamp>/`, existing
  drafts are attempt 1's starting point, and the last run's open findings seed attempt 1's feedback.

## 1.7.1 — 2026-10-21

### From the second candidate-review-system run (both units escalated after 3 attempts; no output published)
- **Scope check works on macOS and cannot be mistyped:** `snapshot --role R` prints a one-line `CHECK:` command that
  verifies the sha with Python (no `sha256sum`/`shasum` difference) and runs the private checker. The hand-off copies
  that line as printed; the run had retyped the 64-char sha wrong once.
- **Per-file class fields:** `${this.baseUrl}/…` resolves with the field of the same file (each Angular service has its
  own `baseUrl`), including fields built from constants. The run's false positive (`/api/opt/reference/admin/{table}`
  reported as invented) is gone; unmatched UI calls on that repo: 13, all marked.
- **Domain pack per project:** the judge applies the pack named in `.agentic-sdlc/project.yaml` (`domain_pack:`), or
  none; the broker-dealer pack is used only when there is no project.yaml.

## 1.7.0 — 2026-10-21

### From the first full onboarding run on candidate-review-system (Spring root app + Angular `ui/`)
- **Frontend units get an onboarding benchmark** (was: `--service ui` exited "not found"): OBF-1 sections, OBF-2 every
  backend path the code calls is in the API Surface, OBF-3 nothing documented that the code never calls, OBF-4 calls no
  endpoint serves are marked `no matching endpoint` (WARN), OBF-5 token storage in `localStorage` is recorded under
  Compliance Notes.
- **Commented-out code is not code:** the dependency map blanks Java comments before reading mappings. The run's critic
  caught 10 commented legacy routes documented as active; the benchmark now catches them (OB-5) before the critic.
- **Angular/TS call resolution:** calls built from constants (`${API_BASE_URL}${OPT_ENDPOINTS.X}/${id}`, nested
  constants, class-field bases, `const url = ...; http.get(url)`, `post<Record<a, b>>(`) are resolved; base constants
  are no longer counted as calls; a call whose prefix cannot be resolved is skipped rather than guessed. On that repo:
  111 → 180 call sites read, unmatched calls 21 → 16 (all real: e.g. `/api/opt/create`, `/api/training/*`).
- **Tables:** "invented table" now checks against every table the repo defines (Flyway, any `.sql` script, JPA
  `@Table`), and English words are no longer read as table names (the run hit `was`).
- **OB-13 (WARN):** with a single backend, frontend calls no endpoint serves are listed as tech debt, not catalogued.
- Template header no longer says "Part of Broker Dealer OMS POC".

## 1.6.4 — 2026-10-21

- **Onboarding documents what exists; it does not stop on findings.** Hard stops are now only: the unit is unknown to
  `layout.py`, the stack is unknown, or there is no source. Token storage in `localStorage` (JWT, MSAL/OIDC cache),
  frontend calls with no matching endpoint, a missing API base URL, cross-schema reads, WebFlux, and a unit missing from
  the root CLAUDE.md are recorded as findings (Known Tech Debt / Compliance Notes, with file:line, in the summary and PR
  body) and onboarding continues. Fixes are separate stories.
- Found on candidate-review-system: `ui/src/app/msal.config.ts:49` keeps the MSAL token cache in `localStorage`.

## 1.6.3 — 2026-10-21

- **JDK pre-flight follows the repository**, not broker-dealer's JDK 21: the JDK must match the Java version the build
  declares (pom.xml `java.version` / `maven.compiler.release`, or the Gradle toolchain); a newer JDK is accepted only if
  the project compiles with it. Onboarding no longer stops for the JDK: it only needs it for the optional coverage scan.
- Onboard discovery template no longer hard-codes "Java 21 / Spring Boot 3.2".

## 1.6.2 — 2026-10-21

### Found on candidate-review-system (Spring Boot app at the root + Angular `ui/`)
- **`service:all` discovers units with `impact/layout.py`** (was: its own find commands, which missed the root app and
  listed only `ui`). Backends are onboarded before the frontends that call them.
- **Angular:** onboarding treats any TypeScript SPA under the React profile and adds Angular variants of the scans
  (routes, `HttpClient` calls, `environment*.ts`, `angular.json` port). The dependency map already reads Angular calls
  (111 found in `ui/`).
- **Dependency map:** reads `application*.properties` as well as YAML; a Spring Boot app with no `server.port` gets the
  default 8080.
- Measured on that repo: root app with 145 endpoints, `ui/` with 111 API calls, 21 calls with no matching endpoint.

## 1.6.1 — 2026-10-21

### Security fixes from the independent review of 1.6.0
- **`project.yaml` is validated:** unit names must match `[A-Za-z0-9][\w.-]*`, paths must be relative without `..`,
  no duplicates, no collision with an existing `services/<name>/`. The gates' scan copy fails closed if any file would
  land outside it (a crafted name could otherwise write files outside the copy and hide code from Semgrep).
- **Gradle and build wrappers:** agents may not change `build.gradle(.kts)`, `settings.gradle(.kts)`,
  `gradle.properties`, `gradle/wrapper/*`, `.mvn/`, `mvnw*` or `gradlew*` (only `pom.xml` has a guarded-parts check).
  The wrappers are protected paths. `pom.xml` guarded parts now include `build-helper-maven-plugin` and
  `sourceDirectory`/`testSourceDirectory` (compiled code outside `src/` that no gate scans).
- **Known limit:** CI protected-paths does not yet guard Gradle build files, so a human PR could disable Gradle tests
  without CI flagging it. Agents are stopped by the scope check.
- `selftest/layout_selftest.py` 22/22.

## 1.6.0 — 2026-10-21

### Any repository layout, not only `services/<name>/`
- **`impact/layout.py`** is the one place every check asks where the units are. Detected: `services/<name>/`, top-level
  modules (`pom.xml`/`build.gradle` + `src/main/`), **a single app at the repository root** (path `.`, owning `src/`,
  the build files and the root `CLAUDE.md`), and frontends (top-level folders with `package.json`, e.g. `ui/`).
  Anything else is declared in `.agentic-sdlc/project.yaml` (example shipped; a protected, human-edited file).
- **Dependency map:** builds the root app (working tree and git ref) with only the files it owns.
- **Benchmark:** onboard, doc, arch and dev use each unit's real directory (`Repo.dir()`); Dev finds changed units
  through the layout, including new files.
- **Scope check:** the code paths Dev/DevOps may write, QA's test folders and Doc's files come from the layout and are
  stored in the integrity-checked snapshot.
- **Gates:** for a non-standard layout they scan a view where each backend sits at `services/<name>/` and report findings
  at their real paths (fingerprints and baselines use the real paths). Broker-dealer is unchanged: 26 findings, 0 NEW.
- **Specs:** every loop reads `services/{service}/` as the unit's path from `layout.py`; Onboard Step 0 picks the unit
  from it and stops with the list if the unit is unknown.
- **Self-test:** `selftest/layout_selftest.py` 16/16 (root app + `ui/`: layout, depmap, onboard benchmark, dev pack,
  scope check, gates, project.yaml), in CI.

## 1.5.0 — 2026-10-21

### One folder to copy: `.agentic-sdlc/` is committed in the repository
- **Name:** the folder is `.agentic-sdlc/` and its override variable is `AGENTIC_SDLC` (were `.guardrails/` and
  `PLUMBLINE_GUARDRAILS`). The old name stays a protected path.
- **`python3 tools/make_kit.py`** builds `build/kit/.agentic-sdlc/`: the specs, generated agents/commands/prompts,
  benchmark, scope check, gates, impact map, packs, self-tests, `requirements.txt`, `VERSION`, a README and
  **`install.sh`**. The install script copies the generated files to `.claude/` and `.github/` (the only paths the tools
  fix), installs the 3 workflows and adds `.plumbline/` to `.gitignore`. Team members copy the folder and run it.
- **No separate repository needed:** the CI templates no longer check out `plumbline` repository. `guardrails.yml` checks out
  the **base branch** and runs its `.agentic-sdlc/`; `plumbline-critic.yml` extracts the base branch's `.agentic-sdlc/` with
  `git archive`; `impact-cache.yml` (merged code only) uses the committed copy. A PR still cannot change its own checker:
  `.agentic-sdlc/` is a protected path, and the copy that judges it is the base branch's.
- **`requirements.txt`:** the whole Python footprint — python3 ≥ 3.10, `pyyaml==6.0.2`, `semgrep==1.180.0` (gates only).
- **Verified:** all four self-tests pass from inside the kit; gates on broker-dealer with the kit committed: 26 findings,
  26 baseline, 0 NEW (the scanners do not read `.agentic-sdlc/`).
- **Not yet generic:** the Semgrep rules, domain pack, baseline and ArchUnit test are broker-dealer's; specs assume
  Java/Spring + React + Kafka + Postgres + JIRA. Splitting core / stack profile / domain pack is planned.

## 1.4.0 — 2026-10-19

### Copilot gets the same isolated agents as Claude Code
- **Ten Copilot custom agents** in `.github/agents/`: `plumbline-<role>-originator.agent.md` for the nine loops and `plumbline-critic.agent.md`. All are `user-invocable: false` (only the loops call them) and least-privilege: `read/readFile`, `search`, `edit`; `execute/runInTerminal` only for Dev, QA and DevOps; the critic gets `read/readFile` and `search` only. No web, browser, GitHub or nested-agent tools.
- **Copilot prompts are orchestrators too.** Stage 1 is the same hand-off as Claude Code (inputs as files, brief, feedback file, sha-checked scope check) and calls the originator with `#agent/runSubagent`. The originator's work is no longer done inline: if subagents are unavailable the loop stops.
- **The Copilot judge is the `plumbline-critic` subagent** (clean context, read-only). The new-chat `/plumbline-critic` prompt stays as a fallback; a review in the same chat is still labelled self-attested.
- **Known limit removed:** the Copilot scope check now has the same strength as Claude Code's, because the orchestrator holds the sha and the originator runs in its own context.
- **Requires** a VS Code with custom agents as subagents and the Run Subagent tool (`agent/runSubagent`) enabled.
- **Repository:** the CI templates check out `umeshkumarkv/plumbline` (public; was `umeshkvguptha/…`, which did not exist).
- **Prompt frontmatter** uses `agent: agent` (was `mode: agent`).
- **Self-test:** `agents_selftest.py` 62/62 (adds Copilot agent least-privilege and hand-off checks). CI templates pinned to `v1.4.0`.

## 1.3.0 — 2026-10-19

### Commands are orchestrators; the originator is an isolated agent per role
- **Nine originator subagents:** `plumbline-{pm,ba,arch,dev,qa,devops,doc,sm,onboard}-originator`. Each starts with a clean context every attempt. It gets a brief file, its input files, the rulebook and, from attempt 2, the feedback file. It never sees the orchestrator's reasoning.
- **Least-privilege tools:**
  - PM, BA, Arch and Doc: `Read, Grep, Glob, Write, Edit`. SM and Onboard: `Read, Grep, Glob, Write`.
  - Dev and DevOps: the same five plus `Bash`. QA: `Read, Grep, Glob, Write, Bash` (local stack only).
  - None of them gets MCP, web, Agent, `gh`, `git commit` or `git push`.
- **The orchestrator (the command)** owns all of this:
  - preconditions and fetching JIRA, GitHub and CI data into files;
  - the brief, and the call to the originator;
  - the scope check, the benchmark, and the call to the judge;
  - feedback routing, the attempt counter and escalation;
  - the human approval gate and every external write.
- **External calls moved out of Stage 1:**
  - SM's facts, including PR and review status, are fetched in Phase 0.
  - DevOps CI logs are saved to a file, and commit/push moved to a new orchestrator step C2.
  - The Arch and QA story files are saved by the orchestrator. The Onboard Confluence draft is a file the orchestrator publishes.
- **New `bench/scope_check.py`** (deterministic). Before the originator runs it snapshots tracked, untracked and gitignored files (build output excepted), everything under `.plumbline/`, every git ref, skip-worktree/assume-unchanged flags, and a hash of the whole guardrails checkout. The snapshot and a private copy of the checker are stored **outside** the repository; the snapshot is checked by its SHA-256, so the originator can neither rewrite it nor edit the checker. Afterwards:
  - every changed path must be inside the role's allowed paths; protected control files are denied except to Doc's CLAUDE.md job;
  - inside `.plumbline/` only the artifact (`--writable`) and the fix log may change: input files (story, facts, CI log, discovery, brief, feedback) are read-only;
  - a commit or a new branch fails; so do a new skip-worktree flag, any edit to the guardrails checkout, and any change to the test/coverage parts of a `pom.xml` (surefire, failsafe, JaCoCo, skipTests);
  - pre-existing uncommitted work is not blamed. Each violation becomes a `SCOPE:` feedback item and fails the attempt.
- **Working files** (brief, feedback, fix log) live in `.plumbline/work/<name>/`. The orchestrator writes the feedback file from the failing items; the judge is told never to read `.plumbline/work/`.
- **Evidence the originator cannot forge:** Dev's orchestrator runs `mvn clean verify` on the changed services itself before the benchmark, so no report, `jacoco.exec` or compiled class from the originator survives. SM's Phase 1 posts the judged report verbatim. Onboard's Phase 0 saves the discovery report, Dev's saves the story and approved design, QA's saves a test plan (AC classification, URLs, Postgres/Kafka availability, login env var names, never values).
- **DevOps:** the originator applies an approved suggest-fix (never a workflow file); the orchestrator commits and pushes to the feature branch only, before Stage 2, because the evidence is a CI run.
- **Known limit (Copilot):** Stage 1 runs in the same chat, so its scope check catches mistakes, not a determined originator; the CI gates remain the hard control.
- **Loop names are unique per role** (`{ticket}-pm`, `{ticket}-arch`, `{ticket}-dev`, …), so benchmark reports no longer overwrite each other.
- **Build:** `<!-- @originator role=… tools=… artifact=… inputs=… -->` sections in the specs become the Claude agents plus a thin hand-off in each command. Copilot, which has no subagents, keeps Stage 1 inline under the same rules and the same scope check.
- **Self-test:** `selftest/agents_selftest.py` passes 52/52 (25 scope cases, including snapshot and checker-copy tampering, skip-worktree, input edits, gitignored files, skipTests and branches) and runs in CI.
- **Pins:** CI templates now use `v1.3.0`.

## 1.2.1 — 2026-10-19

### Feedback loop made explicit; every loop gets at least 3 attempts
- **`shared/three-stage.md` defines the feedback loop:**
  - The originator receives exactly the failing benchmark checks and the judge's findings (rule, location, fix).
  - It fixes each one and logs it in `{name}-fixlog.md` (fixed, or disputed with evidence).
  - Both stages then re-run in full, with a **fresh** judge that verifies each earlier finding as RESOLVED or STILL PRESENT. The judge never sees the fix log.
- **`max_attempts = 3` in every loop.** PM, BA, Arch, Doc and SM went from 2 to 3; Code Review keeps 3 rounds. Escalation happens only after attempt 3 fails, or at once on a Hard Stop.
- **If attempt 2 repeats attempt 1's failures**, attempt 3 must take a different approach.
- **Escalation report:** per-attempt failures and fixes, items still open, and disputed items with both sides' evidence.
- **"How It Works" diagrams:** every loop's diagram now shows the cycle (originator → benchmark → judge → feedback → re-run), and every retry branch names the feedback step.
- **Decks:**
  - Brownfield slide 11 and Greenfield slide 4 show the feedback lane and the strip Attempt 1 → 2 → 3 → human.
  - Phase-slide subtitles say "findings fixed and re-run, up to 3 attempts, then a human".
  - The Greenfield arch mock-up now shows max 3 attempts.

## 1.2.0 — 2026-10-19

### Every loop is now ORIGINATOR → BENCHMARK → JUDGE
- **New stage 2, `bench/`:** a deterministic benchmark per agent (pm, ba, arch, dev, code-review, qa, devops, sm, doc, onboard). It runs after the agent writes its artifact and before the isolated critic.
  - **On FAIL:** the attempt goes back to the originator and the judge is not called.
  - **On PASS:** the report goes to the judge as facts. The loop passes only if both pass.
- **Mechanical rubric items moved from the LLM to code.** Examples: section presence, AC format, story points, ports, schemas, routes, migration numbering, "the endpoint this design calls exists", the QA evidence format, SM counts recomputed from the JIRA export, and endpoints/topics/tables documented and real.
- **New judge stages where there were none:**
  - QA: rubric `qa evidence`, plus a results file and replay of recorded GETs.
  - DevOps: rubric `devops fix`.
  - SM: rubric `sm report`. The old in-agent completeness check becomes a pre-flight that does not gate.
- **Critic agents** (Claude and Copilot) take `BENCHMARK`. They treat its PASS/FAIL as facts and never mark an item PASS that a FAILed check covers.
- **Specs:** `shared/three-stage.md` defines the protocol. `shared/gates.md` is retired, because gates run inside the dev/code-review benchmark.
- **Self-test:** `selftest/bench_selftest.py` checks good and bad fixtures for all 10 agents, plus attack regressions (15/15). It runs in self-check CI.
- **Independent review**, 2 rounds, ended GREEN.
  - Round 1 found 6 blockers/majors:
    - Decision steps dropped the benchmark gaps.
    - DevOps passed on CI green alone.
    - DOC-2 could not fail.
    - Onboard benchmarked the old file instead of the draft.
    - The code-review worktree had no test run.
    - The QA and onboard benchmarks could be gamed.
  - All are fixed and pinned by self-test cases.
- **On the real OMS** (`bench/RESULTS.md`): 64 doc-drift items in 8 of 9 service CLAUDE.md files (precision 53/54 audited), including a live bug (execution-service calls `GET /market/{symbol}`, which does not exist), plus 29 plaintext credential lines.
- **Pins:** CI templates now use `v1.2.0`.

## 1.1.1 — 2026-10-14

### `impact/` fixes found by a second, independent build of the same idea
- **HTTP verb change is now BREAKING.** Before, `GET /x` → `POST /x` counted the endpoint as still present, so `--fail-on-breaking` passed. A caller's endpoint now survives only if it still accepts the caller's verb.
- **Verb detection reads the whole statement.** `restTemplate.getForObject(base + "/api/..")` had no verb, because the verb comes before the path. It is now detected.
- **Suspect calls.** A call with a runtime segment that lines up only with fixed endpoints (`/market/{symbol}` vs `/market/hours`) is reported as `suspect` instead of `ambiguous`. On the OMS this surfaces a real bug: execution-service calls `/api/v1/market/{symbol}`, which marketdata-service does not serve (the 404 is swallowed).
- **Independent edge check** (`eval/impact/edges/`): a hand-built map of every OMS Kafka, HTTP and schema link, written by an agent that never saw `impact/`.
  - Kafka: 16/16.
  - Service-to-service HTTP: 10/10, counting host:port config links; precision 10/11.
- **No regression:** all 4 scenario sets reproduce their recorded scores exactly, and the self-test passes 12/12. The depmap cache version is now 7, so old cached maps are rebuilt.
- **Pins:** CI templates now use `v1.1.1`.

## 1.1.0 — 2026-10-14

### New: `impact/` — cross-service impact map for large monorepos
- **`depmap.py`:** a deterministic dependency map, no LLM. It covers Kafka, REST, gateway routes, host:port config, JWT issuer→verifier, cross-schema SQL and Maven modules. Contracts are tracked per method, with fingerprints that ignore comments and logging. The cache is keyed by git tree hash, so a PR only re-extracts the services it changes.
- **`impact.py`:** diffs the contracts of base and head, then filters by the keys that changed. Keys cover renamed or removed fields, Map keys, headers, claims and enum values; changes of type or format; `@JsonProperty` names. A unit counts as affected only if it reads a changed key. The output is `impact.json`, `impact.md` for the critic, and `--fail-on-breaking` for CI.
- **Measured** (`eval/impact/RESULTS.md`):
  - Held-out recall went from 77.5% to 66.7% to 95.7% as the tool improved; precision was 82–89%.
  - On 999 synthetic services (3.27M lines), one PR takes 1.5–3.8 s; a cold map takes 40 s.
- **Wired in:**
  - The isolated-critic protocol and both critic agents take `IMPACT`, and a BREAKING item is a blocker.
  - `critic.yml` builds the bundle.
  - `guardrails.yml` fails on BREAKING (from guardrails v1.1.0).
  - `run_gates.py --changed-from` gates only the services a PR changed.
  - The self-test has 8 impact cases, including git mode and the cache.
- **Hardening after independent review:**
  - PR workflows only restore the cache; the new `impact-cache.yml` writes it from merged commits.
  - Units are extracted from stored git blobs whenever attributes exist, which closes a `.gitattributes` re-encoding route to cache poisoning.
  - `.gitattributes` is now protected, and the gates fail closed on non-UTF-8 sources.
  - Services are identified by `spring.application.name`, and file moves are detected, so moving a folder is a no-op.
  - Removing a service reports the routes and URLs still pointing at it.
  - Symlinks are skipped.
  - Workflows are pinned to v1.1.0.
- **Housekeeping:** unreviewed files that appeared in the working folder (`impact/contract_map.py`, `eval/impact/cases.json`, `run-v1/`, `run-v2/`) were moved out and are not part of this release.

## 1.0.0 — 2026-10-13

### Plumbline agent pack: fixes to the original Claude Code + Copilot sets
1. **Code-review round tracking was unreachable.** The counter searched for "Code Review Eval Loop — Round {n}" but comments were posted as "Code Review Eval Loop ({date}): Round …", so it was always Round 1. Now one machine marker, `[plumbline:code-review pr=#N round=R/M verdict=…]`, is used for both writing and counting. It is scoped to the PR, resets after APPROVED or a human `reset` marker, and stops after ESCALATED until a human resets it.
2. **Arch DoR missed the Design Completeness Rule.** The 4 hard-stop items (identity fields, UUID domains, RBAC per role, gateway headers) are now DoR items: 11 → 15.
3. **Onboard contradictions:** a new CLAUDE.md is now always write-guarded; the `service:all` step numbering is fixed (0–5); the critic scorecard denominator is 12 (Java) / 20 (React); the critic re-runs every attempt (previously attempt 1 only).
4. **BA no longer creates Epics** (PM's job, and the creation was unguarded). BA fails fast without a `plumbline-prd-approved` Epic.
5. **One write policy for all agents:** comments are informational; labels, transitions, creates, push, PR create and PR review are always approval-gated.
6. **DevOps supply chain:** `curl … | bash` and the unpinned Veracode `LATEST` are replaced with pinned URLs plus SHA-256 verification (`security/tool-versions.env`).
7. **Drift between the sets removed:** the Claude Code set had stale command names (`/ba-agent`, `/pm-agent`, `/qa-agent`, `/devops-agent`, `/architect-agent`, `/code-review`), a **hard-coded demo login** (`trader.john` / `Demo@1234`), hard-coded `/Users/...` paths and `JAVA_HOME`, a missing JIRA write guard in the legacy `sm-agent` command (the Copilot copy had it), and a security-report template that only referenced another file instead of being written out.
8. `jira-ping` now exists for Claude Code too; `sm-agent` is retired (superseded by `sm-eval-loop`).

### Deferred, not fixed (recorded so nobody assumes otherwise)
- **Scale gap** from the 2026-10-13 review. *Update 1.1.0:* the review side is now covered by `impact/` (PR-scoped context and gates). What remains open: root CLAUDE.md §3/§7/§8 grow with service count, and `service:all` onboarding is sequential with a per-module Write Guard. Decision (2026-10-13, `claude/DECISION-2026-10-13-durable-focus.md` in the project): don't build scale infrastructure that vendors will ship; revisit when a prospect's estate needs it. The Plumbline design is kept as reference only.
- **Audit records** are specified (`packs/governance/audit-record.schema.json`) but not yet written by the loops.

### New
- **Bots never approve PRs.** The code-review verdict is a `plumbline/code-review` status check plus a review comment; CODEOWNERS approve.
- **`gates/checks/protected_paths.py`:** no PR (any branch name) can change workflows, CODEOWNERS, agent prompts, scanner ignore files, lint/ArchUnit config, jacoco/surefire/failsafe configuration, scanner pins or CLAUDE.md without the `plumbline-policy-change` label + CODEOWNERS review (`packs/governance/CODEOWNERS.template`). The workflow runs from the base branch (`pull_request_target`). Gates scan a sanitised copy, so `.semgrepignore`, `.gitignore` and `// nosemgrep` cannot hide code. New structure check C5-java-outside-services flags production Java placed outside `services/` (which the gates would not scan).
- **Round-4 hardening:** Semgrep can no longer skip code silently. Package folders it ignores by default (`vendor`, `build`, `test`, `dist` …) are renamed in the scan copy, the 1 MB size limit is off, and the gate fails closed if Semgrep crashes, returns unparseable output, times out on a file or leaves any production Java/YAML file unscanned; symlinks under `services/` fail the gate. `protected_paths` now also covers `.mvn/` / `maven.config` / `settings.xml`, `CLAUDE*.md`, `.github/copilot-instructions.md`, `.github/instructions/`, `AGENTS.md` and `.plumbline/`, and normalises pom whitespace so a split `<artifactId>` cannot hide a surefire/jacoco change. The CI critic deletes any committed `.plumbline/` before building its rulebook. The CODEOWNERS template is synced with the protected list. C4 now catches injection through any method name, and C8 catches secrets logged through getters, fields or method calls. Findings are de-duplicated to one per rule per line, which takes the baseline from 27 to 26.
- **Self-test extended:** nosemgrep is ignored, setter injection and secret-concatenation logging are caught, a duplicate of a baselined finding is NEW, and 8 `protected_paths` scenarios run on a scratch git repo (dependency bump allowed; coverage/surefire weakening, CLAUDE.md edit, nested `.semgrepignore`, rename of a protected file, workflow edit blocked; labelled policy PR allowed).
- **Onboard cross-consistency** and all quality checklists are marked by the isolated critic. SM (mechanical counts), QA (HTTP/DB/Kafka evidence) and DevOps (CI result) keep in-agent checks by design.
- One canonical spec per agent, with `build.py` emitting both runtimes; CI can run `--check` to block drift.
- Deterministic gates in every code loop before any LLM review.
- An isolated `plumbline-critic` (read-only subagent; Copilot: CI or a new session; same-chat reviews are labelled self-attested) in the dev, code-review, arch, BA, PM, doc and onboard loops.
- Gates, eval harness, domain rule pack, governance pack.
