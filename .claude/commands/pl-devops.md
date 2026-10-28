---
description: Plumbline — diagnose a failing CI run and fix it (code, tests, coverage) or propose the fix (config, pipeline), checked by an independent judge
argument-hint: "<PR number or branch with a failing CI run>"
---

# /pl-devops

Get a failing CI run green the honest way. A **fixer** subagent classifies the failure and either fixes it (compile
error, failing test, coverage) or writes a diagnosis for you to approve (pipeline, container, migration, dependency,
secrets). An independent **judge** checks the fix addresses the cause and weakens nothing. Up to 3 attempts, then it
is handed to the user. Nothing is pushed without your yes.

Target: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-devops-fixer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-devops-fixer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the fixer's or the judge's work yourself. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match), `gh` and the project's build/test
command yourself. Do not research the code yourself — the fixer and the judge do; you route,
check scope and hand over.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue.

## Drafts
Logs and diagnoses go in `.plumbline-drafts/ci-<branch>/`. Make sure the line
`.plumbline-drafts/` is in `.git/info/exclude` — read and edit that file with your file tools (no shell `echo`/`mkdir`).

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/` must be in `.git/info/exclude`); `/pl-sm` can summarise it.

## Step 1 — The failure
1. Find the latest failed run for the PR/branch (`gh run list --branch <b>`, `gh run view <id> --log-failed`, or the
   connected GitHub tools) and save the failing log to `.plumbline-drafts/ci-<branch>/ci.log`. No `gh` and no GitHub
   tools → ask the user to paste the failing log.
2. Check out the branch (`git switch <branch>`; `git status` must be clean first).
3. **Pre-existing failures:** a failure that also fails on the base branch (its last CI run, or a log the user gives)
   is not this branch's problem — note it for the hand-over and fix only what this branch broke. Several categories
   *caused by this branch* is a stop-and-ask; one new failure plus old ones is not.

## Step 2 — Attempts (1, 2, 3)
1. **Fixer** — start `plumbline-devops-fixer` with: the log path, the branch, the build/test command (from the units'
   CLAUDE.md), the diagnosis path `.plumbline-drafts/ci-<branch>/diagnosis.md`; on attempts 2–3 the new log and the
   judge's findings.
2. **If the fixer wrote a diagnosis instead of a fix** (pipeline YAML, container file, migration already applied,
   dependency, secret): show it to the user. Changes under `.github/` are never made by the agent — they go in a
   separate PR a human makes. For other categories, if the user approves, start the fixer again with "approved:
   apply the diagnosis" (this does not use an attempt).
3. **Local check** — run the build/test command yourself; it must pass.
4. **Judge** — start `plumbline-judge` with exactly: *Review:* "`git diff` on branch <branch>", the diagnosis/log
   paths; *Checklist:* the **Fix checklist** below, verbatim. FAIL → next attempt.
5. **CI** — on judge PASS, ask the user before commit + push to the PR branch (show the message; never `main`/the base
   branch). After the push, check the new run (`gh run view`); still red → save the new log, next attempt.

### Fix checklist
1. The fix addresses the root cause named in the classification, not a symptom.
2. No test, check, coverage threshold or scanner was skipped, disabled, deleted or loosened.
3. The change is minimal — nothing unrelated to the failure.
4. Business behaviour is unchanged unless the failure was a real bug in it (then say so).
5. No secret, credential or environment-specific value was added.
6. The change can be rolled back by reverting this one commit.

**Stop and ask the user** if: the fix needs business-logic changes beyond the failing case; a migration was already
applied to a shared environment; this branch caused several failure categories at once; the change in behaviour looks
intended — a story or commit says so (then the user decides whether code or test is right; a commit called a
refactor or tidy-up did not intend to change output, so the tests are right); or the build fails with a new category after
a fix.

## Step 3 — Hand over
Show: category · cause · fix · local result · CI result · judge verdict.
