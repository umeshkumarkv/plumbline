# Plumbline

**AI agents for existing codebases, with a second pair of eyes.** Plumbline gives Claude Code and GitHub Copilot ten
commands, one per SDLC role. Each one has a *writer* agent do the work and a separate *judge* agent — fresh context, never saw how the work
was done — check it against your project's rules. Up to 3 attempts, then it hands over to you. Nothing is committed,
pushed or posted without your yes.

| Command | What it does | Writes to |
|---|---|---|
| `/pl-onboard` | Documents the codebase: one `CLAUDE.md` per service/frontend + a master `CLAUDE.md` | CLAUDE.md files |
| `/pl-pm "idea"` | Feature idea → PRD (problem, solution, success criteria, scope, backlog) | JIRA epic* |
| `/pl-ba CRS-40` | Epic → stories with testable acceptance criteria | JIRA stories* |
| `/pl-arch CRS-12` | Story → technical design (API, data, logic, access, tests) | JIRA comment* |
| `/pl-dev CRS-12` | Implements the story with tests on a new branch | branch* |
| `/pl-code-review 42` | Independent review of a PR or branch against your `CLAUDE.md` rules | PR comment* |
| `/pl-qa CRS-12` | Runs the acceptance criteria against the running system, records evidence | JIRA comment* |
| `/pl-doc 42` | After merge: updates the API spec and CLAUDE.md files to match the code | docs PR* |
| `/pl-devops 42` | Fixes a red CI run (code/tests/coverage) or proposes the fix (pipeline/config) | branch* |
| `/pl-sm` | Daily sprint health: stuck, blocked, Definition of Done, velocity | JIRA comments* |

\* only after you say yes — you see the exact content first.

The usual flow: **onboard** once → **pm → ba → arch → dev → code-review → qa → doc**, with **devops** when CI is red
and **sm** every morning. Each command also works on its own.

**Nothing to install.** Plumbline is two folders of markdown: `.claude/` (Claude Code) and `.github/` (Copilot +
an optional CI check). Same on Windows, macOS and Linux.

## Install — copy two folders into your project

Get Plumbline once: `git clone https://github.com/umeshkumarkv/plumbline` — or on GitHub: **Code → Download ZIP** and
unzip. Then copy its `.claude` and `.github` folders into your project's root (they merge with folders you already
have; Plumbline's commands are named `pl-*` and its agents `plumbline-*`, so they don't clash with yours).

**Windows (PowerShell), from your project folder:**
```powershell
robocopy $HOME\plumbline\.claude .claude /E
robocopy $HOME\plumbline\.github .github /E
```
**macOS / Linux, from your project folder:**
```bash
cp -R ~/plumbline/.claude ~/plumbline/.github .
```
Commit them. Done.

## Use

**Claude Code:** type `/pl-onboard`.
**VS Code + Copilot:** open Chat in **Agent** mode, make sure the **runSubagent** tool is enabled in the tools picker,
then type `/pl-onboard`.

Start with `/pl-onboard` — the other commands read the `CLAUDE.md` files it writes. The first run asks for your
JIRA project and Confluence space and stores them in the root `CLAUDE.md` under *Plumbline settings*. Review what it
wrote with `git diff`, then commit on a branch and open a PR.

JIRA, Confluence and GitHub work through the tools you have connected (e.g. the Atlassian MCP server); without them,
paste the story text instead.

## CI check (optional)

`.github/workflows/plumbline-checks.yml` runs on every pull request, in GitHub Actions:
- **protected files** — a PR may not change Plumbline's agents or checks unless a maintainer adds the
  `plumbline-policy-change` label;
- **Semgrep** — 15 generic Java/Spring rules (money as floating point, SQL concatenation, hard-coded secrets, field
  injection, …) on **the lines the PR changes only**, so existing code never blocks anyone.

Don't want it? Delete that file.

## What's in the box
```
.claude/commands/   plumbline-<role>.md   ← one per command: the steps + the judge's checklist (the real content)
.claude/agents/     plumbline-<role>-writer.md (pm, ba, arch, dev, doc, onboard, sm), plumbline-qa-runner.md,
                    plumbline-devops-fixer.md, plumbline-judge.md (shared by every command)
.github/prompts/    the same commands for Copilot (each points at .claude/commands)
.github/agents/     the same agents for Copilot (each points at .claude/agents, plus its tool list)
.github/workflows/  plumbline-checks.yml  (optional CI)
.github/plumbline/  semgrep-java.yml      (rules for the CI check)
```
To change how a command behaves, edit its file in `.claude/` — Copilot uses the same file. Commands that need scratch
space (PRDs, stories, designs, QA evidence, CI logs) use `.plumbline-drafts/`, which they add to `.git/info/exclude`
so it never shows in `git status`.

## Remove
Delete the `pl-*` and `plumbline-*` files from `.claude/` and `.github/`, and `.github/plumbline/`. Your CLAUDE.md files
stay.

## Upgrading from 2.0 / 2.1
Commands were renamed from `/plumbline-<role>` to `/pl-<role>` in 2.2. Delete the old `.claude/commands/plumbline-*.md`
and `.github/prompts/plumbline-*.prompt.md`, then copy the two folders again.

## Upgrading from 1.x
1.x installed a `.plumbline/` folder and needed Python. Remove it, then install as above:
`python3 .plumbline/init.py --uninstall --yes` (or delete `.plumbline/` and the old `plumbline-*` command files by hand).
The full 1.x framework — ten roles, local benchmarks, impact maps — is kept at tag
[`v1.11.0`](https://github.com/umeshkumarkv/plumbline/tree/v1.11.0).
