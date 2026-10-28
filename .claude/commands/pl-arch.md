---
description: Plumbline — technical design for one story (API, data, logic, integrations, security, tests), checked by an independent judge before any code
argument-hint: "<story key, e.g. CRS-12, or a pasted story>"
---

# /pl-arch

Write the technical design a developer (or `/pl-dev`) builds from: endpoint, data changes, service logic,
calls and events, security, tests, API-spec delta. A **writer** subagent drafts it; an independent **judge** checks it
against the story and the code. Up to 3 attempts, then it is handed to the user. Nothing is posted without a yes.

Story: $ARGUMENTS

## How subagents are started
- **Claude Code:** the Agent tool with `subagent_type: plumbline-arch-writer` or `plumbline-judge` — in the foreground (`run_in_background: false`): wait for each result before the next step.
- **GitHub Copilot:** VS Code — `#runSubagent` (the `agent/runSubagent` tool); Copilot CLI — the `task` tool; with
  agent `plumbline-arch-writer` or `plumbline-judge` (`.github/agents/`). If subagents are not available, stop and say so.

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
Drafts go in `.plumbline-drafts/<KEY>/`. Make sure `.plumbline-drafts/.gitignore` exists with the single line `*` (write it with your write tool; it keeps the folder out of git without touching `.git/`, which Claude Code protects).
Save the story you read from JIRA (description, criteria, links) as `.plumbline-drafts/<KEY>/story.md` for the writer
and judge of this run.

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
  `[Plumbline /pl-<role>]` or `[Plumbline approve /pl-<role>]` (JIRA returns them as `\[Plumbline …\]`: ignore
  backslashes), and for an epic the PRD page it links, **at the version
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

## Step 1 — Pre-flight
Fetch the story with the connected JIRA tools (or ask the user to paste it). Read the root `CLAUDE.md` and the unit's
CLAUDE.md.

**Stop and ask the user** if: the story has no acceptance criteria; a blocked-by ticket is not Done; the design would
need another unit's database, a new unit, an out-of-scope feature, or a new library the root CLAUDE.md does not allow.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-arch-writer` with: the story path, the unit, the CLAUDE.md paths, the draft path
   `.plumbline-drafts/<KEY>/design.md` (on `handoff-arch.md`); on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the design path, the story path, the CLAUDE.md paths and
   the unit folder; *Checklist:* the **Design checklist** below, verbatim. PASS → Step 3. FAIL → next attempt.

After 3 failed attempts: stop, show the last findings, and hand over (usually the story needs the BA to clarify).

### Design checklist
1. *Acceptance criteria → design* maps every AC id of the story to a part of the design — none left out.
2. Endpoint: method, path, auth/roles, request and response fields with types, and the unit and port match the CLAUDE.md
   files (and any code the design cites).
3. Every error path in the criteria has a status and an error code in the project's error format.
4. Data: the migration (next free version number, in the unit's own schema) or an explicit "no schema change"; entity
   changes with types.
5. Service logic: class and method, ordered steps, error paths; follows the layering rules in the CLAUDE.md files.
6. Calls to other units hit endpoints that exist; the failure/timeout behaviour is stated. Consumed events have a
   producer; produced events have a consumer or a stated reason.
7. Cache/config/env-var changes named, or "none".
8. **Identity and access, exactly:** the field used for ownership checks, the kind of each identifier (e.g. user id vs
   customer id, compared like with like), who may call each endpoint per role, and the headers/claims the gateway
   passes.
9. Tests: at least 3 cases per layer touched (logic, API/controller, UI), including the error paths.
10. API-spec delta (e.g. openapi.yaml) stated, or "no change". No placeholders left.

## Step 3 — Hand over
Show the design. Ask before posting it as the story comment (it is already on `handoff-arch.md`, starting
`[Plumbline /pl-arch] <date>`) — show the exact text first and wait for a yes; the approval follows the JIRA hand-off.
A design covering several stories is posted on the first and linked from the others. Next step: `/pl-dev <KEY>`.
