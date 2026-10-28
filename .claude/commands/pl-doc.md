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
- **Limits:** at most 3 attempts per item, one writer and one judge per attempt. If the work covers more than 6 items
  (stories, units, tickets), show the list and ask before starting; when nobody can answer, do the first 6 and list
  the rest in the hand-over.
- **Nobody to answer** (a scheduled or headless run): wherever a step says ask, take the safe choice it names, or else
  stop that item — never guess. Write nothing outside the repository and `.plumbline-drafts/`, and list every
  question you could not ask in the hand-over.
- **Hand-over:** the first line is one of `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what
  did not run>` — then the details, then each question for the user, each with the exact text or command it would
  send or run.

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
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — The change
1. Find the change: a story key → its tracker row's Branch; a PR number (`gh pr view <n>` / `gh pr diff <n>`, or the connected GitHub tools), a story key
   (search PRs for it), or a branch. Work out the commit range: `<base>...<merge or head>`.
2. List what changed in the code: endpoints, request/response fields, error codes, events/topics, cache keys, env vars,
   migrations, new libraries, new units.
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
On PASS, set the tracker rows of the change's stories to Status `documented`.
Show the doc diff summary and the judge verdict. Ask before commit, push and opening a docs PR — show the exact message
first and wait for a yes. Never commit to the base branch directly.
