# Changelog

## 2.8.1 — 2026-10-29 — approvals that do not depend on JIRA history; ready to test in one go
- **`/pl-approve <KEY> <pm|ba|arch|review|qa>`:** the second person reads the hand-off as the next role will, sees
  any judge FAIL, template failure, open question or page edited since the hand-off, and approves or rejects. It
  posts an `[Plumbline approve /pl-<role>]` comment (template `approval.md`) and, on approval, adds the label. It
  refuses to let the person who ran the step approve it. No writer, no judge: the decision is the person's.
- **Gate no longer depends on reading JIRA's change history:** an approval comment by someone other than `Run by`
  is enough; the change history is the fallback; neither → `STOPPED: cannot verify who approved — run /pl-approve`.
- **Page versions:** when the tools give no page version, commands compare the page's last-modified time; when
  neither is available, the hand-over says later edits cannot be detected (instead of guessing).
- **Doc writer has no shell:** `/pl-doc` saves the diff for it.
- **Every command's Shell rule** now names `check-template.sh`, which 2.8.0 asked them to run.
- **Eval sample** in the 2.8 shape (core + `CLAUDE.reference.md`, rules tagged); `setup-case.sh` merges the two for
  Plumbline before 2.8, so `eval/ab.sh v2.6.0 …` compares commands, not documentation.
- **[TEST-PLAN.md](TEST-PLAN.md):** everything to test 2.8 in one session, in order, with pass conditions and a
  results table. README: `/pl-approve`, and how to give the judge its own model.
- Self-test covers `/pl-approve` (the one command without a judge) and the approval template.

## 2.8.0 — 2026-10-29 — independent judging, templates, Confluence specs, separate approvers, a small CLAUDE.md
Goal: close the gaps an independent critique of 2.7 found against Plumbline's own aims (agents per role, spec-driven,
CLAUDE.md as a cheap source of truth, JIRA/Confluence hand-off, the same output on every project).
- **Judge reads the code around a diff.** For `/pl-dev`, `/pl-code-review` and `/pl-devops` the judge reads the
  changed files, the callers of changed methods/endpoints, their tests and the entities touched, instead of trusting
  CLAUDE.md for what the code does — writer and judge no longer share one unchecked premise. Code that contradicts
  CLAUDE.md is a minor `CLAUDE.md out of date` finding.
- **Fixed severity lines** in the judge (blocker / major / minor, with examples); a gap that predates the work is never
  blocker or major. Aimed at the c2/c4 major-vs-minor swing seen in round six.
- **Templates** for everything posted (`.github/plumbline/templates/`: PRD, epic, story, design, six hand-off
  comments, sprint report), each ending with a `## Record` (version, commit, judge result, Run by, Approval).
  `check-template.sh` checks headings, order, fields and placeholders before every judge and every post — no model,
  no tokens; a failure is the attempt's finding. Acceptance criteria get stable ids (`AC1`, `AC2`, …).
- **Confluence holds the specs.** The PRD and each design are Confluence pages under the new `Confluence parent page`
  setting; the epic and the arch comment carry a summary, the link and the page version. A page edited after approval
  stops the next command (`STOPPED: <page> changed after approval`). Without Confluence, 2.7 behaviour.
- **Separate approver** (new setting, default `yes`): every hand-off records `Run by`; the command never adds its own
  approval label; the next command checks JIRA's change history and stops if the label is missing, self-added or
  unverifiable. `no` keeps 2.7's self-approval, recorded as `self`. SECURITY.md: what this enforces and what needs
  JIRA workflow conditions.
- **Small CLAUDE.md.** Each unit now has a core `CLAUDE.md` (≤ 8 KB: purpose, build/test recipe, architecture,
  security, rules, must-nevers, decisions, reference index) and a `CLAUDE.reference.md` (≤ 30 KB: API, data,
  integrations, config, debt, open questions) opened only for the section a task needs. Rules are tagged
  `[code: <file>]` or `[decided <source>]`. `/pl-doc` adds only durable rules (`[decided <KEY>]`), keeps the core
  under 8 KB and lists proposed removals for the architect; it never deletes a `[decided]` rule.
- **Freshness:** every command checks `git log <Last updated>..HEAD -- <unit>` and tells the helpers and the judge
  which files CLAUDE.md may be stale for.
- **`examples/CODEOWNERS`:** the architect owns `CLAUDE.md` / `CLAUDE.reference.md`.
- **A/B tooling:** `eval/ab.sh <refA> <refB>` runs the code-review eval on two versions (`REPEAT=n`);
  `eval/ab-command.sh` runs any command on your repository with two versions and counts code reads, tokens, cost.
- Shared blocks rewritten shorter so every command stays within the 140-line budget with the new rules.
- **Self-test:** templates exist and carry a Record; `check-template.sh` passes a good draft and fails a broken one;
  stale 2.7 text: 236 checks.
- **Not yet run:** the 2.7/2.8 eval and A/B runs (see TEST-REPORT §6d). Treat 2.8's effect on tokens and false alarms
  as unmeasured until they are.

## 2.7.0 — 2026-10-28 — CLAUDE.md is the single source of truth; JIRA is the hand-off
Goal: agents stop spending tokens rediscovering the project, and roles hand work to each other in one place.
- **CLAUDE.md is the single source of truth.** Every writer and the judge now work from the CLAUDE.md files and the
  JIRA material, and open code only for the files they change, review or must cite. A fact they had to look up is
  reported as `Add to CLAUDE.md: <fact> — <file>`; a CLAUDE.md line the code contradicts as
  `CLAUDE.md out of date: <what> — <file:line>`. The hand-over lists both for `/pl-doc`.
- **`/pl-onboard`** writes two new sections per unit — *Architecture & structure* and *Decisions & trade-offs* (each
  with its source) — plus the same in the root master, and starts each block with
  `Last updated: <commit> (<date>, /pl-onboard)`.
- **`/pl-doc`** (after merge) now writes back the story's business rules (its acceptance criteria) into *Rules*, the
  design's decisions into *Decisions & trade-offs*, and the "Add to CLAUDE.md" notes, and sets `Last updated:` to the
  merge commit. The architect approves the docs PR.
- **JIRA hand-off with one SME per role** (new shared block in nine commands): the PRD is the epic, stories are
  stories, and the design, dev result, review verdict and QA evidence are `[Plumbline /pl-<role>]` comments on the
  story. Each SME approves with a label — `plumbline-prd-approved`, `plumbline-dor-ready`, `plumbline-arch-approved`,
  `plumbline-review-passed`, `plumbline-qa-passed` — and the next command stops with `STOPPED: <label> not on <KEY>`
  until it is there. Commands read the ticket and the latest comments instead of redoing earlier work; drafts are
  scratch only and no command reads another's drafts.
- **Removed:** the feature tracker, `context.md` and the "changed since verified" diff (replaced by the above).
- **Eval scorer:** a finding naming a class without `.java` now matches; only a finding's own severity label counts.
- **`eval/run.sh`:** a case whose run fails (e.g. a usage limit) is reported as not scored instead of "0 found".
- **Self-test:** checks the new JIRA hand-off block is identical everywhere and that the removed mechanisms are not
  mentioned: 209 checks.

## 2.6.0 — 2026-10-28 — check it yourself: public eval set, team test plan, time in metrics
- **Eval set** (`eval/`): an original sample service (Order Desk) and ten pull requests — five with 13 planted
  defects and an answer key, plus a decoy; five clean changes. `setup-case.sh` builds any case as a git repo for
  Claude Code or Copilot; `score.py` scores a saved review (recall, false alarms, decoy); `run.sh` runs all ten
  headless; `check-cases.sh` compiles and tests the cases. First run published in `eval/published/`: **13/13 found,
  0 false alarms, decoy untouched, $1.78**.
- **TEAM-TEST.md:** a half-day plan for teams to test Plumbline on the eval set and on their own repository, with
  Copilot-specific checks and a results table.
- **Metrics:** `minutes` per run in `.plumbline-drafts/metrics.csv`; `/pl-sm metrics` shows the median. The example
  settings allow `date +%s`.
- **Self-test** now also checks every eval case applies and every doc link (incl. TEAM-TEST, eval README) resolves:
  202 checks.

## 2.5.0 — 2026-10-28 — release hardening
No new commands or tools; the same markdown commands, agents, settings and CI, made safer to run and to release.
- **"Every run" rules in all ten commands** (one shared block, kept identical by the self-test): a judge reply that
  is not the expected JSON is asked again once, then counted as FAIL — the orchestrator never decides PASS itself;
  max 3 attempts per item and a yes before more than 6 items; a defined behaviour for unattended runs; one hand-over
  format whose first line is `PASS`, `FAIL after 3 attempts`, `STOPPED: <reason>` or `UNVERIFIED: <what did not run>`.
- **Judge:** every checklist item now says what was checked; an item that could not be checked is FAIL, never PASS.
- **`FILE: <path>` fallback** only writes to a path the command gave that helper; anything else is a finding.
- **Self-test** `tests/validate.sh` (+ `plumbline-selftest.yml` in CI, skipped in your projects): command structure,
  Copilot pointers, agents named exist, shared blocks identical, stale names, settings sanity (no rule both allowed
  and denied, dangerous git denied, push asks), version, links, workflow syntax. Negative-tested: 4 planted breaks,
  4 caught.
- **Release docs:** README rewritten (status per platform, install with permissions as a standard step, upgrade,
  remove); new [SECURITY.md](SECURITY.md) (what is enforced vs only instructed, threats); new
  [RELEASING.md](RELEASING.md) (checklist); `.github/plumbline/VERSION`.
- `/pl-sm` metrics mode moved to its own section; CI protects the self-test workflow too.
- **Tested** (permissions on, transcripts kept): blind code review 8/8 (third run); arch PASS; unattended QA
  stopped correctly; two negative cases 3/3 each, including a planted secret. `TEST-REPORT.md` section 6a.

## 2.4.1 — 2026-10-28 — independent critique applied
- Test report corrected (all runs used `claude-sonnet-5-5`; the "second model" test was a repeat), evidence status
  stated, tighter example permissions, onboarding one unit at a time. See TEST-REPORT.md section 7.

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
- **Drafts folder ignores itself** (`.plumbline-drafts/.gitignore` = `*`): Claude Code protects `.git/`, so commands no
  longer edit `.git/info/exclude`. Commands create files only with the write tool; onboarding runs tests as
  `cd <unit> && <command>`; the example settings allow `java -version` / `node -v`.
- **After an independent critique:** report corrected (all runs used `claude-sonnet-5-5`, so the "second model" test
  was a repeat; onboarding, BA and QA rows made exact; evidence status stated). Example settings now deny reading
  `*-prod*` / `*-local*` config, deleting branches, `reset`, `checkout`, `restore`, `rebase`, `commit --amend` and
  `git -C`; `git push` always asks. Onboarding helpers run one unit at a time.
- **Tested:** onboarding records real test results and 6 decisions; a prompt-injection branch is failed and the
  injection reported; a repeat of the blind 8-defect review scores 8/8 again (same model — see the correction in the report). `TEST-REPORT.md` section 6.

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
