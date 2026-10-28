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
- **Judge replies:** only the judge's JSON counts. Not JSON → ask that judge once more, then count the attempt as FAIL
  ("judge reply unreadable"). Never decide PASS yourself or drop a finding before the next attempt.
- **Project memory:** helpers work from the CLAUDE.md files (kept current by `/pl-doc`) and the JIRA/Confluence
  material, opening code only for what they change or review; never research the code yourself. List their "Add to
  CLAUDE.md" / "CLAUDE.md out of date" notes in the hand-over for `/pl-doc`.
- **Freshness:** for each unit CLAUDE.md a helper gets, run `git log --oneline <its Last updated commit>..HEAD --
  <unit folder>`. Commits listed → tell the helpers and the judge "CLAUDE.md may be stale for: <files those commits
  changed>", and say so in the hand-over.
- **Templates:** what will be posted is written on its template (JIRA hand-off table; `.github/plumbline/templates/`).
  Give each writer the template, the version (`.github/plumbline/VERSION`), `git rev-parse --short HEAD` and `Run by`
  (the connected Atlassian user). Before each judge and before posting, run `bash .github/plumbline/check-template.sh
  <template> <draft>`: FAIL = that attempt's finding, no judge. No bash here → the judge checks the headings instead.
- **Limits:** at most 3 attempts per item, one writer and one judge each. More than 6 items → show the list and ask;
  nobody to answer → do the first 6 and list the rest.
- **Nobody to answer** (scheduled/headless): where a step says ask, take its safe choice or stop that item — never
  guess; write nothing outside the repository and `.plumbline-drafts/`; list the unasked questions in the hand-over.
- **Hand-over:** first line `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what did not
  run>`; then the details; then each question for the user with the exact text or command it would send or run.

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
At the hand-over append to `.plumbline-drafts/metrics.csv` (header, if new:
`date,command,target,attempts,verdict,tests_run,minutes,human_decision`): date, command, story/branch/PR, attempts,
verdict, tests ran `yes`/`no`/`n/a`, minutes (`date +%s` at start and at hand-over), and `human_decision` once the user
answers: `approved`, `edited` or `rejected`. It stays local; `/pl-sm metrics` summarises it.
**Files:** create drafts and metrics with your write tool (it creates folders) — never `mkdir`, `echo`, `printf` or
redirection, which permission settings block.

## Step 1 — The story
- Several keys (`CRS-301 CRS-302`): implement them in that order on one branch; everything below applies to each.
- A JIRA key: read the story (summary, description, acceptance criteria), its latest `[Plumbline /pl-arch]` comment
  and the design page it links (at that version) with the connected JIRA/Atlassian tools, and save both in `.plumbline-drafts/<KEY>/` for this run's
  writer and judge. No `plumbline-arch-approved` label → `STOPPED` (see JIRA hand-off). No JIRA tools → ask the user to
  paste the story and the design.
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
"tested".

Show: the acceptance criteria → tests table, the design → tests table, files changed, build result, judge verdict. Then ask before each of:
commit, push, open PR, and the JIRA comment `[Plumbline /pl-dev] <date>` with the branch, the PR link, the test result
(or UNVERIFIED) and any "Add to CLAUDE.md" notes — show the exact message/text first and wait for a yes.
