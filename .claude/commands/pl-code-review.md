---
description: Plumbline — independent review of a branch or pull request against the project's CLAUDE.md rules
argument-hint: "<PR number, branch name, or empty for the current branch>"
---

# /pl-code-review

Review a change with an independent **judge** subagent that never saw how the change was written. Read-only: the
review is posted only if the user says yes.

Target: $ARGUMENTS (empty = the current branch)

## How the judge is started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with agent `plumbline-judge` (`.github/agents/`). If subagents are not available
  in this chat, stop and say so.

Do not review the change yourself first and do not pass your opinion to the judge. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match) (and
`gh` if present) yourself; read files with your file read/search tools.

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
The file stays on this machine (`.plumbline-drafts/` must be in `.git/info/exclude`); `/pl-sm` can summarise it.

## Step 1 — What to review
- Base branch: from the root `CLAUDE.md` Plumbline settings (else the repository's default branch).
- A PR number: `git fetch origin pull/<n>/head:pr-<n>` and review `pr-<n>`; or use the connected GitHub tools to read
  the PR. A branch: review it against the base. Empty: the current branch.
- The diff to review: `git diff <base>...<branch>`. Empty diff → say so and stop.
- The rulebook: the root `CLAUDE.md` and the CLAUDE.md of every unit the diff touches.
- **Scope:** the feature-tracker rows whose Branch is this branch give the stories and designs it implements — use
  **all** of them. None found → ask the user which stories it implements; if there are none or no answer, review
  against the CLAUDE.md files only and say so in the report.

## Step 2 — Judge
Start `plumbline-judge` with exactly:
- *Review:* "`git diff <base>...<branch>` in this repository", the list of CLAUDE.md files that apply, and the story
  and design files in scope (or "no story given");
- *Checklist:* the **Review checklist** below, verbatim.

### Review checklist
1. **Correctness** — the code does what its name, story or PR title says; edge cases (null, empty, limits) handled.
2. **Project rules** — every rule and Must-never in the applicable CLAUDE.md files is respected.
3. **Security** — input validation, authorization on new endpoints, no secrets in code or logs, no SQL/command
   string concatenation, no sensitive data in errors.
4. **Data** — migrations are safe on existing data; no breaking schema change without a plan.
5. **APIs** — contract changes are backward compatible or flagged; callers in other units updated.
6. **Tests** — new behaviour is tested; no test deleted, skipped or weakened.
7. **Errors and logging** — failures handled, logged with IDs not secrets.
8. **Performance** — no N+1 queries, unbounded queries or loops over remote calls on a hot path.
9. **Scope** — no unrelated changes; no edits to `.claude/`, `.github/` or CLAUDE.md files unless that is the point
   of the change.
10. **Stories and designs** — every acceptance criterion of the stories in scope is implemented, every test their
    designs list exists, and the diff does nothing those stories do not ask for. N/A when no story is given.
Judge only what this diff introduces; pre-existing issues are out of scope.

## Step 3 — Report
On PASS, set the tracker rows of this branch to Status `reviewed` and Last check to `code-review PASS <date>`.
Show the verdict and a table: severity · file:line · finding · fix. Then offer: post it as a PR review comment
(connected GitHub tools or `gh pr review`) — show the exact text and wait for a yes. Never approve or merge.
