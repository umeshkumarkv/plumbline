# Changelog

## 2.2.0 — 2026-10-27 — short commands, tested end to end
- **Commands are `/pl-<role>`** (`/pl-onboard`, `/pl-pm`, `/pl-ba`, `/pl-arch`, `/pl-dev`, `/pl-code-review`, `/pl-qa`,
  `/pl-doc`, `/pl-devops`, `/pl-sm`); typing `/pl` lists them all. Agents keep `plumbline-*` (never typed; avoids
  clashes). Upgrading: delete the old `plumbline-<role>` command and prompt files, copy the two folders again.
- `/pl-sm` works without a JIRA connection: give it a sprint export (CSV/JSON).
- Helpers start in the foreground and the command waits for each result (a background helper made a run look
  finished early).
- If Claude Code refuses a helper's file write (it blocks report-like files), the helper returns the content as
  `FILE: <path>` and the command saves it; the SM draft is now `standup.md`.
- `/pl-doc` judge traces every documented status/error code to its handler (an unhandled exception is a 500).
- **Tested:** every command on two real repositories (candidate-review-system, broker-dealer), including `/pl-qa`
  driving the real frontend with Playwright and `/pl-sm` on a sprint export; and every judge against deliberately
  flawed work — 47 of 47 planted defects caught; and one feature end to end on broker-dealer (pm → ba → arch → dev →
  code-review → doc: state-machine enforcement, ~15 minutes), and the same on candidate-review-system (Opportunity
  Lost loss-reason rule, backend + UI, ~25 minutes). Report: `TEST-REPORT.md`.

## 2.1.0 — 2026-10-27 — all ten roles
- **Seven roles back, in the 2.0 pattern** (writer subagent → independent judge → up to 3 attempts → hand over; no
  local tooling; Claude Code and Copilot share one file): `/plumbline-pm`, `/plumbline-ba`, `/plumbline-arch`,
  `/plumbline-qa`, `/plumbline-doc`, `/plumbline-devops`, `/plumbline-sm`. Each keeps its 1.x checklist and hard stops,
  made generic (no broker-dealer section numbers; the project's root CLAUDE.md is the reference).
- New agents: `plumbline-{pm,ba,arch,doc,sm}-writer`, `plumbline-qa-runner`, `plumbline-devops-fixer`; the judge is
  shared by all ten commands.
- Checks that the 1.x Python benchmarks did are now done by the judge from the code or data (e.g. SM recomputes every
  list from the sprint facts file; Doc checks every changed endpoint against the spec).
- Drafts (PRDs, stories, designs, QA evidence, CI logs) live in `.plumbline-drafts/`, kept out of git through
  `.git/info/exclude` — nothing is added to the project.
- Onboarding records `API URL` and `Frontend URL` in the root CLAUDE.md settings (used by `/plumbline-qa`).
- Orchestrators route and hand over; they do not research the code themselves, and add `.plumbline-drafts/` to
  `.git/info/exclude` with their file tools (no shell `echo`/`mkdir`).
- `/plumbline-devops`: failures that also fail on the base branch don't block the fix; a commit called a refactor did
  not intend to change output, so the tests are right.
- **Live-tested** (Claude Code, two real repositories): pm, ba, arch, doc and devops all passed their judge on attempt
  1 — see the test report. `/plumbline-qa` and `/plumbline-sm` were not run (they need a running system and live JIRA).

## 2.0.1 — 2026-10-23 — fixes from live runs (Claude Code, two real repositories)
- Orchestrators run only `git` (and the project's build) — no `find`/`grep`/`ls`, which fail in PowerShell; files are
  found with the agent's own search tools.
- `/plumbline-dev` runs the build/tests once **before** the change: pre-existing failures (both test repositories had
  them) are reported, not blamed on the story; a test runner that cannot start is said up front.
- The dev writer never runs `git stash`/`checkout`/`reset`/`restore`/`switch` (it had stashed to prove a test fails).
- Copilot CLI: subagents start with the `task` tool (VS Code: `runSubagent`). Onboarding units may run in parallel.

## 2.0.0 — 2026-10-23 — Plumbline Lite

Plumbline is now two folders of markdown that you copy into a project. No Python, bash, Semgrep or installer on
anyone's laptop; the same files work on Windows, macOS and Linux, in Claude Code and GitHub Copilot.

- **Three commands:** `/plumbline-onboard`, `/plumbline-dev`, `/plumbline-code-review`. Each: writer subagent →
  independent judge subagent (fresh context) → up to 3 attempts → hand over to the user.
- **One source of truth:** the instructions live in `.claude/`; the Copilot prompts and agents point at them.
- **Checks that need no tooling:** onboarding's judge verifies endpoints, tables and integrations by searching the
  code; `/plumbline-dev` runs the project's own build/tests and a `git diff` scope check before the judge.
- **Drafts are your working tree:** review with `git diff`, discard with `git checkout -- <file>`. No `.plumbline/`
  folder, no `project.yaml`, no baseline file.
- **CI (optional), in GitHub Actions:** protected Plumbline files (label `plumbline-policy-change` to approve) and
  Semgrep on the lines a PR changes only (`--baseline-commit`), so existing code never blocks a PR.
- **Settings** (JIRA project, Confluence space, base branch) live in the root `CLAUDE.md`, asked for once.
- Lessons kept from 1.x: the judge asks for the detail an item names and no more; documented debt passes; column
  names are not tables; CLAUDE.md files stay under 30 KB; nothing external is written without a yes.

The 1.x framework (ten roles, local benchmarks, gate baselines, impact maps, `init.py`) remains at tag `v1.11.0`.
