# Changelog

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
