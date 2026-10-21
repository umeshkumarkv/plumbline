# .agentic-sdlc — Agentic SDLC (Plumbline), copy this folder

Everything Plumbline needs lives in this one folder. The only files outside it are the ones Claude Code and Copilot
require at fixed paths (`.claude/`, `.github/`), and `install.sh` generates those from here.

## Use in a repository
```bash
cp -R <source>/.agentic-sdlc ./.agentic-sdlc    # or unpack the release tarball here
python3 .agentic-sdlc/init.py                    # detect, project.yaml, install, baseline, prerequisites, doctor
git add .agentic-sdlc .claude .github .gitignore && git commit -m "Add Plumbline $(cat .agentic-sdlc/VERSION)"
```
`init.py --doctor` reports what the framework sees; `--check` fails CI on drift; `--upgrade <tarball>` updates the
framework and keeps `project.yaml` and the baseline. `--domain broker-dealer` selects the broker-dealer domain pack.
Protect it: `.agentic-sdlc/`, `.claude/` and `.github/` are protected paths (agents may not change them; a PR that does
fails CI unless a human adds the `plumbline-policy-change` label). Add them to CODEOWNERS.

## What is inside
| Folder | What | Generic? |
|---|---|---|
| `plumbline/` | loop specs, shared rules, critic agent, `build.py` (generates `dist/`) | method generic; specs assume the stack below |
| `dist/` | generated Claude Code commands/agents and Copilot prompts/agents | generated |
| `bench/` | Stage 2 benchmark (`run.py`) + Stage 1 scope check (`scope_check.py`) | engine generic; role checks assume the stack |
| `gates/` | Semgrep + structure/domain checks, protected paths, CI templates, baseline | `checks/protected_paths.py` generic; rules and baseline are this repo's |
| `impact/` | cross-service impact map | Spring REST + Kafka |
| `packs/` | domain rule pack, governance schema | domain-specific |
| `selftest/` | self-tests: `python3 .agentic-sdlc/selftest/agents_selftest.py` etc. | |

**Current fit:** Java/Spring Boot services under `services/<name>/`, React under `frontend/`, Kafka, Postgres, JIRA,
GitHub. The Semgrep rules, domain pack, `gates/baseline.json` and ArchUnit test are written for broker-dealer: replace
them for another domain, and regenerate the baseline (`python3 .agentic-sdlc/gates/run_gates.py . --write-baseline`).

## Repository layouts
The checks find each deployable unit with `python3 .agentic-sdlc/impact/layout.py .`. Detected automatically:
`services/<name>/` backends, top-level modules with `pom.xml`/`build.gradle` and `src/main/`, **a single app at the
repository root** (`./src`, the root `CLAUDE.md` is its CLAUDE.md), and frontends (any top-level folder with a
`package.json`, e.g. `ui/`). Anything else: copy `project.yaml.example` to `project.yaml` here and list the units.

## Update
Replace this folder with the new release (keep your `project.yaml`), run `.agentic-sdlc/install.sh`, commit. See `CHANGELOG.md`.
