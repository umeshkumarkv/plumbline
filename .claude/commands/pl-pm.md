---
description: Plumbline — turn a feature idea into a PRD (and, with your yes, a JIRA epic), checked by an independent judge
argument-hint: "<feature idea in plain English>"
---

# /pl-pm

Turn a feature idea into a PRD: problem, solution, success criteria, scope, dependencies, prioritised backlog. A
**writer** subagent drafts it; an independent **judge** checks it. Up to 3 attempts, then it is handed to the user.
The epic is created in JIRA only after the user says yes.

Idea: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-pm-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-pm-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
only `git` (from the repository root — never `git -C`, which permission rules do not match) yourself; read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue.

## Drafts
Drafts go in `.plumbline-drafts/<slug>/` at the repository root (slug = a short kebab-case name for the idea). Before
the first draft, make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — Context
Read the root `CLAUDE.md` (solution, units, out-of-scope list, Plumbline settings) and the CLAUDE.md of the units the
idea touches. If the idea is empty or too vague to name who has the problem, ask one question.

**Stop and ask the user** if: the idea is entirely in the out-of-scope list; it needs a new service/unit not in the
root CLAUDE.md; it contradicts a rule in the root CLAUDE.md; or existing epics already cover part of it (if JIRA tools
are connected, search for them).

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-pm-writer` with: the idea, the CLAUDE.md paths, the draft path
   `.plumbline-drafts/<slug>/prd.md`; on attempts 2–3 also the judge's findings (verbatim JSON).
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the PRD path and the CLAUDE.md paths; *Checklist:* the
   **PRD checklist** below, verbatim. PASS → Step 3. FAIL → next attempt with the findings.

After 3 failed attempts: stop, show the last findings and the draft, and hand over to the user.

### PRD checklist
1. All 6 sections present: Problem, Solution, Success criteria, Out of scope, Dependencies, Backlog.
2. Problem names a specific user role, what they cannot do today, and the business impact.
3. Solution describes the behaviour in at least a paragraph, including what the user sees and any API/data change.
4. At least 2 success criteria, each measurable — verifiable by an API call or something visible in the UI.
5. Out of scope is explicit and refers to the root CLAUDE.md out-of-scope list where it applies.
6. The feature maps to the units in the root CLAUDE.md with no ambiguity about which unit owns what.
7. Dependencies: blocked-by and enables are named, or explicitly "None".
8. Nothing from the root CLAUDE.md out-of-scope list appears in P1, P2 or P3.
9. P1 fits one sprint (story points ≤ 20 unless the root CLAUDE.md says otherwise).
10. No placeholders (`{…}`, TBD, TODO) left.

## Step 3 — Hand over
Show the PRD. Then ask before each of: create the epic in JIRA (Plumbline settings: JIRA project) with the PRD as its
description and label `plumbline-prd-approved`; publish the PRD to Confluence. Show the exact content first and wait
for a yes. No JIRA/Confluence tools connected → give the user the PRD to paste.
