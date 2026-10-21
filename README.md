# Plumbline

**Governed agentic SDLC for existing codebases.** Plumbline puts AI agents (Claude Code, GitHub Copilot) through the
whole delivery cycle — onboarding, PRD, story, design, code, review, QA, docs, CI fixes — and checks every step against
true vertical: a deterministic benchmark first, then an isolated judge, with a human approving every external write.

## Quickstart — try it on an existing repository

Takes about 10 minutes plus one onboarding run. Uses a separate worktree on a new branch, so your main checkout is
untouched and the branch is something you can share as a PR.

### 1. Prerequisites (once per machine)
```bash
python3 -m pip install --user pyyaml     # Python 3.10+
brew install semgrep                     # or: pipx install semgrep — without it only the Semgrep-based checks are skipped
```
Plus the project's own toolchain (JDK for Maven/Gradle projects, node for frontends) and Claude Code or VS Code with
GitHub Copilot (Agent mode).

### 2. Trial branch
```bash
cd <your-repo>
git worktree add ../<your-repo>-plumbline-trial -b plumbline-trial
cd ../<your-repo>-plumbline-trial
```

### 3. Install
```bash
TAR=/path/to/plumbline-<version>.tar.gz
tar -xzf "$TAR" .plumbline/init.py
if [ -d .agentic-sdlc ] || [ -d .plumbline/loops ]; then
  python3 .plumbline/init.py --upgrade "$TAR"     # existing install (also migrates the pre-1.10 .agentic-sdlc folder)
else
  tar -xzf "$TAR" && python3 .plumbline/init.py --domain none
fi
```
`--domain none` = generic rules only. Use `--domain broker-dealer` for the shipped OMS pack. Add `--ci` to also install
the GitHub workflows (`.github/workflows/plumbline-*.yml`).

### 4. Verify
```bash
python3 .plumbline/init.py --doctor      # units, endpoints, frontend calls, JDK, warnings
python3 .plumbline/init.py --check       # must pass
for t in .plumbline/selftest/*_selftest.py; do python3 "$t"; done
git status --short                       # new files only under .plumbline/, .claude/, .github/
```
Installed Semgrep after step 3? Run `python3 .plumbline/init.py --rebaseline` once.

### 5. Onboard
- **Claude Code:** `claude` in the trial folder → `/plumbline-onboard service:all`
- **Copilot:** open the trial folder, Chat in **Agent** mode → `/plumbline-onboard service:all`

Expect originator → benchmark → judge per unit, up to 3 attempts before it hands over to you. CLAUDE.md files are
merged between `plumbline:begin/end` markers, never overwritten: one master at the root, one per unit (`src/CLAUDE.md`
for an app at the repository root).

### 6. Share
```bash
git add .plumbline .claude .github $(git ls-files -mo --exclude-standard -- '*CLAUDE.md')
git commit -m "Trial: Plumbline $(cat .plumbline/VERSION) onboarding"
git push -u origin plumbline-trial        # then open a PR: it shows exactly what Plumbline adds
```

### Clean up
```bash
cd <your-repo> && git worktree remove ../<your-repo>-plumbline-trial
# or keep the branch and remove Plumbline from it: python3 .plumbline/init.py --uninstall --yes
```

### Next roles
`/plumbline-pm`, `-ba`, `-arch`, `-dev`, `-code-review`, `-qa`, `-doc`, `-devops`, `-sm` — same three-stage loop,
each scoped to its own paths. Every external write (JIRA, PR, push) waits for human approval.

**What `init.py` does:** detects the units (`services/<name>/`, top-level modules, an app at the root, frontends such as `ui/`), the Java version, the frontend framework and the base branch; writes `.plumbline/project.yaml`; installs the generated Claude Code commands/agents and Copilot prompts/agents (and the CI workflows with `--ci`); writes the gate baseline; checks prerequisites; prints a **doctor** report. `--doctor` reports only, `--check` (CI) fails on drift, `--upgrade <tarball>` replaces the framework and keeps `project.yaml` and the baseline.

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

## Footprint in a project

Everything Plumbline owns lives in **`.plumbline/`**: the framework, `project.yaml`, the gate baseline, and the loop
working files in `.plumbline/run/` (ignored by `.plumbline/.gitignore`; the root `.gitignore` is not touched).
Outside it, only the entry files the tools require, all named `plumbline-*`:
`.claude/commands`, `.claude/agents` (Claude Code), `.github/prompts`, `.github/agents` (Copilot), and
`.github/workflows` only with `init.py --ci`. `init.py --uninstall --yes` removes all of it; the project's CLAUDE.md
files stay. Commands: `/plumbline-onboard`, `/plumbline-pm`, `/plumbline-ba`, `/plumbline-arch`, `/plumbline-dev`,
`/plumbline-code-review`, `/plumbline-qa`, `/plumbline-doc`, `/plumbline-devops`, `/plumbline-sm`.

CI runs the checks from `.plumbline/` **as committed on the base branch**, so a PR cannot change the checker that
judges it. Building a release here: `python3 tools/make_kit.py` → `build/kit/.plumbline/`.
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
loops/
  spec/*.md                       canonical agent specs (single source of truth)
  shared/*.md                     write policy, three-stage protocol, isolated-critic (judge) protocol
  agents/plumbline-critic.md      read-only critic subagent (Claude Code + Copilot .agent.md; /plumbline-critic prompt fallback)
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
