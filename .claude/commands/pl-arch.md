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
unchanged, then continue — but only for a path you gave that helper; any other path is a FAIL finding, not a write.

## Every run
- **Judge replies:** the judge answers with the JSON its instructions give. If a reply is not that JSON, ask the same
  judge once to answer in that format; if it still does not, count the attempt as FAIL with the finding "judge reply
  unreadable". Never decide PASS yourself, and never edit or summarise away a finding before the next attempt.
- **Project memory:** the CLAUDE.md files are the single source of truth for the project, kept current after every
  merge by `/pl-doc`. Helpers work from them and from the JIRA ticket; they open code only for the files they change
  or review. Never research the code yourself. Collect what helpers report as "Add to CLAUDE.md" or "CLAUDE.md out
  of date" and list it in the hand-over for `/pl-doc`.
- **Templates:** whatever will be posted is written on its template in `.github/plumbline/templates/` (see the
  JIRA hand-off table). Before each judge, and again before posting, run
  `bash .github/plumbline/check-template.sh <template> <draft>`: a FAIL is that attempt's finding and the judge is not
  started. If bash cannot run here, add "matches its template's headings and fields" to the judge's checklist.
  Give each writer its template, the version (`.github/plumbline/VERSION`), `git rev-parse --short HEAD` and `Run by`
  (the connected Atlassian user's name; else ask once).
- **Limits:** at most 3 attempts per item, one writer and one judge per attempt. If the work covers more than 6 items
  (stories, units, tickets), show the list and ask before starting; when nobody can answer, do the first 6 and list
  the rest in the hand-over.
- **Nobody to answer** (a scheduled or headless run): wherever a step says ask, take the safe choice it names, or else
  stop that item — never guess. Write nothing outside the repository and `.plumbline-drafts/`, and list every
  question you could not ask in the hand-over.
- **Hand-over:** the first line is one of `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what
  did not run>` — then the details, then each question for the user, each with the exact text or command it would
  send or run.

## Drafts
Drafts go in `.plumbline-drafts/<KEY>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).
Save the story you read from JIRA (description, criteria, links) as `.plumbline-drafts/<KEY>/story.md` for the writer
and judge of this run.

## JIRA hand-off
Roles pass work to each other only through JIRA and Confluence — never through files on someone's machine — so no
agent redoes what an earlier role settled. Specs people review and edit (PRD, design) are Confluence pages under the
`Confluence parent page` (Plumbline settings); JIRA holds the state (labels), a short summary and the page link.

| Step | Posts | Template | Approval label |
|---|---|---|---|
| `/pl-pm` | PRD page; the epic, with summary + PRD link | `prd.md`, `epic.md` | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — criteria, points, `Blocks` links | `story.md` | `plumbline-dor-ready` |
| `/pl-arch` | design page under the PRD page; story comment with its link and version | `design.md`, `handoff-arch.md` | `plumbline-arch-approved` |
| `/pl-dev` | story comment — branch, PR, test result | `handoff-dev.md` | — (the PR is reviewed next) |
| `/pl-code-review` | PR review + story comment — verdict and findings | `handoff-review.md` | `plumbline-review-passed` |
| `/pl-qa` | story comment — evidence per criterion | `handoff-qa.md` | `plumbline-qa-passed` |
| `/pl-doc` | docs PR updating CLAUDE.md + story comment | `handoff-doc.md` | the architect approves the docs PR |
| `/pl-devops`, `/pl-sm` | comment on the story / sprint issue | `handoff-devops.md`, `sprint-report.md` | — |

- **Input:** read the ticket — description, labels, links, the latest comment of each kind that starts
  `[Plumbline /pl-<role>]`, and each page those link to, **at the version the comment names**. A page now at a later
  version → `STOPPED: <page> changed after approval (v<n> → v<m>)`. Do not redo an earlier role's work; if it is
  wrong, stop and say which role must fix it.
- **Gate:** start only when the previous step's label is on the ticket. Missing → `STOPPED: <label> not on <KEY>`
  (the SME adds it, or tells you to go on).
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first; then
  add the label.
- No Confluence tools or no parent page → the PRD goes in the epic description and the design in the arch comment.
  No JIRA tools → give the output as text to paste, and say the hand-off is manual. `.plumbline-drafts/` is scratch.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,minutes,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, the
minutes from start to hand-over (run `date +%s` once at the start and once at the hand-over), and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft and metrics file with your write tool — it creates missing folders. Never
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
1. *Acceptance criteria → design* maps every AC id of the story to a part of the design — none left out.
2. Endpoint: method, path, auth/roles, request and response fields with types, and the unit and port match the CLAUDE.md
   files (and any code the design cites).
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
Show the design. Ask before (1) publishing it as a Confluence page `<KEY> — <summary> — Design` under the PRD page
(else the parent page), (2) posting the story comment on `handoff-arch.md` with the page link and version, and (3)
adding `plumbline-arch-approved` — show the exact content first and wait for a yes. A design covering several stories
is one page, linked from each story. Next step: `/pl-dev <KEY>`.
