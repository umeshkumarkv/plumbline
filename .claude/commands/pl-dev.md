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
only `git` and the project's build/test command yourself (they work in bash, PowerShell and cmd alike); find and read
files with your file search/read tools — never `find`, `grep`, `ls`, `cat`.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue.

## Step 1 — The story
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
1. **Writer** — start `plumbline-dev-writer` with: the story, the branch, the units and their CLAUDE.md paths, the
   build/test command; on attempts 2–3 also the previous findings and build output.
2. **Build/tests** — run the build/test command yourself. A failure that is not in the baseline → that is the finding;
   next attempt. Pre-existing failures do not count; say so in the hand-over.
3. **Scope check** — run `git diff --name-only <base branch>` and `git status --porcelain`. Fail if anything under
   `.claude/`, `.github/`, any `CLAUDE.md`/`AGENTS.md`, or CI/build settings that skip tests changed, or if an
   existing test was deleted. → next attempt with that as the finding.
4. **Judge** — start `plumbline-judge` with exactly:
   - *Review:* "the change on this branch: `git diff <base branch>`", the story and acceptance criteria, the
     CLAUDE.md paths;
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

## Step 4 — Hand over
Show: the acceptance criteria → tests table, files changed, build result, judge verdict. Then ask before each of:
commit, push, open PR, comment on the JIRA issue — show the exact message/text first and wait for a yes.
