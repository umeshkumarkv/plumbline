---
description: Plumbline — run a story's acceptance criteria against the running system and record the evidence; checked by an independent judge
argument-hint: "<story key, e.g. CRS-12>"
---

# /pl-qa

Test one story's acceptance criteria against the **running** system — API calls and, for UI criteria, Playwright — and
record the evidence. A **runner** subagent executes the tests; an independent **judge** checks the evidence actually
proves each criterion. Up to 3 attempts, then it is handed to the user. QA reports what it observed; it never fixes or
diagnoses code.

Story: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-qa-runner` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-qa-runner` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the runner's or the judge's work yourself. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match) (and `gh` if present) yourself, plus
`curl` (`curl.exe` on Windows) for the health check and the start commands the user approves in Step 1. Do not research the code yourself — that is the
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

## Drafts
Evidence goes in `.plumbline-drafts/<KEY>/qa/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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

## Step 1 — Setup
1. Read the story and its acceptance criteria from JIRA (or ask the user to paste them) and save them as
   `.plumbline-drafts/<KEY>/story.md`. The branch in its latest `[Plumbline /pl-dev]` comment is the code under test.
2. **Gate:** `plumbline-review-passed` on the story (see JIRA hand-off); checked as the JIRA hand-off Gate says.
3. **Environment.** URLs from the root `CLAUDE.md` Plumbline settings (API URL, frontend URL); ask if missing. Check
   each answers with exactly `curl -s -o /dev/null -m 5 -w "%{http_code}" <url>` (any HTTP status means it is up; `000`
   means it is not). If not, offer:
   - **(a) start it here** — show the exact run command of each unit from its CLAUDE.md "Build & run" (with the
     branch under test checked out) and wait for a yes. Start each in the background, poll the URL for up to 3
     minutes, and stop what you started at the end of the run;
   - **(b) use another environment** — the user gives a staging/test URL; use it for this run only;
   - **(c) stop** — report "QA not run: system not reachable at <url>". Never mark a criterion PASS or FAIL without
     having run it.
   When nobody can answer (an unattended run), take (c).
4. Credentials come **only** from environment variables (`PLUMBLINE_DEMO_USER`, `PLUMBLINE_DEMO_PASSWORD`, or what the
   CLAUDE.md names). Never write a password or token into a file, a report or a comment.
5. Classify each criterion: **API** (status/body), **UI** (what the user sees), or **BOTH** (a submit flow); and
   **WRITES** (creates/changes data) or **READS**. Show the table and write it to `.plumbline-drafts/<KEY>/qa/plan.md`.

## Step 2 — Attempts (1, 2, 3)
1. **Runner** — start `plumbline-qa-runner` with: the plan path, the story path, the URLs, the names of the credential
   environment variables, the evidence path `.plumbline-drafts/<KEY>/qa/evidence.md`; on attempts 2–3 the judge's
   findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the evidence path, the plan and story paths;
   *Checklist:* the **QA evidence checklist** below, verbatim.
3. PASS (every criterion passed, judge PASS) → Step 3. Judge FAIL (evidence does not prove the criteria) → next
   attempt. A criterion that genuinely **fails** is not retried away: it is the result — go to Step 3 with it.

### QA evidence checklist
1. Every criterion has a result (PASS / FAIL) with the exact request or UI steps, the expected and the actual outcome.
2. Each PASS is proven by checking the field and value the criterion names, not only the status code.
3. Writes: the evidence shows the data really changed (a follow-up read, or the database/event when the plan has
   access).
4. Standard edge cases were run where they apply: unknown id → 404, no credentials → 401/redirect, invalid input →
   400/422, response format as the CLAUDE.md files describe.
5. UI checks assert the behaviour the criterion describes, not just that an element exists.
6. Nothing was skipped without a stated infrastructure reason; no password or token appears in the evidence.
7. Failures are reported as observed (request, expected, actual, body) — no guesses at the cause.

## Step 3 — Hand over
Show: criterion · type · result. For each failure, exactly four fields: request/steps · expected · actual · response
body. If a failure looks like a design problem (wrong owner field, role, missing header), say "design gap — run
`/pl-arch <KEY>`" and nothing more. Ask before posting the report as a JIRA comment (`[Plumbline /pl-qa] <date>`), the approval label as the JIRA hand-off says (`plumbline-qa-passed`) when every
criterion passed, or moving the ticket — show
the exact text first and wait for a yes.
