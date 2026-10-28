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
Drafts go in `.plumbline-drafts/<slug>/` at the repository root (slug = a short kebab-case name for the idea). Before
the first draft, make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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
1. Every section of the template has real content (`None` is fine only for Open questions and Dependencies).
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
Show the PRD. Then ask before each of: publish it as a Confluence page `<title> — PRD` under the `Confluence parent
page`; create the epic in JIRA (Plumbline settings: JIRA project) with `epic.md` as its description (summary, PRD link
and version); add `plumbline-prd-approved`. Show the exact content first and wait for a yes. After the epic exists,
put its key in the page title. No Confluence → the full PRD goes in the epic description.
