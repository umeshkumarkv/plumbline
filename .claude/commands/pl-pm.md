---
description: Plumbline — turn a feature idea into a PRD (and, with your yes, a JIRA epic), checked by an independent judge
argument-hint: "<feature idea in plain English>"
---

# /pl-pm

Turn a feature idea into a PRD: problem, solution, success criteria, scope, dependencies, prioritised backlog. A
**writer** subagent drafts it; an independent **judge** checks it. Up to 3 attempts, then it is handed to the user.
The epic is created in JIRA only after the user says yes.

Idea: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-pm-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-pm-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
no `git` (the code is already in this folder; only `/pl-dev` and `/pl-code-review` use git); read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.
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
Drafts go in `.plumbline-drafts/<slug>/` at the repository root (slug = a short kebab-case name for the idea). Before
the first draft, make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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

## Step 1 — Context
Read the root `CLAUDE.md` (solution, out-of-scope list, rules, Plumbline settings); the writer may read unit CLAUDE.md
files and code to learn what exists today, but writes business language only. If the idea is empty or too vague to name who has the problem, ask one question.

**Stop and ask the user** if: the idea is entirely in the out-of-scope list; it contradicts a rule in the root CLAUDE.md; or existing epics already cover part of it (if JIRA tools
are connected, search for them).

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-pm-writer` with: the idea, the CLAUDE.md paths, the draft path
   `.plumbline-drafts/<slug>/prd.md`; on attempts 2–3 also the judge's findings (verbatim JSON).
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the PRD path and the root CLAUDE.md (writer: `plumbline-pm-writer`); *Checklist:* the
   **PRD checklist** below, verbatim. PASS → Step 3. FAIL → next attempt with the findings.

After 3 failed attempts: stop, show the last findings and the draft, and hand over to the user.

### PRD checklist
1. Every section of the template has real content (`None` is fine only for Open questions and Dependencies).
2. Problem names a specific business role, what they cannot do today, and the business impact.
3. *Today* says what users can and cannot do now (business terms); Solution describes, in business language, what users will be able to do and see — enough for a BA to write stories.
4. At least 2 success criteria, each observable by a user or measurable in the business.
5. Out of scope is explicit and refers to the root CLAUDE.md out-of-scope list where it applies.
6. No technical design: no APIs, status codes, services or units, data model, classes or points (that is `/pl-arch`).
7. Dependencies are named, or explicitly "None".
8. Nothing from the root CLAUDE.md out-of-scope list appears in P1, P2 or P3.
9. Every backlog item has a size S / M / L, and P1 has no L.
10. No placeholders (`{…}`, TBD, TODO) left.

## Step 3 — Hand over
Show the PRD. Then ask before each, in this order (exact content first, then a yes): (1) create the epic in JIRA
(Plumbline settings: JIRA project) with the title; (2) publish the PRD as a Confluence page `<EPIC> — <title> — PRD`
under the `Confluence parent page` — the key is in the title from the start, so the page is never renamed; (3) set the
epic's description on `epic.md` with the page link and its version; (4) add `plumbline-prd-approved`. No Confluence →
the full PRD goes in the epic description.
