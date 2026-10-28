---
description: Plumbline — the architect's final design: HLD for an epic, LLD for a story, checked by an independent judge before any code
argument-hint: "<epic key → HLD, or story key → LLD>"
---

# /pl-arch

The architect's final word, which every later role follows exactly: the **HLD** for an epic (units, interactions,
data, cross-cutting decisions) and the **LLD** for each story (endpoint, data, logic, tests, points). A **writer**
drafts, an independent **judge** checks. Up to 3 attempts. Nothing is posted without the architect's yes.

Input: $ARGUMENTS

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
- **Templates and lanes:** what will be posted is written on its template (JIRA hand-off table;
  `.github/plumbline/templates/`). Give each writer the template, the version (`.github/plumbline/VERSION`) and
  `git rev-parse --short HEAD`; tell the judge the writer's agent name, so it checks that agent's *Your lane*. Before
  each judge and before posting run `bash .github/plumbline/check-template.sh <template> <draft>` — it also fails
  text outside the role's lane: FAIL = that attempt's finding, no judge. No bash → the judge checks it instead. Before
  posting, set the footer's `judge` to the result (e.g. `PASS 1/3`).
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
The person running a command is that role's SME: their yes at the hand-over is the approval, and JIRA records who.

| Step | Posts | Template | Label added on the SME's yes |
|---|---|---|---|
| `/pl-pm` | PRD page; the epic, with summary + PRD link | `prd.md`, `epic.md` | `plumbline-prd-approved` |
| `/pl-ba` | stories under the epic — business criteria | `story.md` | `plumbline-dor-ready` |
| `/pl-arch <EPIC>` | epic comment — the HLD | `handoff-hld.md` | `plumbline-hld-final` |
| `/pl-arch <STORY>` | story comment — the LLD; story points set | `handoff-arch.md` | `plumbline-arch-approved` |
| `/pl-dev` | story comment — branch, PR, test result | `handoff-dev.md` | — (the PR is reviewed next) |
| `/pl-code-review` | PR review + story comment — verdict and findings | `handoff-review.md` | `plumbline-review-passed` |
| `/pl-qa` | story comment — evidence per criterion | `handoff-qa.md` | `plumbline-qa-passed` |
| `/pl-doc` | docs PR updating CLAUDE.md + story comment | `handoff-doc.md` | the architect approves the docs PR |
| `/pl-devops`, `/pl-sm` | comment on the story / sprint issue | `handoff-devops.md`, `sprint-report.md` | — |

- **Input:** read the ticket — description, labels, links, the latest comment of each kind that starts
  `[Plumbline /pl-<role>]` (JIRA returns `\[Plumbline …\]`: ignore backslashes), the epic's HLD for a story, and for
  an epic the PRD page it links, **at the version it names** (no version → compare last-modified times).
- **Gate:** start only when the previous step's label is on the ticket (a story's design also needs
  `plumbline-hld-final` on its epic). A hand-off edited after it was posted (comment `updated` later than `created`;
  PRD page past the pinned version) → `STOPPED: <what> changed after approval — re-run <command>`.
- **The architect's word is final:** later roles follow the HLD and LLD exactly. A role that cannot → `STOPPED:
  design gap — /pl-arch <KEY>`; never work around it. Do not redo an earlier role's work.
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first; then
  add the label.
- No Confluence tools or no parent page → the PRD goes in the epic description. A comment must stay under 30,000
  characters (JIRA's limit is 32,767): longer → split. No JIRA tools → output as text to paste. Drafts are scratch.

## Metrics
At the hand-over append to `.plumbline-drafts/metrics.csv` (header, if new:
`date,command,target,attempts,verdict,tests_run,minutes,human_decision`): date, command, story/branch/PR, attempts,
verdict, tests ran `yes`/`no`/`n/a`, minutes (`date +%s` at start and at hand-over), and `human_decision` once the user
answers: `approved`, `edited` or `rejected`. It stays local; `/pl-sm metrics` summarises it.
**Files:** create drafts and metrics with your write tool (it creates folders) — never `mkdir`, `echo`, `printf` or
redirection, which permission settings block.

## Step 1 — Pre-flight
An **epic** key → the **HLD**: the epic, its PRD and its stories; draft `.plumbline-drafts/<KEY>/hld.md` on
`handoff-hld.md`; checklist: **HLD checklist**. A **story** key → the **LLD**: the story and its epic's HLD (the gate
needs `plumbline-hld-final` on the epic; a story with no epic is designed against the root CLAUDE.md only); draft
`.plumbline-drafts/<KEY>/design.md` on `handoff-arch.md`; checklist: **Design checklist**. Read the root `CLAUDE.md`
and the CLAUDE.md of each unit involved. **Stop and ask the user** if: the story has no acceptance criteria; a
blocker is not Done; the design would need another unit's database, a new unit, an out-of-scope feature, or a new
library the root CLAUDE.md does not allow.

## Step 2 — Attempts (1, 2, 3)
1. **Writer** — start `plumbline-arch-writer` with: HLD or LLD, the input paths, the CLAUDE.md paths, the draft path;
   on attempts 2–3 the judge's findings.
2. **Judge** — start `plumbline-judge` with exactly: *Review:* the draft, the input paths, the CLAUDE.md paths and the
   unit folders (writer: `plumbline-arch-writer`); *Checklist:* the HLD or Design checklist, verbatim. PASS → Step 3.

After 3 failed attempts: stop, show the last findings, and hand over (usually the story needs the BA to clarify).

### HLD checklist
1. Every story of the epic is in *Story design order* with exactly one unit; units exist in the root CLAUDE.md.
2. Interactions name each call/event with its failure behaviour; consumed events have a producer.
3. Data: each piece has one owning unit; no unit reads another's database.
4. Cross-cutting covers security/roles, errors, transactions/idempotency and audit — or says "not affected".
5. Every decision has its reason; nothing contradicts the root CLAUDE.md rules; no production code.

### Design checklist
1. *Acceptance criteria → design* maps every AC id to how it is met **and checked** (endpoint, status, fields, error
   code, or UI behaviour) — none left out; no criterion is changed (questions for BA go under Open questions).
1b. Conforms to the epic's HLD: the unit, interactions, data ownership and decisions are the HLD's (a needed change
   → stop: the HLD must change first). Technical blockers named or None; story points 1/2/3/5/8.
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
Show the HLD or LLD. Ask before posting it as the epic or story comment (already on its template) — exact text
first, then a yes; then add the label (`plumbline-hld-final` / `plumbline-arch-approved`) and, for an LLD, set the
story-points field and one `Blocks` link per technical blocker. The architect's yes makes it final: later roles
follow it exactly. A design covering several stories is posted on the first and linked from the others. Next step:
`/pl-arch <STORY>` for each story in *Story design order*, then `/pl-dev <KEY>`.
