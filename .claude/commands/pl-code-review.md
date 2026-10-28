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

## JIRA hand-off
Roles pass work to each other only through JIRA — never through files on someone's machine — so no agent works out
again what an earlier role settled. The person running a command is that role's SME; their yes at the hand-over is the
approval.

| Step | Lives in JIRA as | Template | Approval label (added on the SME's yes) |
|---|---|---|---|
| `/pl-pm` | epic — the PRD in its description | `epic.md`, `prd.md` | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — criteria, points, `Blocks` links | `story.md` | `plumbline-dor-ready` |
| `/pl-arch` | comment on the story — the design | `handoff-arch.md`, `design.md` | `plumbline-arch-approved` |
| `/pl-dev` | comment on the story — branch, PR, test result | `handoff-dev.md` | — (the PR is reviewed next) |
| `/pl-code-review` | PR review + comment on the story — verdict and findings | `handoff-review.md` | `plumbline-review-passed` |
| `/pl-qa` | comment on the story — evidence per criterion | `handoff-qa.md` | `plumbline-qa-passed` |
| `/pl-doc` | docs PR updating CLAUDE.md + comment on the story | `handoff-doc.md` | the architect approves the docs PR |
| `/pl-devops`, `/pl-sm` | comment on the story / sprint issue | `handoff-devops.md`, `sprint-report.md` | — |

- **Input:** read the ticket — description, labels, links, and the latest comment of each kind that starts
  `[Plumbline /pl-<role>]`. Do not redo an earlier role's work; if it is wrong, stop and say which role must fix it.
- **Gate:** start only when the previous step's label is on the ticket. Missing → `STOPPED: <label> not on <KEY>`
  (the SME adds it, or tells you to go on).
- **Output:** post it as the table says, starting `[Plumbline /pl-<role>] <date>`, and add the label — both only
  after the SME's yes, with the exact text shown first.
- `.plumbline-drafts/` is scratch before posting; no other command reads it. No JIRA tools connected → give the
  output as text for the SME to paste, and say the hand-off is manual.

## Metrics
At the hand-over, append one line to `.plumbline-drafts/metrics.csv` (create it with the header
`date,command,target,attempts,verdict,tests_run,minutes,human_decision` if missing): today's date, this command, the
story/branch/PR, attempts used, the final verdict, `yes`/`no`/`n/a` for whether the build/tests ran, the
minutes from start to hand-over (run `date +%s` once at the start and once at the hand-over), and leave
`human_decision` empty. When the user answers the hand-over question, fill it in: `approved`, `edited`, or `rejected`.
The file stays on this machine (`.plumbline-drafts/.gitignore` holds `*`); `/pl-sm` can summarise it.
**Files:** create every draft and metrics file with your write tool — it creates missing folders. Never
`mkdir`, `echo`, `printf` or redirection: permission settings block them.

## Step 1 — What to review
- Base branch: from the root `CLAUDE.md` Plumbline settings (else the repository's default branch).
- A PR number: `git fetch origin pull/<n>/head:pr-<n>` and review `pr-<n>`; or use the connected GitHub tools to read
  the PR. A branch: review it against the base. Empty: the current branch.
- The diff to review: `git diff <base>...<branch>`. Empty diff → say so and stop.
- The rulebook: the root `CLAUDE.md` and the CLAUDE.md of every unit the diff touches.
- **Scope:** the story keys in the branch name, PR title or the stories' `[Plumbline /pl-dev]` comments — use **all**
  of them. From JIRA take each story's criteria and its latest `[Plumbline /pl-arch]` design comment, and save them in
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
with the verdict on each story in scope; on PASS, add `plumbline-review-passed` to those stories. Never approve or
merge.
