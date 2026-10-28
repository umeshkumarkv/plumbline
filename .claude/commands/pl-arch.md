---
description: Plumbline — technical design for one story (API, data, logic, integrations, security, tests), checked by an independent judge before any code
argument-hint: "<story key, e.g. CRS-12, or a pasted story>"
---

# /pl-arch

Write the technical design a developer (or `/pl-dev`) builds from: endpoint, data changes, service logic,
calls and events, security, tests, API-spec delta. A **writer** subagent drafts it; an independent **judge** checks it
against the story and the code. Up to 3 attempts, then it is handed to the user. Nothing is posted without a yes.

Story: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-arch-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-arch-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
only `git` (from the repository root — never `git -C`, which permission rules do not match) yourself; read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue.

## Drafts
Drafts go in `.plumbline-drafts/<KEY>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).
Save the story text you fetched as `.plumbline-drafts/<KEY>/story.md` (the writer and judge read it there). If the
feature tracker already has a story file for this key, use that instead of fetching.

## Feature tracker
`.plumbline-drafts/features.md` links each story to its files and branch, so every command finds its inputs without
being told. One markdown table, one row per story:
`| Story | Title | Unit | Story file | Design file | Branch | Status | Last check |`
Status is one of: `story ready` · `designed` · `built` · `built, tests not run` · `reviewed` · `QA passed` ·
`documented`. Read it with your file tools; create it with that header if missing; change only your own rows, with your
edit tool. A path or branch named in this command's input wins over the tracker.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — Pre-flight
Fetch the story with the connected JIRA tools (or ask the user to paste it). Read the root `CLAUDE.md` and the unit's
CLAUDE.md.

**Stop and ask the user** if: the story has no acceptance criteria; a blocked-by ticket is not Done; the design would
need another unit's database, a new unit, an out-of-scope feature, or a new library the root CLAUDE.md does not allow.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-arch-writer` with: the story path, the unit, the CLAUDE.md paths, the draft path
   `.plumbline-drafts/<KEY>/design.md`; on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the design path, the story path, the CLAUDE.md paths and
   the unit folder; *Checklist:* the **Design checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

After 3 failed attempts: stop, show the last findings, and hand over (usually the story needs the BA to clarify).

### Design checklist
1. Every acceptance criterion maps to a part of the design (endpoint, rule, error, UI behaviour) — none left out.
2. Endpoint: method, path, auth/roles, request and response fields with types, and the unit and port match the code
   and the routing/gateway config.
3. Every error path in the criteria has a status and an error code in the project's error format.
4. Data: the migration (next free version number, in the unit's own schema) or an explicit "no schema change"; entity
   changes with types.
5. Service logic: class and method, ordered steps, error paths; follows the layering rules in the CLAUDE.md files.
6. Calls to other units hit endpoints that exist; the failure/timeout behaviour is stated. Consumed events have a
   producer; produced events have a consumer or a stated reason.
7. Cache/config/env-var changes named, or "none".
8. **Identity and access, exactly:** the field used for ownership checks, the kind of each identifier (e.g. user id vs
   customer id, compared like with like), who may call each endpoint per role, and the headers/claims the gateway
   passes.
9. Tests: at least 3 cases per layer touched (logic, API/controller, UI), including the error paths.
10. API-spec delta (e.g. openapi.yaml) stated, or "no change". No placeholders left.

## Step 3 — Hand over
Set the story's tracker row: Design file, Status `designed` (add the row if missing). One design may cover several
stories — set it on each.
Show the design. Ask before posting it as a comment on the story with label `plumbline-arch-approved` — show the exact
content first and wait for a yes. Next step: `/pl-dev <KEY>`.
