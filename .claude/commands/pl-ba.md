---
description: Plumbline — split an epic or requirement into ready-to-build stories with testable acceptance criteria, each checked by an independent judge
argument-hint: "<epic key, e.g. CRS-40, or a requirement in plain English>"
---

# /pl-ba

Turn an approved epic (or a requirement) into user stories that a developer — human or agent — can build without
guessing: user story, testable acceptance criteria, scope, constraints, test data, points. A **writer** subagent drafts
each story; an independent **judge** checks it. Up to 3 attempts per story, then it is handed to the user. Stories are
created in JIRA only after the user says yes.

Input: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-ba-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-ba-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
only `git` (from the repository root — never `git -C`, which permission rules do not match) yourself; read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.
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

## Drafts
Drafts go in `.plumbline-drafts/<KEY or slug>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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

## Step 1 — Input
- An epic key: fetch it (and its PRD, from the description or a linked Confluence page) with the connected
  JIRA/Atlassian tools. The epic should carry `plumbline-prd-approved`; if not, tell the user and ask whether to go on.
- Plain English: use it and continue. BA never creates epics: the stories are created without a parent unless the
  user names an epic at the hand-over (suggest `/pl-pm` for a new epic).
- No JIRA tools: ask the user to paste the epic/PRD.

Read the root `CLAUDE.md` and the CLAUDE.md of each unit involved. Split the work into stories, each inside **one
unit**. Show the list (title, unit, rough size) and continue.

**Settle shared decisions once, before any story is written:** the branch pattern, the PR target branch and the JIRA
key format. Take them from the root CLAUDE.md Plumbline settings; if the CLAUDE.md files disagree with each other,
ask the user which applies (unattended: use the Plumbline settings and say so). Give the same values to every writer —
stories must never disagree with each other on these.

**Stop and ask the user** if: a story needs another unit's database directly; it needs a unit that does not exist;
it is in the root CLAUDE.md out-of-scope list; or you cannot tell which unit owns a concept.

## Step 2 — Each story, attempts (1, 2, 3)
1. **Writer** — start `plumbline-ba-writer` with: the requirement/PRD, the story title and unit, the CLAUDE.md paths,
   the shared decisions (branch pattern, PR target, key format), the draft path `.plumbline-drafts/<KEY>/story-<n>.md`; on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the story path, the CLAUDE.md paths and the unit folder;
   *Checklist:* the **Story checklist** below, verbatim. PASS → next story. FAIL → next attempt.

After 3 failed attempts: mark the story ESCALATED with its last findings and move on. Points of 13+ after attempt 3
means the story must be split — say so.

### Story checklist
1. User story is "As a <specific role> / I want / So that".
2. Acceptance criteria are numbered `AC1`, `AC2`, … and each is testable on its own: for an API — method, path, expected status, and the field and
   value checked; for UI — the screen, the action, and what the user sees.
3. The criteria cover the happy path, not-found, and invalid input (where they apply).
4. The story stays inside one unit; any call to another unit uses that unit's existing API (check it exists).
5. Points are one of 1 / 2 / 3 / 5 / 8.
6. Blocked-by is named, or explicitly "None".
7. Nothing from the root CLAUDE.md out-of-scope list.
8. Tech constraints: unit, port, branch pattern, PR target and "read CLAUDE.md first" are stated, and the branch
   pattern and PR target are exactly the shared decisions given in the request.
9. Test data is named: an existing table/fixture/seed (check it exists) or synthetic values.
10. Every endpoint, table or field the story says exists today is in the CLAUDE.md files (section named) or in a file
    the story cites — nothing taken on trust from memory.

## Step 3 — Hand over
Show a table: story · unit · points · result. For each passed story, show its Definition of Ready (items 1–10 checked)
and ask before creating it in JIRA under the epic with label `plumbline-dor-ready` and its blocked-by links — show the
exact content first and wait for a yes.
**Writing to JIRA (once approved):** create each story with its epic as `parent`; put the points in the project's
story-points field (team-managed projects: `customfield_10016`, "Story point estimate" — check the issue-type fields if
unsure); write acceptance criteria as plain `-` bullets (markdown `- [ ]` arrives as literal text); then add one
`Blocks` link per blocked-by. Read one created issue back to confirm parent, points and labels were saved.
