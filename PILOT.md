# Plumbline pilot — one team, one repo, two sprints

The tests in [TEST-REPORT.md](TEST-REPORT.md) were run by the people who built Plumbline, on repositories they knew.
A pilot answers the question those tests cannot: **does it save a real team time without lowering quality, on code
we have never seen?**

## Set-up (day 1, about 1 hour)
1. The team picks the repository and a JIRA project. Plumbline's authors do not see the code beforehand.
2. Copy `.claude/` and `.github/` into the repo; merge `examples/claude-settings.json` into `.claude/settings.json`
   (replace the build/test lines with the repo's own commands).
3. Run `/pl-onboard`. A tech lead reviews the CLAUDE.md files it wrote and merges them like any PR.
4. Agree the baseline: the team's last two sprints — stories completed, cycle time (In Progress → merged), review
   comments per PR, bugs found after merge.

## During the pilot (two sprints)
- Pick 4–6 real backlog items. For each: `/pl-ba` → `/pl-arch` → `/pl-dev` → `/pl-code-review` → `/pl-qa` →
  `/pl-doc`. A person approves every hand-over as usual; nothing changes in the team's review or merge rules.
- One person, not the one approving, plants 3–5 defects in one branch each sprint and runs `/pl-code-review` on it
  (a blind test, like section 5.2 of the test report).
- Every command appends a line to `.plumbline-drafts/metrics.csv` and records the human decision (`approved`,
  `edited`, `rejected`). Keep the file; it is the main evidence.

## What we measure

| Measure | Where it comes from | Good result |
|---|---|---|
| Hand-overs approved without edits | `metrics.csv` `human_decision` | ≥ 60% |
| Hand-overs rejected | `metrics.csv` | ≤ 15% |
| Attempts per run | `metrics.csv` `attempts` | median 1 |
| Runs where tests did not run | `metrics.csv` `tests_run = no` | 0 for dev |
| Review comments from humans on agent PRs | the PRs | not higher than the team's baseline |
| Bugs found after merge in agent-built stories | JIRA, 30 days after the pilot | not higher than baseline |
| Cycle time for agent-built stories | JIRA | lower than baseline |
| Planted defects caught blind | the blind tests | ≥ 80%, no false alarms on clean code |
| Agent time per command | `metrics.csv` `minutes` | recorded, compared with the team's own estimate |
| Agent cost per story | the Claude Code usage page | recorded, no target |

## Exit
At the end of sprint 2 the team writes one page: keep, change or stop, with the numbers above. Problems found go back
into Plumbline as fixes, like every round in the test report.
