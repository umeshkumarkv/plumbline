# Plumbline

**AI agents for existing codebases, with a second pair of eyes.** Plumbline gives Claude Code (and, in preview, GitHub
Copilot) ten commands, one per SDLC role. In each, a *writer* agent does the work and a separate *judge* agent — fresh
context, never saw how the work was done — checks it against your project's rules. Up to 3 attempts, then it hands
over to you. Nothing is committed, pushed or posted without your yes.

| Command | What it does | Writes to |
|---|---|---|
| `/pl-onboard` | Documents the codebase: per service/frontend a short `CLAUDE.md` + a `CLAUDE.reference.md` catalogue, and a master `CLAUDE.md`; checks the tests run | CLAUDE.md files |
| `/pl-pm "idea"` | Feature idea → PRD in business language (problem, behaviour, success criteria, scope, sized backlog) | Confluence page + JIRA epic* |
| `/pl-ba CRS-40` | Epic → stories in business language (Given/When/Then criteria, examples) — no APIs, units or points | JIRA stories* |
| `/pl-arch CRS-40` / `CRS-12` | The architect's final design: epic → HLD (Confluence page + its decisions into CLAUDE.md); story → LLD (unit, how each criterion is checked, API, data, logic, tests, points) | Confluence + docs PR + JIRA* |
| `/pl-dev CRS-12` | Implements the story and the design's tests on a new branch | branch* |
| `/pl-code-review 42` | Independent review of a PR or branch against your `CLAUDE.md` rules and its stories | PR comment* |
| `/pl-qa CRS-12` | Runs the acceptance criteria against the running system, records evidence | JIRA comment* |
| `/pl-doc 42` | After merge: updates the API spec and CLAUDE.md files to match the code | docs PR* |
| `/pl-devops 42` | Fixes a red CI run (code/tests/coverage) or proposes the fix (pipeline/config) | branch* |
| `/pl-sm` | Daily sprint health: stuck, blocked, Definition of Done, velocity; `/pl-sm metrics` | JIRA comments* |

\* only after you say yes — you see the exact content first.

The usual flow: **onboard** once → **pm → ba → arch → dev → code-review → qa → doc**, with **devops** when CI is red
and **sm** every morning; arch runs once per epic (HLD) and once per story (LLD). Each command also works on its own. Testing it? [TEST-PLAN.md](TEST-PLAN.md) runs everything in one go.

## Status

| | Status |
|---|---|
| Claude Code | **Supported.** Tested with Claude Code 2.1.309 on Linux on two real codebases — see [TEST-REPORT.md](TEST-REPORT.md) |
| Claude Code on macOS / Windows | Expected to work; not yet tested. The template check is a bash script (Git Bash on Windows); without bash the judge checks the template instead |
| GitHub Copilot (VS Code agent mode, Copilot CLI) | **Preview.** Files follow the documented format; not yet tested end to end |
| Stacks tested | Java/Spring Boot backends, Angular and React frontends. Others should work; not yet tested |

What is enforced and what is only instructed is set out in [SECURITY.md](SECURITY.md).

**Check it yourself:** [eval/](eval/README.md) has a sample service and ten pull requests — five with planted defects
and an answer key, five clean — so anyone can run `/pl-code-review` in Claude Code or Copilot and score it. Testing
Plumbline with a team? Use [TEAM-TEST.md](TEAM-TEST.md); for a two-sprint trial, [PILOT.md](PILOT.md).

## Install

1. Get Plumbline: `git clone https://github.com/umeshkumarkv/plumbline` (or **Code → Download ZIP**).
2. Copy its `.claude` and `.github` folders into your project's root. They merge with what you have; Plumbline's
   files are named `pl-*` and `plumbline-*`, so they don't clash.
   - macOS / Linux: `cp -R ~/plumbline/.claude ~/plumbline/.github .`
   - Windows (PowerShell): `robocopy $HOME\plumbline\.claude .claude /E` and `robocopy $HOME\plumbline\.github .github /E`
3. **Permissions (recommended for every team):** merge the `allow`, `deny` and `ask` lists from
   [`examples/claude-settings.json`](examples/claude-settings.json) into your `.claude/settings.json`, and replace the
   build/test lines with your project's commands. See [Permissions](#permissions).
4. **Owners (recommended):** merge [`examples/CODEOWNERS`](examples/CODEOWNERS) into `.github/CODEOWNERS` and require
   code-owner review, so the architect approves every CLAUDE.md change.
5. Commit on a branch and open a PR.

Requirements: Claude Code with subagents (the Agent tool), or VS Code with Copilot agent mode and the **runSubagent**
tool enabled. JIRA, Confluence and GitHub work through the tools you have connected (e.g. the Atlassian MCP server);
without them, paste the story text instead.

## Use

Type `/pl-onboard` first — the other commands read the `CLAUDE.md` files it writes. It asks for your JIRA project,
Confluence space and parent page and base branch, runs each unit's tests once, and asks you to settle any rule the repository
contradicts itself on (for example, which branch PRs target). Review its changes with `git diff`, then commit on a
branch and open a PR.

Every command ends with a hand-over whose first line is `PASS`, `FAIL after 3 attempts`, `STOPPED: <reason>` or
`UNVERIFIED: <what did not run>`, followed by each action it proposes, with the exact text or command, waiting for
your yes.

## How the commands work together
- **CLAUDE.md is the single source of truth, kept small.** `/pl-onboard` reads the code once. Each unit gets a core
  `CLAUDE.md` (at most 8 KB: purpose, build and test recipe, architecture, security, rules, must-nevers, decisions)
  that every agent loads, and a `CLAUDE.reference.md` (endpoints, data, integrations, config, debt) opened only for the
  section a task needs. Every rule says where it comes from: `[code: <file>]` (what the code does today) or
  `[decided <source>]` (what a person decided). After each merge `/pl-doc` adds the new durable rules and design
  decisions, keeps the core under 8 KB, and proposes removals for the architect, who approves the docs PR. Before
  each run, commands check whether the code changed since CLAUDE.md's `Last updated` commit and warn the agents.
- **JIRA is the hand-off; the SME's yes is the approval.** The PRD and each epic's HLD are Confluence pages, linked
  from the epic. Everything else lives in JIRA: the epic, the stories, and one `[Plumbline /pl-<role>]` comment per
  step — the LLD on each story. The HLD's decisions and rules also go into CLAUDE.md (`[decided <EPIC>]`) through a
  docs PR the architect owns, so every later agent works under them. Each command posts only after its SME's yes and then adds its label
  (`plumbline-prd-approved`, `plumbline-dor-ready`, `plumbline-hld-final`, `plumbline-arch-approved`,
  `plumbline-review-passed`, `plumbline-qa-passed`); JIRA records who posted it. The next command starts only when the
  label is there, and stops if a PRD page or hand-off comment was edited after it was posted. Code still needs a second
  person: the PR approval your GitHub branch protection requires.
- **The architect's design is final.** Dev, code review, QA, doc and devops follow the HLD and LLD exactly; a role that
  cannot stops with `design gap — /pl-arch <KEY>` instead of working around it, and code review fails any difference.
- **Same shape everywhere, versioned.** Everything Plumbline produces — JIRA descriptions and comments, Confluence
  pages, PR descriptions and reviews, and the CLAUDE.md files — is written on a template in
  `.github/plumbline/templates/` and names its template version (`story v1`). `check-template.sh` checks headings,
  fields, the version and the role lane before any judge runs; a template cannot change without a new version
  (`VERSIONS` lock + `CHANGELOG.md`). Acceptance criteria carry ids (`AC1`, `AC2`,
  …) that design, tests and QA evidence cite.
- **Every agent stays in its lane.** Each writer has a *Your lane* section (what it owns, what it must never do);
  the template check rejects what other roles own (an API path or points in a BA story, code in a design), the judge
  fails anything else outside the lane, and the PM, BA and SM writers cannot edit files or run commands.
  PM and BA agents may read code to learn what exists today, but write business language only. Business SMEs approve
  business content; the architect owns units, technical checks, blockers and points; branch and PR target come from the
  repository settings.
- **Independent judging.** For code changes the judge reads the changed files, their callers, tests and entities
  itself — it does not take CLAUDE.md's word for what the code does.

Also:
- **Honest test status** — if the build or tests could not run, `/pl-dev` says **UNVERIFIED** first, also in its JIRA
  comment. Work a judge passed by reading is not called tested.
- **Metrics** — every command appends a line to `.plumbline-drafts/metrics.csv` (attempts, verdict, tests run, your
  decision). `/pl-sm metrics` summarises it.
- **Drafts** — `.plumbline-drafts/` is scratch before posting; it ignores itself (`.gitignore` = `*`) and no command
  reads another's drafts.

## Permissions
Plumbline runs with Claude Code's normal permission prompts. The example settings:
- **allow** reading, `git` read commands, creating branches, writing inside `.plumbline-drafts/`, and your test
  commands;
- **ask** before every `git push` — and leave JIRA, Confluence and GitHub write tools on ask too;
- **deny** `reset`, `checkout`, `restore`, `rebase`, `clean`, `stash`, `commit --amend`, deleting branches, `git -C`,
  edits to `.claude/` and `.github/`, and reading `.env`, key and credential files and `*-prod*` / `*-local*`
  config.

Anything an agent can read reaches the model and its logs: if other files in your repository hold secrets, add them to
`deny`. Details and the threat model: [SECURITY.md](SECURITY.md).

## CI check (optional)
`.github/workflows/plumbline-checks.yml` runs on every pull request in GitHub Actions:
- **protected files** — a PR may not change Plumbline's commands, agents or checks unless a maintainer adds the
  `plumbline-policy-change` label;
- **Semgrep** — 15 Java/Spring rules (money as floating point, SQL concatenation, hard-coded secrets, …) on **the
  lines the PR changes only**, using the rules from the base branch.

`plumbline-selftest.yml` is Plumbline's own test and is skipped in your project. Delete either file if you don't want it.

## A different model for the judge (optional)
Writer and judge use your session's model, so they can share blind spots. To give the judge its own model, add a
`model:` line to the frontmatter of `.claude/agents/plumbline-judge.md` (e.g. `model: opus`, or a full model id), and
check `/agents` shows it. The file is protected by the CI check, so this needs the `plumbline-policy-change` label.
Compare with `eval/ab.sh` before and after.

## What's in the box
```
.claude/commands/   pl-<role>.md          one per command: the steps + the judge's checklist
.claude/agents/     plumbline-<role>-writer.md, plumbline-qa-runner.md, plumbline-devops-fixer.md,
                    plumbline-judge.md (shared by every command)
.github/prompts/    the commands for Copilot (each points at .claude/commands)
.github/agents/     the agents for Copilot (each points at .claude/agents, plus its tool list)
.github/workflows/  plumbline-checks.yml (optional CI), plumbline-selftest.yml (Plumbline's own test)
.github/plumbline/  templates/ (every posted artefact), check-template.sh, semgrep-java.yml (CI rules), VERSION
examples/           claude-settings.json (recommended permissions), CODEOWNERS
eval/               sample app + 10 review cases, setup / score / run / A/B scripts (not copied into your project)
tests/              validate.sh — Plumbline's self-test
```
To change how a command behaves, edit its file in `.claude/` — Copilot uses the same file.

## Upgrade
Check your version in `.github/plumbline/VERSION`, read [CHANGELOG.md](CHANGELOG.md), then copy the `.claude` and
`.github` folders again (step 2 of Install) and re-merge `examples/claude-settings.json`. Your `CLAUDE.md` files and
`.plumbline-drafts/` are not touched.
- From 2.7 or earlier: run `/pl-onboard` again so each unit's CLAUDE.md is split into the core and
  `CLAUDE.reference.md`, rules get their `[code]`/`[decided]` tags, and the settings gain `Confluence parent page`.
  Stories posted before 2.8 have no AC ids; new ones do.
- From 2.0 / 2.1: also delete the old `.claude/commands/plumbline-*.md` and `.github/prompts/plumbline-*.prompt.md`
  (commands were renamed to `/pl-<role>` in 2.2).
- From 1.x: delete `.plumbline/` (or run `python3 .plumbline/init.py --uninstall --yes`). The 1.x framework is kept at
  tag [`v1.11.0`](https://github.com/umeshkumarkv/plumbline/tree/v1.11.0).

## Remove
Delete `.claude/commands/pl-*.md`, `.claude/agents/plumbline-*.md`, `.github/prompts/pl-*.prompt.md`,
`.github/agents/plumbline-*.agent.md`, `.github/workflows/plumbline-*.yml`, `.github/plumbline/` and
`.plumbline-drafts/`, and remove the Plumbline lines from `.claude/settings.json`. Your CLAUDE.md and
CLAUDE.reference.md files stay.

## Releases
Each release passes `bash tests/validate.sh` and the steps in [RELEASING.md](RELEASING.md).
