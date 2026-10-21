# .plumbline — Agentic SDLC (Plumbline), copy this folder

Everything Plumbline needs lives in this one folder, including the loop working files (`run/`, ignored by this
folder's `.gitignore`). Outside it, `init.py` writes only the entry files Claude Code and Copilot require, all named
`plumbline-*` (`.claude/commands`, `.claude/agents`, `.github/prompts`, `.github/agents`), and CI workflows only with
`--ci`. `init.py --uninstall --yes` removes everything again (CLAUDE.md files stay).

## Use in a repository
```bash
~/plumbline/install.sh                        # from a clone of https://github.com/umeshkumarkv/plumbline
# (or copy this folder in and run: python3 .plumbline/init.py)
git add .plumbline .claude .github && git commit -m "Add Plumbline $(cat .plumbline/VERSION)"
```
`init.py --doctor` reports what the framework sees; `--check` fails CI on drift; `--upgrade <tarball>` updates the
framework and keeps `project.yaml` and the baseline. `--domain broker-dealer` selects the broker-dealer domain pack.
Protect it: `.plumbline/`, `.claude/` and `.github/` are protected paths (agents may not change them; a PR that does
fails CI unless a human adds the `plumbline-policy-change` label). Add them to CODEOWNERS.

## What is inside
| Folder | What | Generic? |
|---|---|---|
| `loops/` | loop specs, shared rules, critic agent, `build.py` (generates `dist/`) | method generic; specs assume the stack below |
| `dist/` | generated Claude Code commands/agents and Copilot prompts/agents | generated |
| `bench/` | Stage 2 benchmark (`run.py`) + Stage 1 scope check (`scope_check.py`) | engine generic; role checks assume the stack |
| `gates/` | Semgrep + structure/domain checks, protected paths, CI templates, baseline | `checks/protected_paths.py` generic; rules and baseline are this repo's |
| `impact/` | cross-service impact map | Spring REST + Kafka |
| `packs/` | domain rule pack, governance schema | domain-specific |
| `selftest/` | self-tests: `python3 .plumbline/selftest/agents_selftest.py` etc. | |

**Fit:** Java/Spring Boot backends (any layout below) and React/Angular/Vue frontends, JIRA + Confluence, GitHub.
Generic by default: `java-generic.yml` + `structure_check`, no domain pack, and a gate baseline built from *this*
repository (`init.py --rebaseline`). `--domain broker-dealer` adds the example OMS rule packs and domain invariants.

## Repository layouts
The checks find each deployable unit with `python3 .plumbline/impact/layout.py .`. Detected automatically:
`services/<name>/` backends, top-level modules with `pom.xml`/`build.gradle` and `src/main/`, **a single app at the
repository root** (`./src`, the root `CLAUDE.md` is its CLAUDE.md), and frontends (any top-level folder with a
`package.json`, e.g. `ui/`). Anything else: copy `project.yaml.example` to `project.yaml` here and list the units.

## Update
`git -C ~/plumbline pull && ~/plumbline/install.sh` (or `init.py --upgrade <tarball>`) replaces the framework and keeps `project.yaml`,
the baseline and `run/`. See `CHANGELOG.md`.
