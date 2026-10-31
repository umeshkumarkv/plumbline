# Changelog

## 2.8.15 — 2026-10-31 — close-out: dry-run install verified
- **Dry run of the install** (copy `.claude/commands`, `.claude/agents`, `.github/plumbline` into an empty project) found
  one broken pointer: every command referred to `OPERATING-MODEL.md`, which was not installed. It now lives at
  `.github/plumbline/OPERATING-MODEL.md`. Result: 45 files, all markdown, every reference resolves.
- Self-test now repeats that dry run on every change (every file a command or agent points to must be in the install)
  and checks the flow: every label a gate waits for is added by an earlier step.
- Example keys in command hints are neutral (`PROJ-12`), not a real-looking project.

## 2.8.14 — 2026-10-31 — the operating model
Implements [OPERATING-MODEL.md](.github/plumbline/OPERATING-MODEL.md), agreed with the team lead, and nothing else.
- **Flow:** dev → doc → code review → merge → CI/CD deploys to QA → devops → QA → Done. `/pl-doc` runs on the **open
  PR** and posts the exact CLAUDE.md / API-spec text (PR comment + story comment, `plumbline-docs-ready`); `/pl-dev`
  (apply mode) applies it word for word in the same PR; `/pl-code-review` needs `docs-ready` and checks code and docs
  together (item 12). `/pl-devops` after a merge confirms the pipeline deployed to QA (`handoff-deploy`,
  `plumbline-deployed-qa`); QA tests that deployment and **closes the story**. A failing pipeline or CI run becomes exact
  fix text for dev.
- **Nothing travels through anyone's folder:** the HLD's CLAUDE.md additions are exact text in the epic comment, applied
  by dev in the epic's first story PR; the arch writer edits no repository file.
- **SME approval is explicit:** "Your yes approves this as the <role> SME. JIRA will show you as the person who posted it."
- **Metrics in JIRA:** every hand-off footer records attempts, minutes and `SME edited`; `/pl-sm metrics` reads JIRA;
  `metrics.csv` is gone.
- **Any git host:** GitHub, GitLab or Bitbucket — "the git host's connector"; PR means PR or MR.
- **Markdown-only install:** `VERSION` → `VERSION.md`; the template lock moved to `tests/`; the optional GitHub Actions
  check moved to `examples/ci/`. Install = `.claude/commands`, `.claude/agents`, `.github/plumbline` — all `.md`.
  **Copilot on hold** (its files stay in the repository, not in the install).
- `/pl-dev` names branches by the *Branch pattern* setting (it had hard-coded `ai/<KEY>-<slug>`).
- Templates: every hand-off template v2 (footer metrics; exact-text hand-offs); new `handoff-deploy` v1.

## 2.8.13 — 2026-10-31 — only dev and code review use git
- `/pl-dev` creates the branch and the PR; `/pl-code-review` reads it and writes the review. **No other command runs
  git or `gh`:** `/pl-onboard`, `/pl-pm`, `/pl-ba`, `/pl-arch`, `/pl-qa`, `/pl-doc`, `/pl-devops` and `/pl-sm` work on the
  code already in the folder. Their changes (CLAUDE.md files, docs, a CI fix) stay in the folder with a PR description
  on `pr.md` in drafts — the user commits. CI logs and PRs are read through the connected GitHub tools.
- Without git: units are found with file search; the base branch is asked; scope checks use the writer's list of
  changed files; the judge compares against copies saved in drafts (`before/`); footers and `Last updated` use commit
  `—`; the freshness check is gone (`/pl-doc` keeps CLAUDE.md current after each merge).
- Agents: the devops fixer and QA runner run no git; the judge runs read-only git only for dev and code review.
- Self-test fails if any command other than `/pl-dev` and `/pl-code-review` runs git or `gh`.

## 2.8.12 — 2026-10-30 — markdown only, again
Plumbline is a framework of markdown files that runs the same on macOS, Windows and Linux. 2.8.0 had added
`check-template.sh` and 2.8.11 `onboard-audit.py` — both executables in your project. Both are gone:
- The **Template check** is a written procedure in `.github/plumbline/templates/README.md` that every command does
  itself before the judge and before posting (headings, fields, placeholders, footer and version, role lane).
- The **onboarding audit** is a judge checklist, `.github/plumbline/checklists/onboard-audit.md`: every unit, every
  check (endpoints, tables, topics, tags, silent header defaults, pass-through filters, CORS, reachability, recipes
  that ran, security risks reaching the root), no sampling, all failures in one list in the summary.
- The permission allow-list no longer names any script. The self-test fails if anything but markdown (plus `VERSION`
  and the optional CI `.yml`) is ever installed into a project; the template checker lives on in `tests/` for
  Plumbline's own maintainers only.

## 2.8.11 — 2026-10-30 — onboarding audits itself: every gap in one run
- **`onboard-audit.py`** (deterministic, no model) runs after each writer and before the root judge: endpoints in code
  vs docs (full paths), tables in migrations, Kafka topics, `[code: …]` tags that name missing files, `X-User-*`
  headers with silent defaults, filters that pass requests without a role header, CORS open to any origin,
  docker-compose ports vs "Reachable without that check", test recipes that did not run, and unit security risks
  missing from the root. Its FAIL lines are the next attempt's findings; the summary prints whatever remains, in one
  list. On OMS PR #3 it reports exactly the three open issues (frontend recipe, marketdata pass-through, risk-service
  `SYSTEM` default) and nothing else.
- Test recipes are reused only if they actually ran (2.8.10 reused a "NOT RUN" recipe).
- Unit writers mark each risk as `Security risk:`; every one must be in the root's *Decisions needed*.
- Self-test: the audit passes the eval sample and catches a removed endpoint.

## 2.8.10 — 2026-10-30 — cheap re-runs; security and conventions enforced by templates; existing docs checked
From the second review of OMS PR #3 and the comparison with the original broker-dealer CLAUDE files.
- **Refresh mode (cost).** A re-run of `/pl-onboard` no longer rewrites everything: a unit whose files pass the template
  check, with no code change since `Last updated`, gets the judge only and is **kept** if it passes — no writer. Other
  existing units get the writer in **update mode** (keep what is true, fix what failed, add what the template now
  requires). Test recipes are **reused** unless a build file changed. The summary shows each unit's mode.
- **Security as template fields** (`claude-unit` v2): `Identity`, `Verified at`, `Reachable without that check` per
  environment — the checker fails a file without them, with no model involved. The judge reads the deploy files
  (docker-compose, k8s, Helm); "the gateway is the trust boundary" alone fails.
- **`claude-root` v3:** required `Secrets found` field in *Decisions needed*; new **Conventions** section (money, errors,
  logging, naming, tests — from docs or consistent code patterns, with sources).
- **Existing docs are checked:** the team's text outside the markers is kept; every technical claim the code
  contradicts is reported as "Docs vs code" and listed in *Decisions needed*; conventions still true become
  `[decided docs: <file §section>]` rules.
- **Test recipes run:** the project's own dependencies may be installed from its lockfile (`npm ci`, Maven/Gradle
  downloads) — never tools or runtimes; the recipe names the runtime the build requires when a different one ran.
- **Onboarding checklists are files** (`.github/plumbline/checklists/`), read by the judge; `/pl-onboard` 140 → 113 lines.

## 2.8.9 — 2026-10-30 — onboarding finds security risks, every unit, and stays small (from OMS PR #3)
Review of the first real Claude Code onboarding (OMS PR #3): accurate and deep, but it missed every security risk,
skipped the frontend, changed a Dockerfile, committed drafts, and filled each core file to 8 KB.
- **Security:** onboarding scans for committed secrets (file and key — never a value; placeholders ignored) and each
  unit's Security section must say how identity reaches the unit, where it is verified, and whether the unit is
  reachable without that check (published ports, k8s Service type). Both go into the root's *Decisions needed*, and a
  security item cannot be settled by an answer alone — it stays listed until the code no longer has it.
- **Every unit:** every folder with its own build file and source is a unit, frontend included; skipping one needs the
  user's yes, recorded; the root judge checks every unit has its file.
- **Scope check in onboarding:** only the unit's CLAUDE.md files may change; anything else is reverted and is a finding.
- **Drafts never committed:** restored the `.plumbline-drafts/.gitignore` rule in every command (2.8.0 dropped it from
  `/pl-onboard`, `/pl-dev`, `/pl-doc` and `/pl-code-review` when the shared block was shortened); self-test guards it.
- **Smaller always-loaded files:** unit core at most 6 KB (was 8), root at most 10 KB; detail goes to the reference.

## 2.8.8 — 2026-10-28 — tickets move with the work; /pl-doc closes; fixes from the sample and OMS runs
- **JIRA status transitions.** New `Workflow` setting (your status names for To Do → In Progress → In Review → Done),
  proposed by `/pl-onboard` from the project's real statuses. `/pl-dev` → In Progress at start (the epic with its first
  story) and In Review with the PR; a `/pl-code-review` or `/pl-qa` FAIL → In Progress; **only `/pl-doc` → Done**, after
  merge and `plumbline-qa-passed` (the epic with its last story), so docs are never skipped. Moves go through JIRA's
  transitions as part of the hand-over the SME approves; a refused transition is reported, never forced. `/pl-sm`
  flags tickets whose status and labels disagree.
- **Freshness:** CLAUDE.md's own edits no longer make it "stale" (`':!**/CLAUDE*.md'`) — every run after an onboard,
  doc or HLD update raised a false alarm.
- **`/pl-dev`:** no longer offers to continue without CLAUDE.md (2.8.7 stops instead).
- **`/pl-arch`:** the HLD and Design checklists check the unit's **Must never**, not only the root rules; a list or
  query the Must never limits states its bound and why it holds.
- **`/pl-onboard`:** suggests the base branch from the repository's real default (`origin/HEAD` — the OMS default was
  `develop`), proposes `Workflow`, and asks "Is this the system you meant?" before finishing — a no stops the run.
- **Template `claude-root` v2** (adds `Workflow`) — the first template version bump: lock and template CHANGELOG
  updated; v1 root files still read.

## 2.8.7 — 2026-10-28 — fixes from the OMS run; half-day smoke test
Fixes from the first model-followed run (TEST-REPORT §6f):
- No root CLAUDE.md → every command except `/pl-onboard` stops first: `STOPPED: run /pl-onboard first`.
- `/pl-pm` creates the epic first and titles the PRD page with its key from the start; it never renames the page after
  the epic pins its version.
- "Edited after it was posted" now covers descriptions (changed in the issue history after the label was added) and
  pages, not only comments.
- `/pl-ba`: stories from the PRD's P1 unless the user names other priorities; created in dependency order with
  "story <n>" replaced by keys; the architect (not the team) sets points.
- Design checklist tidied (no item dropped).
- **SMOKE-TEST.md:** the half-day Stage 1 run — 7 steps, 2 deliberate breaks, what to send back, and the bar for a
  team pilot.

## 2.8.6 — 2026-10-28 — every output templated, and templates versioned
- **No untemplated output left.** New templates: `pr.md` (every PR description — story, docs, CI fix), `sm-flag.md`
  (each flagged ticket's comment), and `claude-root.md`, `claude-unit.md`, `claude-reference.md` (the CLAUDE.md files,
  written by `/pl-onboard`, `/pl-doc` and `/pl-arch <EPIC>`). `/pl-code-review` posts one `handoff-review.md` text as
  both the PR review and the story comment. Commit messages are `<KEY>: <summary>`.
- **Template versions.** Every template starts with `<!-- plumbline:template <name> v<N> -->`; every output names the
  version it was written on (hand-off footer `· story v1 ·`; CLAUDE.md `Last updated: … (…, /pl-onboard, claude-unit v1)`)
  and `check-template.sh` fails it otherwise. `templates/VERSIONS` locks version to content (sha256): the self-test
  fails a template changed without a new version. `templates/CHANGELOG.md` records each version; commands read older
  hand-offs as written. Everything starts at v1; 2.8.0–2.8.5 output reads as v1. `tests/lock-templates.sh` re-locks.
- Every command's Every-run rule covers JIRA, Confluence, PR descriptions and reviews, and CLAUDE.md files; the JIRA
  hand-off table names every template; the self-test checks each command names its templates and that the eval
  sample's CLAUDE.md files pass theirs (headings now unnumbered, as the templates).

## 2.8.5 — 2026-10-28 — the HLD is a Confluence page, and its decisions go into CLAUDE.md
- `/pl-arch <EPIC>` publishes the HLD as a Confluence page under the PRD (template `hld.md`), adds its decisions
  (*Decisions & trade-offs*) and rules (*Rules*, `[decided <EPIC>]`) to the CLAUDE.md files through a docs PR the
  architect owns, and posts a short epic comment (`handoff-hld.md`: page link and version, summary, docs PR).
  Nothing that does not exist in code yet goes into CLAUDE.md — `/pl-doc` adds endpoints and tables after merge.
- The arch writer may edit CLAUDE.md for an HLD (Rules and Decisions only); a scope check allows only CLAUDE.md
  changes, and the HLD checklist (item 6) fails anything else.
- `/pl-arch <STORY>` is unchanged: the LLD is a story comment.
- Commands read the HLD from the page the epic comment links, pinned to its version; an HLD page edited after it was
  posted stops the next command.

## 2.8.4 — 2026-10-28 — the architect's design is final; the SME's yes is the approval
- **HLD and LLD.** `/pl-arch <EPIC>` writes the HLD (units and responsibilities, interactions, data ownership,
  cross-cutting rules, story design order, decisions) as a comment on the epic, labelled `plumbline-hld-final`;
  `/pl-arch <STORY>` writes the LLD, which must conform to the HLD, and needs `plumbline-hld-final` on the epic. The
  architect sets story points and technical-blocker links when the LLD is posted.
- **The design is final.** Dev, code review, devops (and QA, doc) follow the HLD and LLD exactly. The dev checklist
  no longer accepts a "justified deviation"; a role that cannot follow the design stops with `design gap — /pl-arch
  <KEY>`; code review fails any difference from the design (new item 11). `handoff-dev.md`: *Deviations* →
  *Design gaps* (None).
- **`/pl-approve` and `Separate approver` removed.** Every command already posts only after its SME's yes, with the exact
  text shown; JIRA records who. Each command adds its own label on that yes. A second person is still required where
  it matters — the PR approval enforced by GitHub branch protection. The "edited after it was posted" check stays.
- **PM and BA may read code** (Read, Grep, Glob, Write) to learn what exists today — CLAUDE.md and the reference
  file first, code only to confirm one behaviour — and write it in business terms in a new `## Today` section of the
  PRD and the story. What they write stays business-only (the template check and judge are unchanged).

## 2.8.3 — 2026-10-28 — every role in its lane; business SMEs approve business content only
- **PM and BA write business language only.** The PRD describes behaviour, success criteria and scope with a sized
  backlog (S/M/L); stories are a user story, Given/When/Then criteria (`AC1`…), examples, out of scope and business
  dependencies. "Context for the developer" and "Tech constraints" are gone from the story.
- **The architect owns the technical side:** the design comment gains *Ownership and estimate* (the unit, technical
  blockers, suggested points) and maps each AC to how it is checked technically (QA tests against that mapping).
  The team sets story points when `/pl-approve <KEY> arch` runs, which also adds the blocker links. Branch pattern and
  PR target come only from the repository settings.
- **Guards:** every writer has a *Your lane* section (owns / never); the judge fails work outside the lane (major,
  "outside role"); templates carry a `plumbline:forbid` pattern and `check-template.sh` rejects lines other roles own
  (API paths, status codes, class names, points in a PRD or story; production code in a design) — no model involved;
  the PM, BA and SM writers' tools are `Read, Write` only (no search: they cannot survey code); the arch writer cannot
  edit files.
- **`## Record` replaced by one footer line:** `— Plumbline <version> · /pl-<command> · commit <sha> · judge <result> ·
  AI-drafted, posted after SME review`. Who posted and who approved are taken from JIRA (comment author, issue
  creator), not typed in; the self-approval check uses the author.
- Self-test: role check (business story passes, API path + points fail), lanes present, PM/BA/SM tool lists.

## 2.8.2 — 2026-10-29 — hand-offs in JIRA; Confluence only for the PRD
- The design is the full `[Plumbline /pl-arch]` comment on the story again (template `handoff-arch.md`, which now holds
  all design sections; `design.md` removed). Every hand-off is a JIRA ticket or comment; the PRD is the only Confluence
  page, linked and version-pinned from the epic.
- A hand-off comment edited after its approval stops the next command, as an edited PRD page does.
- A comment must stay under 30,000 characters (JIRA's limit 32,767); longer → split the story.
- **From the live test on OMS** (TEST-REPORT §6e): template fields are bullets (`- Label: value`), because Confluence
  and JIRA merge plain lines into one paragraph; `check-template.sh` accepts `-` and `*` bullets (JIRA returns `*`)
  and ignores the backslashes JIRA and Confluence add on read-back (`\[Plumbline …\]`, `\~`); commands ignore those
  backslashes when they look for `[Plumbline …]` comments.

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
