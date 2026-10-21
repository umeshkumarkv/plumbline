# Plumbline

**Governed agentic SDLC for existing codebases.** Plumbline puts AI agents (Claude Code, GitHub Copilot) through the
whole delivery cycle — onboarding, PRD, story, design, code, review, QA, docs, CI fixes — and checks every step against
true vertical: a deterministic benchmark first, then an isolated judge, with a human approving every external write.

## Install in any repository (one step)

```bash
tar -xzf plumbline-<version>.tar.gz          # unpacks .agentic-sdlc/ at the repository root
python3 .agentic-sdlc/init.py                 # detect → project.yaml → agents/prompts/workflows → baseline → doctor
```
`init.py` detects the units (`services/<name>/`, top-level modules, an app at the root, frontends such as `ui/`), the
Java version, the frontend framework and the base branch; writes `.agentic-sdlc/project.yaml`; installs the generated
Claude Code commands/agents and Copilot prompts/agents and the CI workflows; writes this repository's gate baseline;
checks prerequisites (python3, PyYAML, Semgrep, JDK, node); and prints a **doctor** report of what the framework can
and cannot see. `--doctor` reports only, `--check` (CI) fails on drift, `--upgrade <tarball>` replaces the framework and
keeps `project.yaml` and the baseline. Then run `/onboard-eval-loop service:all`.

## What is inside

| Part | What it is | Where |
|---|---|---|
| **Loops** | One spec per role (PM, BA, Arch, Dev, Code Review, QA, Doc, DevOps, SM, Onboard), built into Claude Code commands + agents and Copilot prompts + agents. Each command orchestrates ORIGINATOR → BENCHMARK → JUDGE, at least 3 attempts before a human | `loops/`, `dist/` |
| **Benchmark** | Deterministic checks per role, run before the judge; scope check that keeps each originator inside its role | `bench/` |
| **Gates** | The rulebook as CI checks (Semgrep + structure checks), with a ratchet baseline: legacy debt never blocks, new violations always do. `java-generic.yml` for any Spring project; domain packs on top | `gates/` |
| **Impact map** | Which other units a change affects (REST, Kafka, shared schema), without an LLM — 1.5–3.8 s per PR on a 999-service repo | `impact/` |
| **Domain packs** | Business invariants for the judge and the gates (the broker-dealer OMS pack ships as an example) | `packs/domain-rules/` |
| **Governance** | Approval matrix, audit-record schema, model re-qualification | `packs/governance/` |
| **Eval harness** | Planted-defect harness that scores gates, judges and both together, and re-qualifies every model or tool version | `eval/` |

**CLAUDE.md pattern:** one master `CLAUDE.md` at the root (solution and architecture) and one per unit
(`src/CLAUDE.md` for an app at the root); generated content is merged between markers, never overwritten.

Results on `broker-dealer` (9 services): see **[eval/RESULTS.md](eval/RESULTS.md)**. Short version: gates own the mechanical rules; a fresh-context critic armed with the rulebook caught 79/80 planted defects with no false alarms on clean controls. Both numbers come with caveats, listed in the results.

## Quick start (on the OMS repo)

Everything a repository needs ships as **one folder, `.agentic-sdlc/`**, committed in that repository. Only the files
Claude Code and Copilot require at fixed paths live outside it (`.claude/`, `.github/`), and `install.sh` writes them.
```bash
python3 tools/make_kit.py                          # here: builds build/kit/.agentic-sdlc/ (or use the release tarball)
cp -R build/kit/.agentic-sdlc <repo>/.agentic-sdlc
cd <repo> && .agentic-sdlc/install.sh                # .claude/, .github/prompts|agents|workflows, .gitignore
pip install -r .agentic-sdlc/requirements.txt        # python3 >= 3.10, PyYAML, Semgrep
python3 .agentic-sdlc/gates/run_gates.py . --baseline .agentic-sdlc/gates/baseline.json      # 0 NEW on main
```
CI runs the checks from `.agentic-sdlc/` **as committed on the base branch**, so a PR cannot change the checker that
judges it. See `tools/KIT-README.md` (shipped as `.agentic-sdlc/README.md`) for what is generic and what is
broker-dealer-specific.
Optional: `gates/archunit/OmsArchitectureTest.java` (type-aware layering rules; needs archunit-junit5), `gates/ci/critic.yml` (headless critic for Copilot users), `packs/domain-rules/tests/OrderTransitionPolicyTest.java`.

## Layout

```
gates/
  semgrep/oms-rules.yml           C1–C12 code-review categories (CLAUDE.md §10–§14)
  semgrep/oms-domain-rules.yml    money rounding/cents, trading-day timezone, unbounded queries, quantity
  checks/structure_check.py       class suffixes, Kafka naming, Flyway rules, enum persistence, service tests
  checks/domain_check.py          order state machine (§5), cross-schema SQL (§3)
  checks/protected_paths.py       agent PRs may not touch the controls that judge them
  run_gates.py                    runner + ratchet baseline (fingerprints survive line shifts)
  baseline.json                   26 pre-existing findings (one per rule per line) on broker-dealer@develop
  ci/guardrails.yml ci/critic.yml CI templates (gates + protected paths; headless critic)
  archunit/
eval/
  harness.py                      apply defects → gates → anonymised diffs → score
  data/defects.json               set 1: 50 defects + 15 controls (single change)
  data/defects-heldout.json       set 2: 30 PR-sized defects + 10 controls (held out from gate tuning)
  set1-gates-v1-critic/           set 1: gates v1 + isolated critic verdicts
  set1-gates-v2/ set1-gates-v3/   set 1 re-scored with later gate versions (training)
  set2-gates-v2-critic-judge/     set 2 held-out: gates v2, critic verdicts, judge adjudication
  set2-critic-primed/             bias probe: critic primed with author self-review
  set2-gates-v3/                  set 2 with committed gates (training; see RESULTS)
  RESULTS.md
bench/
  run.py common.py packs/*.py     Stage 2 benchmark per agent (pm ba arch dev code-review qa devops sm doc onboard)
  scope_check.py                  Stage 1 guard: an originator may change only its role's paths
  eval/oms/                       benchmark results on the real OMS (docs drift, secrets)
  README.md
plumbline/
  spec/*.md                       canonical agent specs (single source of truth)
  shared/*.md                     write policy, three-stage protocol, isolated-critic (judge) protocol
  agents/plumbline-critic.md           read-only critic subagent (Claude Code + Copilot .agent.md; /plumbline-critic prompt fallback)
                                  originator subagents are generated from the specs' @originator sections
  build.py                        spec → dist/ (python3 loops/build.py; --check in CI)
  tools/merge_to_spec.py          one-off migration from the drifted Claude/Copilot sets
dist/                             generated — do not edit
packs/domain-rules/  packs/governance/
docs/DECK-CORRECTIONS.md  CHANGELOG.md
security/tool-versions.env.example   pinned scanner URLs + SHA-256 (template)
.github/workflows/self-check.yml     this repo's own CI: dist up to date + gate self-test
selftest/                            gate fixture (`// expect: RULE`), impact fixture, bench fixtures (good/bad per agent)
```

## Not verified in the authoring environment
Maven Central was blocked, so nothing was compiled: ArchUnit tests, the JUnit spec test and the planted defects are unexecuted. The CI workflows are templates. Semgrep gates, the harness and the build script ran end to end.
