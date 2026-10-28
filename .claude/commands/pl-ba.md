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
only `git` (from the repository root — never `git -C`, which permission rules do not match), `bash .github/plumbline/check-template.sh` yourself; read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.
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

## Drafts
Drafts go in `.plumbline-drafts/<KEY or slug>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).

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

## Step 1 — Input
- An epic key: fetch it (and its PRD, from the description or a linked Confluence page) with the connected
  JIRA/Atlassian tools. The epic must pass the JIRA hand-off gate for `plumbline-prd-approved`.
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
and ask before creating it in JIRA under the epic with its approval label as the JIRA hand-off says (`plumbline-dor-ready`) and its blocked-by links — show the
exact content first and wait for a yes.
**Writing to JIRA (once approved):** create each story with its epic as `parent`; put the points in the project's
story-points field (team-managed projects: `customfield_10016`, "Story point estimate" — check the issue-type fields if
unsure); write acceptance criteria as plain `-` bullets (markdown `- [ ]` arrives as literal text); then add one
`Blocks` link per blocked-by. Read one created issue back to confirm parent, points and labels were saved.
