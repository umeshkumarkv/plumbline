---
description: Plumbline — approve or reject one role's hand-off as its approver; posts the decision and, on approval, adds the step's label
argument-hint: "<KEY> <pm|ba|arch|review|qa>"
---

# /pl-approve

The second pair of human eyes. The person who ran a step does not approve it (with `Separate approver: yes`, the
default); someone else runs `/pl-approve` on the ticket. It reads the hand-off exactly as the next role will see it,
shows it, records the decision as a `[Plumbline approve /pl-<role>]` comment, and on approval adds the label the next
command waits for. No writer and no judge: the decision is the person's.

Input: $ARGUMENTS

## How it runs
No subagents. **Shell:** run only `git` (from the repository root — never `git -C`, which permission rules do not
match), `bash .github/plumbline/check-template.sh` and `date +%s` yourself; read files with your file tools.

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
  the approval must come from someone other than the **author** of that step's hand-off (the comment's author; for
  an epic or story description, the issue's creator): a `[Plumbline approve /pl-<role>]` comment by them, else the
  issue's change history for the label. Otherwise stop: `STOPPED: <label> not on <KEY>` · `STOPPED: <KEY>
  self-approved by <name>` · `STOPPED: cannot verify who approved <KEY> — run /pl-approve`.
- **Output:** post what the table says, on its template, after the SME's yes with the exact text shown first. JIRA
  records who posted it. `Separate approver: yes` → no label; tell the SME `/pl-approve <KEY> <role>` must be run by
  another person. `no` → add the label after the yes.
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

## Step 1 — What is being approved
| Role | Ticket | The hand-off | Label |
|---|---|---|---|
| `pm` | the epic | its description (`epic.md`) and the PRD page it links | `plumbline-prd-approved` |
| `ba` | a story | its description (`story.md`) | `plumbline-dor-ready` |
| `arch` | a story | the latest `[Plumbline /pl-arch]` comment (the design) | `plumbline-arch-approved` |
| `review` | a story | the latest `[Plumbline /pl-code-review]` comment (and the PR review) | `plumbline-review-passed` |
| `qa` | a story | the latest `[Plumbline /pl-qa]` comment | `plumbline-qa-passed` |

Fetch the ticket with the connected JIRA/Atlassian tools (no tools → stop: approval needs JIRA). No hand-off found →
`STOPPED: no /pl-<role> hand-off on <KEY>`. For `pm`, read the linked PRD page and note its version (or last-modified time); for comments, note their date.

## Step 2 — Who is approving
`Approver` is the connected Atlassian user. With `Separate approver: yes` (root CLAUDE.md Plumbline settings), if the
approver is the hand-off's author (comment author; for an epic or story description, the issue's creator) →
`STOPPED: you ran this step; another person must approve it`.

## Step 3 — Show it
Show the hand-off as posted, then flag plainly: its `Judge` line is not PASS; the template check
(`bash .github/plumbline/check-template.sh` on the posted text saved to `.plumbline-drafts/<KEY>/approve-<role>.md`)
fails; open questions are not `None`; the PRD page or the hand-off comment was edited after it was posted. Do not judge the content yourself and do
not redo the role's work — the approver decides.

## Step 4 — Hand over: the decision
Ask: **approve**, or **reject** with reasons. Write the comment on `approval.md` (Decision, the hand-off's date, the
page version, the reasons), run the template check, show it, and on a yes: post it; on approve, add the label. For
`arch`, also ask the approver for the story points (default: the design's suggestion), set the story-points field and
add one `Blocks` link per technical blocker the design names. Never add a label for a rejection; never approve for someone who is not in this
chat. Hand-over first line: `PASS` (approved), `STOPPED: rejected` or `STOPPED: <reason>`.
