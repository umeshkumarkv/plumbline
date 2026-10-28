---
description: Plumbline — daily sprint health report (stuck, blocked, unassigned, Definition of Done, velocity) from JIRA, checked by an independent judge
argument-hint: "[empty for the daily report, or a story key for one ticket]"
---

# /pl-sm

The daily sprint check: what is done, in review, in progress, blocked, at risk or unassigned; whether in-review
tickets meet the Definition of Done; velocity. A **writer** subagent writes the report from the sprint data; an
independent **judge** checks every list and number against that data. Up to 3 attempts, then it is handed to the
user. Comments are posted to JIRA only after the user says yes.

Target: $ARGUMENTS (empty = the whole active sprint; a key = that ticket only)

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-sm-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-sm-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match) and `gh` yourself. Do not research the code yourself — that is the
writer's/runner's and the judge's job; you route, check scope and hand over.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue — but only for a path you gave that helper; any other path is a FAIL finding, not a write.

## Every run
- **Judge replies:** the judge answers with the JSON its instructions give. If a reply is not that JSON, ask the same
  judge once to answer in that format; if it still does not, count the attempt as FAIL with the finding "judge reply
  unreadable". Never decide PASS yourself, and never edit or summarise away a finding before the next attempt.
- **Project memory:** before the first helper, for each unit involved take the `Verified at` commit from its
  CLAUDE.md and run `git diff --name-only <commit>..HEAD -- <unit folder>` (ignore the CLAUDE.md files themselves). Give every helper that list as **changed
  since verified** (or "none"; "unknown" if the CLAUDE.md has no `Verified at`), plus the path of `context.md` in the
  draft folder. More than 20 changed files in a unit → suggest `/pl-onboard <unit>` first. Never research the code
  yourself to fill gaps — the helpers do, and record what they find in `context.md`.
- **Limits:** at most 3 attempts per item, one writer and one judge per attempt. If the work covers more than 6 items
  (stories, units, tickets), show the list and ask before starting; when nobody can answer, do the first 6 and list
  the rest in the hand-over.
- **Nobody to answer** (a scheduled or headless run): wherever a step says ask, take the safe choice it names, or else
  stop that item — never guess. Write nothing outside the repository and `.plumbline-drafts/`, and list every
  question you could not ask in the hand-over.
- **Hand-over:** the first line is one of `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what
  did not run>` — then the details, then each question for the user, each with the exact text or command it would
  send or run.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,minutes,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, the
minutes from start to hand-over (run `date +%s` once at the start and once at the hand-over), and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Metrics mode
**`/pl-sm metrics`** — instead of the sprint report, read `.plumbline-drafts/metrics.csv` and show one table per
command: runs, median attempts, median minutes, PASS rate, runs where tests did not run, and approved / edited /
rejected / not yet answered (rows written before 2.6 have no minutes). Numbers only from the file; no judge needed. Stop after the table.

## Step 1 — Sprint data
With the connected JIRA/Atlassian tools, fetch the data as below. Without them, ask the user for an export of the
sprint's issues (JIRA "Export → CSV" or JSON, plus last sprint's Done count) and use that as the source instead.
1. JIRA project from the root `CLAUDE.md` Plumbline settings. Fetch the active sprint's issues (JQL
   `project = <KEY> AND sprint in openSprints()`): key, summary, status, assignee, updated, story points, labels,
   blocked-by links, whether the description has acceptance criteria. Also the previous sprint's Done count.
2. For each In Review ticket, its PR state: human approval, `/pl-code-review` result, CI status, merged
   (`gh pr list --search <KEY>` or the connected GitHub tools).
3. Write all of it, **unedited**, with today's date, to `.plumbline-drafts/sprint-<name>/facts.md` — make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it
   keeps the folder out of git without touching `.git/`). This file is the single source of truth.

**Stop and ask the user** if: JIRA returns an error; more than one sprint is open; a blocked-by chain is circular.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-sm-writer` with: the facts path, the report path
   `.plumbline-drafts/sprint-<name>/standup.md`; on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the standup path and the facts path; *Checklist:* the
   **Sprint report checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

### Sprint report checklist
1. Sections present: Done, In review, In progress, Blocked, At risk, Unassigned, Velocity, Flags for action, Comments.
2. Each list contains exactly the tickets the facts imply — recompute from the facts file: at risk = In Progress with
   no update for more than 2 days; needs attention = In Review for more than 1 day; blocked = a blocker that is not
   Done; unassigned = To Do with no assignee; no acceptance criteria flagged.
3. Velocity numbers equal the facts (this sprint's Done count and points, last sprint's count, trend).
4. Definition of Done is checked for every In Review ticket: acceptance criteria tested (QA passed), PR approved by a
   human, code review passed on the current commit, CI green, merged — each item marked from the facts.
5. Every flagged ticket says why and who must act; risks are ordered by impact on the sprint goal.
6. Comments to post are factual — no blame, no guesses presented as facts — and nothing contradicts the facts file.

## Step 3 — Hand over
Show the report. Ask before posting: the report (e.g. as a comment on the sprint's tracking issue or a Confluence
page) and the per-ticket comments — show the exact text first and wait for a yes. Never move or close a ticket whose
Definition of Done is not met.
