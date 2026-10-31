---
description: Plumbline — on an open PR, write the exact API-spec and CLAUDE.md text the change needs and post it for dev to apply, checked by an independent judge
argument-hint: "<story key or PR number>"
---

# /pl-doc

Before review, bring the documentation in line with an open PR: the API spec (e.g. `openapi.yaml`) and the CLAUDE.md
files of the units it touches. A **writer** drafts the exact new text; an independent **judge** checks every change in
the code is reflected. The text is posted on the PR and the story; **dev applies it word for word in the same PR**, so
code and docs are reviewed and merged together. Up to 3 attempts. Docs only — never code, never git.

Change: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-doc-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-doc-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself. **Shell:** run no `git` (the code is already in this folder; only `/pl-dev` and `/pl-code-review` use git); read the merged PR with the git host's connector (GitHub, GitLab or Bitbucket). Do not research the code yourself — that is the
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

## Step 1 — The change
1. Find the open PR: a story key → the PR in its `[Plumbline /pl-dev]` comment (gate: that comment exists); a PR number
   → its story key from the PR title or branch. Read the PR's diff and changed files with the git host's connector
   (no connector → ask the user to paste the diff), and save it as `.plumbline-drafts/doc-<KEY>/change.diff`.
2. List what changed in the code: endpoints, request/response fields, error codes, events/topics, cache keys, env vars,
   migrations, new libraries, new units. From the story's JIRA ticket also take: the **durable** business rules its
   acceptance criteria add — constraints every later change must keep, not display details (→ Rules, tagged
   `[decided <KEY>]`), the *Decisions* in its latest `[Plumbline /pl-arch]` comment (→ Decisions & trade-offs), and every
   "Add to CLAUDE.md" / "CLAUDE.md out of date" note in its `[Plumbline …]` comments.
3. Copy the current CLAUDE.md files and API spec the change touches (from your clone, base branch pulled) into
   `.plumbline-drafts/doc-<KEY>/before/` and again into `…/after/` — the writer edits only the `after/` copies.

**Stop and ask the user** if: the change adds a new unit or a new cross-unit event (the root CLAUDE.md needs a human
decision first); the code contradicts the existing API spec in a way that needs an architecture call; or a new
library arrived without the root CLAUDE.md allowing it.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-doc-writer` with: `change.diff`, the list from Step 1, the `after/` copies it may edit
   (API spec; the touched units' CLAUDE.md and CLAUDE.reference.md; the root only if the architecture changed); on
   attempts 2–3 the judge's findings.
2. **Scope check** — the writer lists every file it changed: only files under `after/`. Anything else → finding.
3. **Judge** — start `plumbline-judge` with exactly: *Review:* `change.diff`, the `after/` files and their `before/`
   copies; *Checklist:* the **Doc checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

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
9. New Rules are durable constraints tagged `[decided <KEY>]`; no `[decided]` rule was removed; each core CLAUDE.md
   is at most 6 KB and each reference file at most 30 KB, with the core's Reference counts still right.

## Step 3 — Hand over
Write `handoff-doc.md`: for each changed file, its path, the section, and the exact new text from `after/` (set
`Last updated: — (<date>, /pl-doc, <template> v<N>)` in each CLAUDE.md). Show it with each file's size before → after,
any *Proposed removals*, and the judge verdict. On the SME's yes (JIRA hand-off: Output), post the same text as a PR
comment and as the story comment, and add `plumbline-docs-ready`. Next: dev applies it word for word
(`/pl-dev <KEY>`), then `/pl-code-review`. The architect approves the CLAUDE.md part when the PR is merged.
