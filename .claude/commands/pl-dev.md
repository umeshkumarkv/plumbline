---
description: Plumbline — implement a story with tests; checked by the build, a scope check and an independent judge
argument-hint: "<JIRA key, e.g. CRS-12, or a short story description>"
---

# /pl-dev

Implement one story on a new branch. A **writer** subagent makes the change; then three checks: the project's
**build/tests**, a **scope check** (only allowed files changed), and an independent **judge**. Up to 3 attempts, then
it is handed to the user. Nothing is committed, pushed or posted without the user's yes.

Story: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-dev-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with agent `plumbline-dev-writer` or `plumbline-judge` (`.github/agents/`).
  If subagents are not available in this chat, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
only `git` (from the repository root — never `git -C`, which permission rules do not match) and the project's build/test command yourself (they work in bash, PowerShell and cmd alike); find and read
files with your file search/read tools — never `find`, `grep`, `ls`, `cat`.
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
`date,command,target,attempts,verdict,tests_run,minutes,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, the
minutes from start to hand-over (run `date +%s` once at the start and once at the hand-over), and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft, tracker and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — The story
- Several keys (`CRS-301 CRS-302`): implement them in that order on one branch; everything below applies to each.
- Look each story up in the feature tracker: use its story file and **design file**. No design → say so and ask
  whether to run `/pl-arch` first; continue without one only if the user agrees.
- A JIRA key: fetch the issue with the connected JIRA/Atlassian tools (summary, description, acceptance criteria). If
  no JIRA tools are connected, ask the user to paste the story.
- A description: use it; ask for acceptance criteria if there are none.
- No acceptance criteria at all → stop and ask. Do not invent them.

## Step 2 — Prepare
1. Read the root `CLAUDE.md` (Plumbline settings: base branch) and pick the units the story touches; read their
   CLAUDE.md files. No CLAUDE.md yet → suggest `/pl-onboard` first, then continue if the user agrees.
2. Build/test command: from the units' CLAUDE.md "Build & run" (on Windows use the `.cmd` wrapper, e.g. `mvnw.cmd`).
3. `git status` must be clean. Create the branch: `git switch -c ai/<KEY>-<short-slug> <base branch>`.
4. **Baseline:** run the build/test command once before any change and keep the result. If it already fails, note
   which tests or which step fail — those are pre-existing and do not count against the story. If the test runner
   cannot run at all, tell the user now and continue: the story's tests are still written, and the judge checks them by
   reading.

## Step 3 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-dev-writer` with: the story, the design path(s), the branch, the units and their
   CLAUDE.md paths, the build/test command; on attempts 2–3 also the previous findings and build output.
2. **Build/tests** — run the build/test command yourself. A failure that is not in the baseline → that is the finding;
   next attempt. Pre-existing failures do not count; say so in the hand-over.
3. **Scope check** — run `git diff --name-only <base branch>` and `git status --porcelain`. Fail if anything under
   `.claude/`, `.github/`, any `CLAUDE.md`/`AGENTS.md`, or CI/build settings that skip tests changed, or if an
   existing test was deleted. → next attempt with that as the finding.
4. **Judge** — start `plumbline-judge` with exactly:
   - *Review:* "the change on this branch: `git diff <base branch>`", the story and acceptance criteria, the design
     path(s), the CLAUDE.md paths;
   - *Checklist:* the **Dev checklist** below, verbatim.
   PASS → Step 4. FAIL → next attempt with the findings.

After 3 failed attempts: stop, show the last findings and the branch, and hand over to the user.

### Dev checklist
1. Each acceptance criterion is implemented, and has a test that would fail without the change (name the test).
2. The change follows the rules and Must-never items in the root and unit CLAUDE.md files.
3. No test was deleted, skipped or weakened to pass; no check was switched off.
4. Inputs are validated; no secrets in code or logs; no SQL/command built by string concatenation; errors do not
   leak internals.
5. Only the code the story needs changed; nothing unrelated.
6. Any API or schema change is backward compatible, or the story says it may break — and callers in other units are
   updated or listed.
7. Every test the design's Tests section lists exists in the diff — answer as a list `design item → test name`. A
   missing one fails this item, unless the story itself moves it to another named story.
8. The change follows the design (endpoints, order of checks, error codes, files); any deviation is named and
   justified in a code comment or the hand-over.

## Step 4 — Hand over
**If the build/test command could not run** (or ran only for some units), the first line of the hand-over is:
**UNVERIFIED — the tests were written but not run (<reason>). Run `<command>` before merging.** Never call such work
"tested". Set the tracker rows: Branch, Status `built` (tests ran and passed) or `built, tests not run`.

Show: the acceptance criteria → tests table, the design → tests table, files changed, build result, judge verdict. Then ask before each of:
commit, push, open PR, comment on the JIRA issue — show the exact message/text first and wait for a yes.
