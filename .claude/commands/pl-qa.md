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

Never do the runner's or the judge's work yourself. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match), `bash .github/plumbline/check-template.sh` (and `gh` if present) yourself, plus
`curl` (`curl.exe` on Windows) for the health check and the start commands the user approves in Step 1. Do not research the code yourself — that is the
writer's/runner's and the judge's job; you route, check scope and hand over.
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

## Drafts
Evidence goes in `.plumbline-drafts/<KEY>/qa/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

## JIRA hand-off
Roles pass work to each other only through JIRA — tickets, comments and labels — never through files on someone's
machine, so no agent redoes what an earlier role settled. Only the PRD is a Confluence page (under the `Confluence
parent page` in the Plumbline settings), linked from the epic; every other hand-off is the ticket or a comment on it.

| Step | Posts | Template | Approval label |
|---|---|---|---|
| `/pl-pm` | PRD page; the epic, with summary + PRD link | `prd.md`, `epic.md` | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — criteria, points, `Blocks` links | `story.md` | `plumbline-dor-ready` |
| `/pl-arch` | story comment — the full design | `handoff-arch.md` | `plumbline-arch-approved` |
| `/pl-dev` | story comment — branch, PR, test result | `handoff-dev.md` | — (the PR is reviewed next) |
| `/pl-code-review` | PR review + story comment — verdict and findings | `handoff-review.md` | `plumbline-review-passed` |
| `/pl-qa` | story comment — evidence per criterion | `handoff-qa.md` | `plumbline-qa-passed` |
| `/pl-doc` | docs PR updating CLAUDE.md + story comment | `handoff-doc.md` | the architect approves the docs PR |
| `/pl-devops`, `/pl-sm` | comment on the story / sprint issue | `handoff-devops.md`, `sprint-report.md` | — |
| `/pl-approve` | the approver's decision on one step + its label | `approval.md` | (adds the step's label) |

- **Input:** read the ticket — description, labels, links, the latest comment of each kind that starts
  `[Plumbline /pl-<role>]` or `[Plumbline approve /pl-<role>]` (JIRA returns them as `\[Plumbline …\]`: ignore
  backslashes), and for an epic the PRD page it links, **at the version
  it names** (no version from the tools → compare last-modified times; neither → say so in the hand-over). A PRD page
  or hand-off comment changed after its approval → `STOPPED: <what> changed after approval`. Do not redo an earlier
  role's work; if it is wrong, say which role must fix it.
- **Gate:** start only when the previous step's label is on the ticket. With `Separate approver: yes` (the default)
  the approval must come from someone other than the **author** of that step's hand-off (the comment's author; for
  an epic or story description, the issue's creator): a `[Plumbline approve /pl-<role>]` comment by them, else the
  issue's change history for the label. Otherwise stop: `STOPPED: <label> not on <KEY>` · `STOPPED: <KEY>
  self-approved by <name>` · `STOPPED: cannot verify who approved <KEY> — run /pl-approve`.
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first. JIRA
  records who posted it. `Separate approver: yes` → no label; tell the SME `/pl-approve <KEY> <role>` must be run by
  another person. `no` → add the label after the yes.
- No Confluence tools or no parent page → the PRD goes in the epic description. A comment must stay under 30,000
  characters (JIRA's limit is 32,767): longer → stop and say the story should be split.
  No JIRA tools → give the output as text to paste, and say the hand-off is manual. `.plumbline-drafts/` is scratch.

## Metrics
At the hand-over append to `.plumbline-drafts/metrics.csv` (header, if new:
`date,command,target,attempts,verdict,tests_run,minutes,human_decision`): date, command, story/branch/PR, attempts,
verdict, tests ran `yes`/`no`/`n/a`, minutes (`date +%s` at start and at hand-over), and `human_decision` once the user
answers: `approved`, `edited` or `rejected`. It stays local; `/pl-sm metrics` summarises it.
**Files:** create drafts and metrics with your write tool (it creates folders) — never `mkdir`, `echo`, `printf` or
redirection, which permission settings block.

## Step 1 — Setup
1. Read the story (business acceptance criteria) and the *Acceptance criteria → design* section of its latest
   `[Plumbline /pl-arch]` comment — the technical check for each AC — and save both as `.plumbline-drafts/<KEY>/story.md`. The branch in its latest `[Plumbline /pl-dev]` comment is the code under test.
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
