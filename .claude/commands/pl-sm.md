---
description: Plumbline — daily sprint health report (stuck, blocked, unassigned, Definition of Done, velocity) from JIRA, checked by an independent judge
argument-hint: "[empty for the daily report, or a story key for one ticket]"
---

# /pl-sm

The daily sprint check: what is done, in review, in progress, blocked, at risk or unassigned; whether in-review
tickets meet the Definition of Done; velocity. A **writer** subagent writes the report from the sprint data; an
independent **judge** checks every list and number against that data. Up to 3 attempts, then it is handed to the
user. Comments are posted to JIRA only after the user says yes.

Target: $ARGUMENTS (empty = the whole active sprint; a key = that ticket only)

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-sm-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-sm-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself. **Shell:** run no `git` (the code is already in this folder; only `/pl-dev` and `/pl-code-review` use git); read PRs with the git host's connector (GitHub, GitLab or Bitbucket). Do not research the code yourself — that is the
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

## Metrics mode
**`/pl-sm metrics`** — instead of the sprint report, read the footers of the sprint's `[Plumbline /pl-*]` comments in
JIRA and show one table per command: runs, median attempts, median minutes, PASS rate, and how often the SME edited the
text (older footers have no minutes — show "unknown"). Numbers only from JIRA; no judge needed. Stop after the table.

## Step 1 — Sprint data
With the connected JIRA/Atlassian tools, fetch the data as below. Without them, ask the user for an export of the
sprint's issues (JIRA "Export → CSV" or JSON, plus last sprint's Done count) and use that as the source instead.
1. JIRA project from the root `CLAUDE.md` Plumbline settings. Fetch the active sprint's issues (JQL
   `project = <KEY> AND sprint in openSprints()`): key, summary, status, assignee, updated, story points, labels,
   blocked-by links, whether the description has acceptance criteria. Also the previous sprint's Done count.
2. For each In Review ticket, its PR state: human approval, `/pl-code-review` result, CI status, merged
   (the git host's connector (GitHub, GitLab or Bitbucket)).
3. Write all of it, **unedited**, with today's date, to `.plumbline-drafts/sprint-<name>/facts.md` — make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it
   keeps the folder out of git without touching `.git/`). This file is the single source of truth.

**Stop and ask the user** if: JIRA returns an error; more than one sprint is open; a blocked-by chain is circular.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-sm-writer` with: the facts path, the report path
   `.plumbline-drafts/sprint-<name>/standup.md`; on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the standup path and the facts path; *Checklist:* the
   **Sprint report checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

### Sprint report checklist
1. Sections present: Done, In review, In progress, Blocked, At risk, Unassigned, Velocity, Flags for action, Comments.
2. Each list contains exactly the tickets the facts imply — recompute from the facts file: at risk = In Progress with
   no update for more than 2 days; needs attention = In Review for more than 1 day; blocked = a blocker that is not
   Done; unassigned = To Do with no assignee; no acceptance criteria flagged.
3. Velocity numbers equal the facts (this sprint's Done count and points, last sprint's count, trend).
4. Definition of Done is checked for every In Review ticket: acceptance criteria tested (QA passed), PR approved by a
   human, code review passed on the current commit, CI green, merged — each item marked from the facts.
5. Every flagged ticket says why and who must act; risks are ordered by impact on the sprint goal.
6. Comments to post are factual — no blame, no guesses presented as facts — and nothing contradicts the facts file.
7. Status and labels agree: Done without `plumbline-qa-passed`; a merged PR without `plumbline-docs-ready`; In Review
   with no `[Plumbline /pl-dev]` comment — each flagged ("status ≠ labels").

## Step 3 — Hand over
Show the report. Ask before posting: the report (e.g. as a comment on the sprint's tracking issue or a Confluence
page) and the per-ticket comments, one per flagged ticket on `sm-flag.md` — show the exact text first and wait for a yes. Never move or close a ticket whose
Definition of Done is not met.
