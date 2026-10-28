---
description: Plumbline — after a change is merged, update the API spec and CLAUDE.md files to match it, checked by an independent judge
argument-hint: "<PR number, story key, or branch>"
---

# /pl-doc

After a change lands, bring the documentation in line with the code: the API spec (e.g. `openapi.yaml`) and the
CLAUDE.md files of the units it touched. A **writer** subagent edits the docs; an independent **judge** checks every
change in the code is reflected. Up to 3 attempts, then it is handed to the user. Docs only — never code.

Change: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-doc-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-doc-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match) (and `gh` if present) yourself. Do not research the code yourself — that is the
writer's/runner's and the judge's job; you route, check scope and hand over.
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
- **Gate:** start only when the previous step's label is on the ticket. With `Separate approver: yes` (Plumbline
  settings; the default) it must also have been added — per the issue's change history — by someone other than that
  step's `Run by`. Otherwise stop: `STOPPED: <label> not on <KEY>` · `STOPPED: <label> on <KEY> self-approved by
  <name>` · `STOPPED: cannot verify who approved <KEY>`. Only with `Separate approver: no` may the SME say go on.
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first.
  `Run by` is the connected Atlassian user. `Separate approver: yes` → do not add the label: write `Approval: pending
  — <label> to be added by the <role> approver` and tell the SME who must approve. `no` → add the label after the yes
  and write `Approval: self — <name> (<date>)`.
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

## Step 1 — The change
1. Find the change: a story key → the PR in its `[Plumbline /pl-dev]` comment; a PR number (`gh pr view <n>` / `gh pr diff <n>`, or the connected GitHub tools), a story key
   (search PRs for it), or a branch. Work out the commit range: `<base>...<merge or head>`.
2. List what changed in the code: endpoints, request/response fields, error codes, events/topics, cache keys, env vars,
   migrations, new libraries, new units. From the story's JIRA ticket also take: the business rules its acceptance
   criteria add (→ Rules), the *Decisions* of the design page its `[Plumbline /pl-arch]` comment links (→ Decisions & trade-offs), and every
   "Add to CLAUDE.md" / "CLAUDE.md out of date" note in its `[Plumbline …]` comments. CLAUDE.md is the single source
   of truth: after this merge it must say everything the next agent needs, so no one rediscovers it from the code.
3. `git status` must be clean. Create a docs branch: `git switch -c docs/<KEY or pr-n> <base branch>`.

**Stop and ask the user** if: the change adds a new unit or a new cross-unit event (the root CLAUDE.md needs a human
decision first); the merged code contradicts the existing API spec in a way that needs an architecture call; or a new
library arrived without the root CLAUDE.md allowing it.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-doc-writer` with: the commit range, the list from Step 1, the files it may edit (the
   API spec files and CLAUDE.md files of the touched units; the root CLAUDE.md only if the architecture changed); on
   attempts 2–3 the judge's findings.
2. **Scope check** — `git status --porcelain`: only documentation files changed. Anything else → finding, next attempt.
3. **Judge** — start `plumbline-judge` with exactly: *Review:* "the code change `git diff <range>` and the doc change
   `git diff`", the files edited; *Checklist:* the **Doc checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

### Doc checklist
1. Every endpoint the code change added or changed is in the API spec with the right method, path, parameters,
   request and response schema, and error responses.
2. Every new or changed response field is in the spec's schema with the right type (money as string where the
   CLAUDE.md files say so, ids with their format, timestamps as date-time).
3. Every new error code is documented, and every documented status/error code is what the code really returns — trace
   each thrown exception to its handler (an unhandled exception is a 500, not a 400).
4. Every new event/topic, cache key and environment variable is in the touched unit's CLAUDE.md.
5. New libraries and migrations are noted in the unit's CLAUDE.md.
6. Edits are in place: existing sections updated, nothing unrelated rewritten or removed; plumbline markers kept.
7. The root CLAUDE.md changed only if the architecture changed (new unit, new cross-unit event, new pattern).
8. The API spec still parses (valid YAML/JSON) and every documented path exists in the code.

## Step 3 — Hand over
Show the doc diff summary and the judge verdict. Ask before commit, push and opening a docs PR, and before the JIRA
comment `[Plumbline /pl-doc] <date>` with the docs PR link — show the exact text first and wait for a yes. The docs PR
needs the architect's approval: the architect owns what CLAUDE.md says. Set `Last updated: <merge commit> (<date>,
/pl-doc)` in each CLAUDE.md you change. Never commit to the base branch directly.
