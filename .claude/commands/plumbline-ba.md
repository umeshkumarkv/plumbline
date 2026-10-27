---
description: Plumbline — split an epic or requirement into ready-to-build stories with testable acceptance criteria, each checked by an independent judge
argument-hint: "<epic key, e.g. CRS-40, or a requirement in plain English>"
---

# /plumbline-ba

Turn an approved epic (or a requirement) into user stories that a developer — human or agent — can build without
guessing: user story, testable acceptance criteria, scope, constraints, test data, points. A **writer** subagent drafts
each story; an independent **judge** checks it. Up to 3 attempts per story, then it is handed to the user. Stories are
created in JIRA only after the user says yes.

Input: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-ba-writer` or `plumbline-judge`.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-ba-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

Never do the writer's or the judge's work yourself, and never pass the writer's reasoning to the judge. **Shell:** run
only `git` yourself; read and search files with your file tools. Do not research the code yourself — that is the
writer's and the judge's job; you route, check scope and hand over.

## Drafts
Drafts go in `.plumbline-drafts/<KEY or slug>/`. Make sure `.plumbline-drafts/` is in `.git/info/exclude` (add it with
your edit tool if missing).

## Step 1 — Input
- An epic key: fetch it (and its PRD, from the description or a linked Confluence page) with the connected
  JIRA/Atlassian tools. The epic should carry `plumbline-prd-approved`; if not, tell the user and ask whether to go on.
- Plain English: use it and continue. BA never creates epics: the stories are created without a parent unless the
  user names an epic at the hand-over (suggest `/plumbline-pm` for a new epic).
- No JIRA tools: ask the user to paste the epic/PRD.

Read the root `CLAUDE.md` and the CLAUDE.md of each unit involved. Split the work into stories, each inside **one
unit**. Show the list (title, unit, rough size) and continue.

**Stop and ask the user** if: a story needs another unit's database directly; it needs a unit that does not exist;
it is in the root CLAUDE.md out-of-scope list; or you cannot tell which unit owns a concept.

## Step 2 — Each story, attempts (1, 2, 3)
1. **Writer** — start `plumbline-ba-writer` with: the requirement/PRD, the story title and unit, the CLAUDE.md paths,
   the draft path `.plumbline-drafts/<KEY>/story-<n>.md`; on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the story path, the CLAUDE.md paths and the unit folder;
   *Checklist:* the **Story checklist** below, verbatim. PASS → next story. FAIL → next attempt.

After 3 failed attempts: mark the story ESCALATED with its last findings and move on. Points of 13+ after attempt 3
means the story must be split — say so.

### Story checklist
1. User story is "As a <specific role> / I want / So that".
2. Every acceptance criterion is testable on its own: for an API — method, path, expected status, and the field and
   value checked; for UI — the screen, the action, and what the user sees.
3. The criteria cover the happy path, not-found, and invalid input (where they apply).
4. The story stays inside one unit; any call to another unit uses that unit's existing API (check it exists).
5. Points are one of 1 / 2 / 3 / 5 / 8.
6. Blocked-by is named, or explicitly "None".
7. Nothing from the root CLAUDE.md out-of-scope list.
8. Tech constraints: unit, port, branch pattern, PR target and "read CLAUDE.md first" are stated and match the root
   CLAUDE.md settings and the code.
9. Test data is named: an existing table/fixture/seed (check it exists) or synthetic values.
10. Every endpoint, table or field the story says exists today really exists in the code.

## Step 3 — Hand over
Show a table: story · unit · points · result. For each passed story, show its Definition of Ready (items 1–10 checked)
and ask before creating it in JIRA under the epic with label `plumbline-dor-ready` and its blocked-by links — show the
exact content first and wait for a yes.
