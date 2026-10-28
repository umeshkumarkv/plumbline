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
writer's reasoning or your own opinion to the judge. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match) commands yourself (they work in bash,
PowerShell and cmd alike); find and read files with your file search/read tools — never `find`, `grep`, `ls`, `cat`.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/` must be in `.git/info/exclude`); `/pl-sm` can summarise it.

## Step 1 — Settings
Read the root `CLAUDE.md` if it exists. If it has no **Plumbline settings** (JIRA project, Confluence space, base
branch), ask the user for them once (base branch: suggest the repository's default branch) and keep the answers for
the root file in Step 4.

## Step 2 — Find the units
Use `git ls-files` or your file search tool to find build files: `pom.xml`, `build.gradle`, `build.gradle.kts`, `package.json` (ignore `node_modules`,
`target`, `build`, `dist`), plus other stacks' build files if present. A folder with its own build file and source is a
unit; a parent build file that only lists modules is not. For each unit decide its CLAUDE.md:
- a unit in a folder → `<folder>/CLAUDE.md`;
- an app at the repository root → `src/CLAUDE.md` (the root `CLAUDE.md` is the master).

Show the user the list (name, folder, kind, CLAUDE.md) in one table and continue.

## Step 3 — Each unit (units may run in parallel)
For attempt = 1, 2, 3:
1. **Writer** — start `plumbline-onboard-writer` with: the unit name, folder, CLAUDE.md path, and on attempts 2–3
   the judge's findings from the previous attempt (verbatim JSON).
2. **Judge** — start `plumbline-judge` with exactly:
   - *Review:* the CLAUDE.md path, the unit folder, and "compare with `git diff -- <CLAUDE.md path>`: text outside the
     plumbline markers must be unchanged";
   - *Checklist:* the **Onboard checklist** below, verbatim.
3. **PASS** → next unit. **FAIL** → next attempt with the findings.

After 3 failed attempts: leave the file as it is, mark the unit **ESCALATED**, keep its last findings for the summary,
and move on.

### Onboard checklist
1. Every endpoint/route the code defines is listed in API — search the mapping annotations or route definitions, compare
   the count, and check at least 10 at random. None listed that the code does not define.
2. Frontend: every backend call is listed with the endpoint it hits; calls that no backend endpoint serves are listed
   as such, not presented as working. (N/A for a backend.)
3. Every entity/table is listed in Data with its key fields; none listed that the code, migrations or SQL scripts do
   not define. Column names are fields, not tables.
4. Integrations: every outbound HTTP call, messaging topic and cache the code uses is listed; nothing invented.
5. Build & run commands, port and configuration match the build and config files.
6. Security: authentication, roles and token storage are described as the code does them, with the file.
7. Rules and Must-never items are each traceable to code or the root CLAUDE.md.
8. Tech debt states the TODO/FIXME count and top files; other debt as counts plus up to 10 locations. Debt recorded
   truthfully passes.
9. All 12 sections present ("None found" is fine); the file is at most 30 KB.
10. Text outside the plumbline markers is unchanged.

## Step 4 — Root master CLAUDE.md
Only if at least one unit passed. Writer: `plumbline-onboard-writer` with "root master file: `CLAUDE.md`, units: <the
table from Step 2 with results>, settings: <from Step 1>". Judge: `plumbline-judge` with the root file and this
checklist: (1) every unit is in the Units table with the right folder and CLAUDE.md; (2) How they connect matches the
units' Integrations/API sections; (3) Plumbline settings present (JIRA project, Confluence space, base branch, API URL,
frontend URL — the URLs match the config); (4) text outside the markers unchanged. Up to 3
attempts.

## Step 5 — Summary
One table: unit · result (PASS / ESCALATED) · attempts · file · open findings. Then:
- review the changes with `git diff`; discard one file with `git checkout -- <file>`;
- commit on a branch and open a PR so the team reviews the docs.

Do not commit, push, open a PR, or write to JIRA/Confluence unless the user asks — and then show exactly what will be
written and wait for a yes.
