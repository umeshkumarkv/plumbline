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

Do not review the change yourself first and do not pass your opinion to the judge. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not match), `bash .github/plumbline/check-template.sh` (and
`gh` if present) yourself; read files with your file read/search tools.

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
  `[Plumbline /pl-<role>]` or `[Plumbline approve /pl-<role>]`, and for an epic the PRD page it links, **at the version
  it names** (no version from the tools → compare last-modified times; neither → say so in the hand-over). A PRD page
  or hand-off comment changed after its approval → `STOPPED: <what> changed after approval`. Do not redo an earlier
  role's work; if it is wrong, say which role must fix it.
- **Gate:** start only when the previous step's label is on the ticket. With `Separate approver: yes` (the default)
  the approval must come from someone other than that step's `Run by`: a `[Plumbline approve /pl-<role>]` comment by
  them, else the issue's change history for the label. Otherwise stop: `STOPPED: <label> not on <KEY>` · `STOPPED:
  <KEY> self-approved by <name>` · `STOPPED: cannot verify who approved <KEY> — run /pl-approve`.
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first.
  `Run by` is the connected Atlassian user. `Separate approver: yes` → no label: `Approval: pending — /pl-approve
  <KEY> <role> by another person`. `no` → add the label after the yes; `Approval: self — <name> (<date>)`.
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

## Step 1 — What to review
- Base branch: from the root `CLAUDE.md` Plumbline settings (else the repository's default branch).
- A PR number: `git fetch origin pull/<n>/head:pr-<n>` and review `pr-<n>`; or use the connected GitHub tools to read
  the PR. A branch: review it against the base. Empty: the current branch.
- The diff to review: `git diff <base>...<branch>`. Empty diff → say so and stop.
- The rulebook: the root `CLAUDE.md` and the CLAUDE.md of every unit the diff touches.
- **Scope:** the story keys in the branch name, PR title or the stories' `[Plumbline /pl-dev]` comments — use **all**
  of them. From JIRA take each story's criteria and its latest `[Plumbline /pl-arch]` comment (the design), and save them in
  `.plumbline-drafts/review-<branch>/` for the judge. No story found → ask which stories it implements; no answer or no
  story → review against the CLAUDE.md files only and say so in the report.

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
Show the verdict and a table: severity · file:line · finding · fix. Then offer, each with the exact text and a yes:
post it as a PR review comment (connected GitHub tools or `gh pr review`); post `[Plumbline /pl-code-review] <date>`
with the verdict on each story in scope; on PASS, its approval label as the JIRA hand-off says (`plumbline-review-passed`). Never approve or
merge.
