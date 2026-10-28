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

## Feature tracker
`.plumbline-drafts/features.md` links each story to its files and branch, so every command finds its inputs without
being told. One markdown table, one row per story:
`| Story | Title | Unit | Story file | Design file | Branch | Status | Last check |`
Status is one of: `story ready` · `designed` · `built` · `built, tests not run` · `reviewed` · `QA passed` ·
`documented`. Read it with your file tools; create it with that header if missing; change only your own rows, with your
edit tool. A path or branch named in this command's input wins over the tracker.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,minutes,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, the
minutes from start to hand-over (run `date +%s` once at the start and once at the hand-over), and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — Setup
1. Use the story file from the feature tracker if there is one; otherwise fetch the story and its acceptance criteria
   (JIRA tools, or ask the user to paste them) and save them as `.plumbline-drafts/<KEY>/story.md`. The tracker row's
   Branch is the code under test.
2. **Gate:** the change should be reviewed first — the PR for this story has a passing `/pl-code-review` or a
   human approval. If not, tell the user and ask whether to continue.
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
When every criterion passed, set the tracker row to Status `QA passed`.
Show: criterion · type · result. For each failure, exactly four fields: request/steps · expected · actual · response
body. If a failure looks like a design problem (wrong owner field, role, missing header), say "design gap — run
`/pl-arch <KEY>`" and nothing more. Ask before posting the report as a JIRA comment or moving the ticket — show
the exact text first and wait for a yes.
