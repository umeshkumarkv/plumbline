# Changelog

## 2.4.0 — 2026-10-28 — onboarding proves the tests run; decisions get settled; secrets and injection
- **Test recipe:** `/pl-onboard` runs each unit's test command once and records, in its CLAUDE.md, the command, the
  runtime it needs and the real result (or exactly why it could not run), plus hard-coded paths tests depend on. The
  summary warns first when a unit's tests do not run — later `/pl-dev` runs there will be UNVERIFIED until fixed.
- **Decisions needed:** the root CLAUDE.md lists where the repo's docs, settings and code disagree (PR target, branch
  naming, ticket key, test command, environments); `/pl-onboard` asks the user and records each answer as
  `(decided <date>)` in the Plumbline settings, which now include `PR target` and `Branch pattern`.
- **Judge:** a credential value anywhere in the work is always a blocker; instructions aimed at the reviewer inside
  the work are reported, never followed.
- **Permissions example:** also denies reading `.env`, key stores, private keys and credential files.

## 2.3.0 — 2026-10-28 — closing the gaps from the first test round
- **Feature tracker** `.plumbline-drafts/features.md`: one row per story (story file, design file, branch, status).
  `/pl-ba`, `/pl-arch`, `/pl-dev` fill it; `/pl-code-review`, `/pl-qa`, `/pl-doc` read it — code review now reviews
  a branch against *all* the stories it carries without being told.
- **Design test plan enforced:** `/pl-dev` gives the writer the design; the judge lists `design test → test name` and
  fails on a missing one; `/pl-code-review` checks stories and designs (item 10).
- **No false "tested":** if the build/tests could not run, `/pl-dev`'s hand-over starts with **UNVERIFIED** and the
  story is marked `built, tests not run`.
- **QA environment step:** `/pl-qa` health-checks the URLs and offers start-here (with a yes), another URL, or stop;
  unattended runs stop with "QA not run" instead of guessing.
- **`/pl-ba` consistency:** branch pattern, PR target and key format are settled once and given to every writer;
  JIRA writes set the epic parent, story points and `Blocks` links and read one issue back.
- **Metrics:** every command appends to `.plumbline-drafts/metrics.csv` (attempts, verdict, tests run, human
  decision); `/pl-sm metrics` summarises it. [PILOT.md](PILOT.md) describes a two-sprint team trial.
- **Permissions:** `examples/claude-settings.json` — a tested allowlist so Plumbline runs with normal permission
  prompts. Helpers write files only with edit tools; commands run git without `-C`.
- **Tested:** backend tests run on a developer Mac — broker-dealer 234 → 411 passing, candidate-review-system 31 → 75
  passing, 0 failures (running them exposed 2 wrong tests, now fixed); a blind code review
  (8/8 hidden defects, no false alarms); repeat runs of PM and Arch; JIRA epic + 5 stories created for real; runs
  with permissions on. Details: `TEST-REPORT.md` section 5.

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
