---
description: Plumbline — document an existing codebase into CLAUDE.md files (one per unit + a master), each checked by an independent judge
argument-hint: "[unit name, or empty for all]"
---

# /pl-onboard

Document this repository for people and AI agents: one CLAUDE.md per unit (backend service, frontend) and one master
CLAUDE.md at the root that describes the whole solution. Each file is written by a **writer** subagent and checked by
an independent **judge** subagent; up to 3 attempts per file, then it is handed to the user.

Target: $ARGUMENTS (empty = every unit)

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-onboard-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with agent `plumbline-onboard-writer` or `plumbline-judge`
  (`.github/agents/`). If subagents are not available in this chat, stop and say so.

Each subagent starts with a clean context. Never do the writer's or the judge's work yourself, and never pass the
writer's reasoning or your own opinion to the judge. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match), `bash .github/plumbline/check-template.sh` commands, and in Step 2b each
unit's own test command, yourself (they work in bash, PowerShell and cmd alike); find and read files with your file search/read tools — never `find`, `grep`, `ls`, `cat`.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue — but only for a path you gave that helper; any other path is a FAIL finding, not a write.

## Every run
- **Judge replies:** only the judge's JSON counts. Not JSON → ask that judge once more, then count the attempt as FAIL
  ("judge reply unreadable"). Never decide PASS yourself or drop a finding before the next attempt.
- **Project memory:** helpers work from the CLAUDE.md files (kept current by `/pl-doc`) and the JIRA/Confluence
  material, opening code only for what they change or review; never research the code yourself. List their "Add to
  CLAUDE.md" / "CLAUDE.md out of date" notes in the hand-over for `/pl-doc`.
- **Freshness:** for each unit CLAUDE.md a helper gets, run `git log --oneline <its Last updated commit>..HEAD --
  <unit folder>`. Commits listed → tell the helpers and the judge "CLAUDE.md may be stale for: <files those commits
  changed>", and say so in the hand-over.
- **Templates and lanes:** what will be posted is written on its template (JIRA hand-off table;
  `.github/plumbline/templates/`). Give each writer the template, the version (`.github/plumbline/VERSION`) and
  `git rev-parse --short HEAD`; tell the judge the writer's agent name, so it checks that agent's *Your lane*. Before
  each judge and before posting run `bash .github/plumbline/check-template.sh <template> <draft>` — it also fails
  text outside the role's lane: FAIL = that attempt's finding, no judge. No bash → the judge checks it instead. Before
  posting, set the footer's `judge` to the result (e.g. `PASS 1/3`).
- **Limits:** at most 3 attempts per item, one writer and one judge each. More than 6 items → show the list and ask;
  nobody to answer → do the first 6 and list the rest.
- **Nobody to answer** (scheduled/headless): where a step says ask, take its safe choice or stop that item — never
  guess; write nothing outside the repository and `.plumbline-drafts/`; list the unasked questions in the hand-over.
- **Hand-over:** first line `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what did not
  run>`; then the details; then each question for the user with the exact text or command it would send or run.

## Metrics
At the hand-over append to `.plumbline-drafts/metrics.csv` (header, if new:
`date,command,target,attempts,verdict,tests_run,minutes,human_decision`): date, command, story/branch/PR, attempts,
verdict, tests ran `yes`/`no`/`n/a`, minutes (`date +%s` at start and at hand-over), and `human_decision` once the user
answers: `approved`, `edited` or `rejected`. It stays local; `/pl-sm metrics` summarises it.
**Files:** create drafts and metrics with your write tool (it creates folders) — never `mkdir`, `echo`, `printf` or
redirection, which permission settings block.

## Step 1 — Settings
Read the root `CLAUDE.md` if it exists. Missing **Plumbline settings** (JIRA project, Confluence space and parent
page, base branch, `Separate approver` — default yes) → ask once (base branch: suggest the default branch).

## Step 2 — Find the units
Use `git ls-files` or your file search tool to find build files: `pom.xml`, `build.gradle`, `build.gradle.kts`, `package.json` (ignore `node_modules`,
`target`, `build`, `dist`), plus other stacks' build files if present. A folder with its own build file and source is a
unit; a parent build file that only lists modules is not. For each unit decide its CLAUDE.md (and, beside it, its
`CLAUDE.reference.md`): a unit in a folder → `<folder>/CLAUDE.md`; an app at the repository root → `src/CLAUDE.md`
(the root `CLAUDE.md` is the master).

Show the user the list (name, folder, kind, CLAUDE.md) in one table and continue.

## Step 2b — Do the tests run here? (one run per unit)
For each unit, take its test command from the build files (`./mvnw test` / `mvnw.cmd test`, `mvn test`,
`./gradlew test`, `npm test -- --watch=false`; the command the README or an existing CLAUDE.md gives wins). Note the
runtime the build files ask for (Java version, Node engines). Run it once from the unit's folder as `cd <folder> && <command>` (not `--prefix` or `-f` flags, which permission
rules do not match), with a 15-minute limit; check the runtime with `java -version` / `node -v`. Keep
only: the exact command, the runtime actually used (`java -version`, `node -v`), the result (`N tests, M failed` or
the first error line), and the duration. Do not change any file to make it pass. If running it needs something you
must not do (install software, network the user has not allowed), do not run it and record why.
The result goes to the writer as the unit's **test recipe**; other commands rely on it, so a failure must be recorded
exactly, never smoothed over.

## Step 3 — Each unit, one at a time (helpers run in the foreground)
For attempt = 1, 2, 3:
1. **Writer** — start `plumbline-onboard-writer` with: the unit name, folder, CLAUDE.md and reference paths, the test recipe
   from Step 2b, the current commit (`git rev-parse --short HEAD`) and today's date for its `Last updated` line, and on attempts 2–3 the judge's findings from the previous attempt (verbatim JSON).
2. **Judge** — start `plumbline-judge` with exactly:
   - *Review:* both paths, the unit folder, and "compare with `git diff -- <both paths>`: text outside the
     plumbline markers must be unchanged";
   - *Checklist:* the **Onboard checklist** below, verbatim.
3. **PASS** → next unit. **FAIL** → next attempt with the findings.

After 3 failed attempts: leave the file as it is, mark the unit **ESCALATED**, keep its last findings for the summary,
and move on.

### Onboard checklist
1. Every endpoint/route the code defines is in the reference API section — search the mapping annotations or route
   definitions, compare the count, check at least 10 at random. None listed that the code does not define.
2. Frontend: every backend call is listed with the endpoint it hits; calls that no backend endpoint serves are listed
   as such, not presented as working. (N/A for a backend.)
3. Every entity/table is in the reference Data section with its key fields; none the code, migrations or SQL scripts
   do not define. Column names are fields, not tables.
4. Integrations: every outbound HTTP call, messaging topic and cache the code uses is listed; nothing invented.
5. Build & run commands, port and configuration match the build and config files. A **Test recipe** line states the
   command, the runtime it needs (from the build files), and the result of the Step 2b run as given in the request
   (passed / failed with the first error / not run and why) — a failure is not hidden or reworded as success.
   Absolute filesystem paths in config that tests or startup depend on are listed.
6. Security: authentication, roles and token storage are described as the code does them, with the file.
7. Every Rule is tagged `[code: <file>]` (and that file enforces it) or `[decided <source>]` (and that source says
   so); every Must-never is traceable to code or the root CLAUDE.md.
8. Tech debt states the TODO/FIXME count and top files; other debt as counts plus up to 10 locations. Debt recorded
   truthfully passes.
9. Core: 8 sections, at most 8 KB, the Reference lines' counts match the reference file. Reference: 6 sections, at
   most 30 KB. Both start with `Last updated: <commit> (<date>, /pl-onboard)` with the commit given in the request.
10. Text outside the plumbline markers is unchanged, in both files.
11. Decisions & trade-offs: each one names its source (code comment, README, ADR, commit message, config) — none is
    invented; "None found" is fine.

## Step 4 — Root master CLAUDE.md
Only if at least one unit passed. Writer: `plumbline-onboard-writer` with "root master file: `CLAUDE.md`, units: <the
table from Step 2 with results>, settings: <from Step 1>". Judge: `plumbline-judge` with the root file and this
checklist: (1) every unit is in the Units table with the right folder and CLAUDE.md; (2) How they connect matches the
units' Integrations/API sections; (3) Plumbline settings present (JIRA project, Confluence space and parent page, base
branch, Separate approver, PR target, branch pattern, API URL, frontend URL — the URLs match the config); (4) text outside the markers unchanged;
(5) **Architecture** (how the units fit, cross-cutting stack and patterns) and **Decisions & trade-offs** (each with
its source, none invented) are present; (6) **Decisions needed** lists every place where the repository's own docs, the settings and the code disagree on how
work is done (base/PR branch, branch naming, ticket key, test command, environments) — each with both sides and their
files — or says "None". Up to 3 attempts.

## Step 4b — Settle the decisions
For each item in **Decisions needed**, ask the user to choose (show both sides and the files). Write each answer into
the Plumbline settings as the value plus `(decided <date>)`, and remove the item from the list. Every other command
treats these settings as the rule. When nobody can answer (an unattended run), leave the items listed: other commands
then use the Plumbline settings value and name the open decision in their hand-over.

## Step 5 — Summary
One table: unit · result (PASS / ESCALATED) · attempts · file · test recipe result · open findings. If any unit's
tests did not run or failed on the untouched code, say so first: later `/pl-dev` runs on that unit will be
**UNVERIFIED** until it is fixed. Then:
- review the changes with `git diff`; discard one file with `git checkout -- <file>`;
- commit on a branch and open a PR so the team reviews the docs.

Do not commit, push, open a PR, or write to JIRA/Confluence unless the user asks — and then show exactly what will be
written and wait for a yes.
