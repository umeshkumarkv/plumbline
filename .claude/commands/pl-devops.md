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
unchanged, then continue — but only for a path you gave that helper; any other path is a FAIL finding, not a write.

## Every run
- **Judge replies:** the judge answers with the JSON its instructions give. If a reply is not that JSON, ask the same
  judge once to answer in that format; if it still does not, count the attempt as FAIL with the finding "judge reply
  unreadable". Never decide PASS yourself, and never edit or summarise away a finding before the next attempt.
- **Project memory:** the CLAUDE.md files are the single source of truth for the project, kept current after every
  merge by `/pl-doc`. Helpers work from them and from the JIRA ticket; they open code only for the files they change
  or review. Never research the code yourself. Collect what helpers report as "Add to CLAUDE.md" or "CLAUDE.md out
  of date" and list it in the hand-over for `/pl-doc`.
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
Logs and diagnoses go in `.plumbline-drafts/ci-<branch>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

## JIRA hand-off
Roles pass work to each other only through JIRA — never through files on someone's machine — so no agent works out
again what an earlier role settled. The person running a command is that role's SME; their yes at the hand-over is the
approval.

| Step | Lives in JIRA as | Approval label (added on the SME's yes) |
|---|---|---|
| `/pl-pm` | epic — the PRD in its description | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — criteria, points, `Blocks` links | `plumbline-dor-ready` |
| `/pl-arch` | comment on the story — the design | `plumbline-arch-approved` |
| `/pl-dev` | comment on the story — branch, PR, test result | — (the PR is reviewed next) |
| `/pl-code-review` | PR review + comment on the story — verdict and findings | `plumbline-review-passed` |
| `/pl-qa` | comment on the story — evidence per criterion | `plumbline-qa-passed` |
| `/pl-doc` | docs PR updating CLAUDE.md + comment on the story | the architect approves the docs PR |

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
