---
description: Plumbline — after a merge, confirm the pipeline deployed to QA; on a failing CI run, diagnose it and post the fix for dev, checked by an independent judge
argument-hint: "<story key after merge, or PR/branch with a failing CI run>"
---

# /pl-devops

Two jobs, never git: **Deploy** — a story key whose PR is merged: the CI/CD pipeline deploys; you confirm it reached
the QA region and tell QA. **CI fix** — a failing run on an open PR: a **fixer** classifies it and fixes it in your clone
(compile error, failing test, coverage) or writes a diagnosis (pipeline, container, migration, dependency, secrets); an
independent **judge** checks it weakens nothing; the fix is posted as exact text for dev to apply. Up to 3 attempts.

## Deploy (a story key whose PR is merged)
1. Gate: `plumbline-review-passed`, PR merged. Find the pipeline run for the merge commit with the git host's connector
   and wait for it (no connector → ask the user for the run's result and log).
2. Success → check the QA URL (Plumbline settings) answers: `curl -s -o /dev/null -m 5 -w "%{http_code}" <url>`
   (`curl.exe` on Windows). Write `handoff-deploy.md` (run, deployed commit, URL, result) and, on the SME's yes, post it
   on the story and add `plumbline-deployed-qa`. Next: `/pl-qa <KEY>`.
3. Failure → save the log to `.plumbline-drafts/deploy-<KEY>/ci.log`, run the **CI fix** steps below on the base branch
   for a diagnosis and fix text, and post `handoff-deploy.md` with *Failure* filled: dev opens a fix PR. No label.

Target: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-devops-fixer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-devops-fixer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the fixer's or the judge's work yourself. **Shell:** run no `git` (the code is already in this folder; only `/pl-dev` and `/pl-code-review` use git); only the project's build/test
command and, for Deploy, `curl` yourself. Read CI runs with the git host's connector (GitHub, GitLab or Bitbucket), or the log the user pastes. Do not research the code yourself — the fixer and the judge do; you route,
check scope and hand over.
If a helper replies with `FILE: <path>` and the content instead of writing the file, save that content to the path
unchanged, then continue — but only for a path you gave that helper; any other path is a FAIL finding, not a write.

## Every run
- **Judge replies:** only the judge's JSON counts. Not JSON → ask that judge once more, then count the attempt as FAIL
  ("judge reply unreadable"). Never decide PASS yourself or drop a finding before the next attempt.
- **Project memory:** no root `CLAUDE.md` → `STOPPED: run /pl-onboard first` (only `/pl-onboard` runs without one).
  Helpers work from the CLAUDE.md files (kept current by `/pl-doc`) and the JIRA/Confluence
  material, opening code only for what they change or review; never research the code yourself. List their "Add to
  CLAUDE.md" / "CLAUDE.md out of date" notes in the hand-over for `/pl-doc`.
- **Templates and lanes:** everything that leaves this machine — JIRA, Confluence, PR descriptions and reviews — and
  every CLAUDE.md file is written on its template in `.github/plumbline/templates/` (`claude-root.md`,
  `claude-unit.md`, `claude-reference.md` for those files; the JIRA hand-off table for the rest), and names the
  template's version. Give each writer the template, the version (`.github/plumbline/VERSION.md`) and the
  commit (`/pl-dev`, `/pl-code-review`: `git rev-parse --short HEAD`; every other command: `—`); tell the judge the writer's agent name, so it checks that agent's *Your lane*. Before
  each judge and before posting, do the **Template check** in `.github/plumbline/templates/README.md` yourself (it
  also catches text outside the lane): any miss is that attempt's finding, no judge. Fill the footer's `judge`, minutes and
  `SME edited`.
- **Limits:** at most 3 attempts per item, one writer and one judge each. More than 6 items → show the list and ask;
  nobody to answer → do the first 6 and list the rest.
- **Nobody to answer** (scheduled/headless): where a step says ask, take its safe choice or stop that item — never
  guess; write nothing outside the repository and `.plumbline-drafts/`; list the unasked questions in the hand-over.
- **Hand-over:** first line `PASS` · `FAIL after 3 attempts` · `STOPPED: <reason>` · `UNVERIFIED: <what did not
  run>`; then the details; then each question for the user with the exact text or command it would send or run.

## Drafts
Logs and diagnoses go in `.plumbline-drafts/ci-<branch>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

## JIRA hand-off
Roles pass work to each other only through JIRA, Confluence and the PR (or MR) — never through files on someone's
machine; every person works in their own clone (OPERATING-MODEL.md). The PRD and each epic's HLD are Confluence pages
under the `Confluence parent page` (Plumbline settings), linked from the epic; every other hand-off is a ticket, a
comment, or a PR comment. Only `/pl-dev` and `/pl-code-review` use git.

| Step | Posts | Template | Label added on the SME's yes |
|---|---|---|---|
| `/pl-pm` | PRD page; the epic, with summary + PRD link | `prd.md`, `epic.md` | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — business criteria | `story.md` | `plumbline-dor-ready` |
| `/pl-arch <EPIC>` | HLD page under the PRD; epic comment with its link and the CLAUDE.md text for dev | `hld.md`, `handoff-hld.md` | `plumbline-hld-final` |
| `/pl-arch <STORY>` | story comment — the LLD; story points set | `handoff-arch.md` | `plumbline-arch-approved` |
| `/pl-dev` | branch + PR; story comment; later applies doc's text to the PR | `pr.md`, `handoff-dev.md` | — |
| `/pl-doc` | the same text as a PR comment and a story comment — exact docs text per file | `handoff-doc.md` | `plumbline-docs-ready` |
| `/pl-code-review` | the same text as the PR review and a story comment — code and docs | `handoff-review.md` | `plumbline-review-passed` |
| merge | a person merges (branch protection; the architect approves CLAUDE.md files) | — | — |
| `/pl-devops` | after merge: story comment — pipeline, deployed commit, QA URL; on a PR's CI failure: the fix | `handoff-deploy.md`, `handoff-devops.md` | `plumbline-deployed-qa` |
| `/pl-qa` | story comment — evidence per criterion | `handoff-qa.md` | `plumbline-qa-passed` |
| `/pl-sm` | sprint report; one comment per flagged ticket; team metrics | `sprint-report.md`, `sm-flag.md` | — |

- **Input:** the ticket (description, labels, links), the latest `[Plumbline /pl-<role>]` comment of each kind (JIRA
  shows `\[Plumbline …\]`: ignore backslashes), and each PRD or HLD page they link at the version named.
- **Gate:** start only when the previous step's label is on the ticket (a story's LLD also needs `plumbline-hld-final`
  on its epic; doc needs the dev comment; QA needs `plumbline-deployed-qa`). A hand-off edited after it was posted
  (comment `updated` later than `created`; a page past its pinned version) → `STOPPED: <what> changed after approval`.
- **The architect's word is final:** later roles follow the HLD and LLD exactly. A role that cannot → `STOPPED:
  design gap — /pl-arch <KEY>`; never work around it. Do not redo an earlier role's work.
- **Output:** show the exact text, then ask: *"Your yes approves this as the <role> SME. JIRA will show you as the
  person who posted it."* On yes: post, add the label.
- **Status:** with that yes, move the ticket via JIRA's transitions to the `Workflow` statuses: `/pl-dev` → In Progress
  (epic too), then In Review with the PR; a review or QA FAIL → In Progress; `/pl-qa` PASS → Done (epic with its last
  story). Never force one. Review changes to the API or rules → run `/pl-doc` again on the same PR.
- No Confluence → the PRD goes in the epic description, the HLD in the epic comment. A comment stays under 30,000
  characters (JIRA's limit 32,767): longer → split. No JIRA tools → output as text to paste. Drafts are scratch.

## Metrics
Metrics live in JIRA, in the footer of every hand-off: judge result and attempts, minutes from start to hand-over
(`date +%s` at both — the one non-build command every command may run), and `SME edited: yes` if the SME changed the
text before posting. `/pl-sm metrics` reads them from JIRA, so the whole team sees the same numbers.
**Files:** before the first draft, create `.plumbline-drafts/.gitignore` containing `*` (drafts are your private
scratch, never committed). Create drafts with your write tool — never `mkdir`, `echo`, `printf` or redirection.

## Step 1 — The failure
1. Find the latest failed run for the PR/branch with the git host's connector and save the failing log to
   `.plumbline-drafts/ci-<branch>/ci.log`. No connector → ask the user to paste it.
2. The PR's branch must already be open in this folder (the user checks it out); copy the files the log points to into
   `.plumbline-drafts/ci-<branch>/before/`.
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
4. **Judge** — start `plumbline-judge` with exactly: *Review:* the files the fixer changed (it lists them) and their
   `before/` copies, the diagnosis/log paths; *Checklist:* the **Fix checklist** below, verbatim. FAIL → next attempt.
5. **CI** — on judge PASS, go to the hand-over. Once dev has pushed it, check the new run with the git host's
   connector; still red → `/pl-devops` again.

### Fix checklist
1. The fix addresses the root cause named in the classification, not a symptom.
2. No test, check, coverage threshold or scanner was skipped, disabled, deleted or loosened.
3. The change is minimal — nothing unrelated to the failure.
4. Business behaviour is unchanged unless the failure was a real bug in it (then say so).
5. No secret, credential or environment-specific value was added; the change can be reverted as one commit.

**Stop and ask the user** if: the fix needs business-logic changes beyond the failing case; a migration was already
applied to a shared environment; this branch caused several failure categories at once; the behaviour change looks
intended — a story or commit says so (the user decides whether code or test is right; a "refactor" or "tidy-up" did
not intend to change output, so the tests are right); or a fix produces a new failure category.

## Step 3 — Hand over
Show: category · cause · fix · local result · CI result · judge verdict. Write `handoff-devops.md` with the fix as
exact text per file (from your clone's changed files); on the SME's yes, post it as a PR comment and a story comment —
dev applies it and pushes. Then undo your local changes (they were only for the local check).
