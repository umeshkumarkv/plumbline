---
description: Plumbline — run a story's acceptance criteria against the running system and record the evidence; checked by an independent judge
argument-hint: "<story key, e.g. CRS-12>"
---

# /pl-qa

Test one story's acceptance criteria against the **running** system — API calls and, for UI criteria, Playwright — and
record the evidence. A **runner** subagent executes the tests; an independent **judge** checks the evidence actually
proves each criterion. Up to 3 attempts, then it is handed to the user. QA reports what it observed; it never fixes or
diagnoses code.

Story: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-qa-runner` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-qa-runner` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the runner's or the judge's work yourself. **Shell:** run no `git` (the code is already in this folder; only `/pl-dev` and `/pl-code-review` use git); only
`curl` (`curl.exe` on Windows) for the health check and the start commands the user approves in Step 1. Do not research the code yourself — that is the
writer's/runner's and the judge's job; you route, check scope and hand over.
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
Evidence goes in `.plumbline-drafts/<KEY>/qa/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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

## Step 1 — Setup
1. Read the story (business acceptance criteria) and the *Acceptance criteria → design* section of its latest
   `[Plumbline /pl-arch]` comment — the technical check for each AC — and save both as `.plumbline-drafts/<KEY>/story.md`. Under test: the merged code the pipeline deployed to the QA region.
2. **Gate:** `plumbline-deployed-qa` on the story (see JIRA hand-off); checked as the JIRA hand-off Gate says.
3. **Environment.** The QA URL and deployed commit from the latest `[Plumbline /pl-devops]` deploy comment (else the
   Plumbline settings); ask if missing. Check
   each answers with exactly `curl -s -o /dev/null -m 5 -w "%{http_code}" <url>` (any HTTP status means it is up; `000`
   means it is not). If not, offer:
   - **(a) start it here** — show the exact run command of each unit from its CLAUDE.md "Build & run" (with the
     base branch pulled) and wait for a yes. Start each in the background, poll the URL for up to 3
     minutes, and stop what you started at the end of the run;
   - **(b) use another environment** — the user gives a staging/test URL; use it for this run only;
   - **(c) stop** — report "QA not run: system not reachable at <url>". Never mark a criterion PASS or FAIL without
     having run it.
   When nobody can answer (an unattended run), take (c).
4. Credentials come **only** from environment variables (`PLUMBLINE_DEMO_USER`, `PLUMBLINE_DEMO_PASSWORD`, or what the
   CLAUDE.md names). Never write a password or token into a file, a report or a comment.
5. Classify each criterion: **API** (status/body), **UI** (what the user sees), or **BOTH** (a submit flow); and
   **WRITES** (creates/changes data) or **READS**. Show the table and write it to `.plumbline-drafts/<KEY>/qa/plan.md`.

## Step 2 — Attempts (1, 2, 3)
1. **Runner** — start `plumbline-qa-runner` with: the plan path, the story path, the URLs, the names of the credential
   environment variables, the evidence path `.plumbline-drafts/<KEY>/qa/evidence.md`; on attempts 2–3 the judge's
   findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the evidence path, the plan and story paths;
   *Checklist:* the **QA evidence checklist** below, verbatim.
3. PASS (every criterion passed, judge PASS) → Step 3. Judge FAIL (evidence does not prove the criteria) → next
   attempt. A criterion that genuinely **fails** is not retried away: it is the result — go to Step 3 with it.

### QA evidence checklist
1. Every criterion has a result (PASS / FAIL) with the exact request or UI steps, the expected and the actual outcome.
2. Each PASS is proven by checking the field and value the criterion names, not only the status code.
3. Writes: the evidence shows the data really changed (a follow-up read, or the database/event when the plan has
   access).
4. Standard edge cases were run where they apply: unknown id → 404, no credentials → 401/redirect, invalid input →
   400/422, response format as the CLAUDE.md files describe.
5. UI checks assert the behaviour the criterion describes, not just that an element exists.
6. Nothing was skipped without a stated infrastructure reason; no password or token appears in the evidence.
7. Failures are reported as observed (request, expected, actual, body) — no guesses at the cause.

## Step 3 — Hand over
Show: criterion · type · result. For each failure, exactly four fields: request/steps · expected · actual · response
body. If a failure looks like a design problem (wrong owner field, role, missing header), say "design gap — run
`/pl-arch <KEY>`" and nothing more. Ask before posting the report as a JIRA comment (`[Plumbline /pl-qa] <date>`), `plumbline-qa-passed` and **Done** when every criterion
passed (the epic too, with its last story); a failure → In Progress, for a fix PR — exact text first, then a yes.
