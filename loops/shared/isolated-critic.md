#### Stage 3 — Judge: isolated critic (the author never grades its own work)

The checklist in this step is the **rubric**. You (the author) do not mark it. An independent critic does.
Run this stage only when the Stage 2 benchmark verdict is PASS (see *Three stages* above).

<!-- @claude -->
1. Write the artifact to a file. For code, include uncommitted and new files:
   `mkdir -p .plumbline/run/review && git add -A -N && git diff develop -- . ':!.plumbline' > .plumbline/run/review/{ticket}-attempt.diff` — then assert the file is non-empty.
   (In the code-review loop the artifact is the PR diff from the pinned review worktree — see its Phase 0.)
   For a design/story/PRD/draft, write the markdown to `.plumbline/run/review/{ticket}-{artifact}.md`.
   Facts the critic cannot read itself (JIRA blocker status, labels) go into a short `FACTS` header at the top of the artifact file,
   stated as data (ticket keys + statuses), never as conclusions.
   For a code artifact that touches `services/`, also write the **impact bundle** (deterministic; which other
   services consume or call what changed, with the counterpart files):
   `python3 "${PLUMBLINE_HOME:-.plumbline}/impact/impact.py" --repo . --base develop --cache ~/.cache/plumbline-impact --json .plumbline/run/review/{ticket}-impact.json --bundle .plumbline/run/review/{ticket}-impact.md`
   (in a working tree with uncommitted changes, commit to a scratch branch first or use `--base-dir`/`--head-dir`).
   Write this step's checklist to `.plumbline/run/review/{ticket}-rubric.md`: the item lines only, with any line naming the attempt
   number (e.g. `… — Attempt {attempt}`) removed. This file is the rubric the critic applies.
2. Invoke the `plumbline-critic` subagent with the Agent tool. Pass **only**: the artifact path, the rubric name, the rubric file path, rulebook paths (root `CLAUDE.md`, the service `CLAUDE.md`, and the domain pack — see *Domain pack* below), the impact bundle path when there is one, the **benchmark report** `.plumbline/run/review/{name}-benchmark.md` as `BENCHMARK`, and (from attempt 2) the prior finding ids with their locations. Never pass anything from `.plumbline/run/work/`.
   **Never pass** your reasoning, your earlier drafts, the attempt number, or what you think the verdict should be.
<!-- @end -->
<!-- @copilot -->
1. Write the artifact to a file. For code, include uncommitted and new files:
   `mkdir -p .plumbline/run/review && git add -A -N && git diff develop -- . ':!.plumbline' > .plumbline/run/review/{ticket}-attempt.diff` — then assert the file is non-empty.
   (In the code-review loop the artifact is the PR diff from the pinned review worktree — see its Phase 0.)
   For a design/story/PRD/draft, write the markdown to `.plumbline/run/review/{ticket}-{artifact}.md`.
   Facts the critic cannot read itself (JIRA blocker status, labels) go into a short `FACTS` header at the top of the artifact file,
   stated as data (ticket keys + statuses), never as conclusions.
   For a code artifact that touches `services/`, also write the **impact bundle** (deterministic; which other
   services consume or call what changed, with the counterpart files):
   `python3 "${PLUMBLINE_HOME:-.plumbline}/impact/impact.py" --repo . --base develop --cache ~/.cache/plumbline-impact --json .plumbline/run/review/{ticket}-impact.json --bundle .plumbline/run/review/{ticket}-impact.md`
   (in a working tree with uncommitted changes, commit to a scratch branch first or use `--base-dir`/`--head-dir`).
   Write this step's checklist to `.plumbline/run/review/{ticket}-rubric.md`: the item lines only, with any line naming the attempt
   number (e.g. `… — Attempt {attempt}`) removed. This file is the rubric the critic applies.
2. Run the **`plumbline-critic`** subagent (`#agent/runSubagent`, agent name `plumbline-critic`, defined in
   `.github/agents/plumbline-critic.agent.md`: clean context, read and search tools only). Pass **only**: the artifact path,
   the rubric name, the rubric file path, rulebook paths (root `CLAUDE.md`, the service `CLAUDE.md`, and
   the domain pack — see *Domain pack* below), the impact bundle path when there is one, the
   **benchmark report** `.plumbline/run/review/{name}-benchmark.md` as `BENCHMARK`, and (from attempt 2) the prior finding ids with
   their locations. Never pass anything from `.plumbline/run/work/`, your reasoning, drafts, the attempt number or a verdict to aim for.
   - **If this VS Code cannot run subagents:** ask the user to open a **new** Copilot chat and run `/plumbline-critic` with
     the same inputs, then paste back its JSON. A review done in this same chat is **self-attested**: label it so in every
     JIRA/PR comment; it cannot satisfy a gate.
   - **Additionally, for PR code:** the `plumbline-critic` CI job (`gates/ci/critic.yml`) re-reviews the pushed PR diff.
<!-- @end -->
3. Check the critic's evidence before using it: for each `location` finding, confirm the quoted text exists at that path and line. Drop findings whose quote does not match, and note them as `discarded (evidence mismatch)` in the scorecard.
4. Use the critic's `items` as this step's PASS/GAP results and its `findings` as the attempt's gaps. Feed the optimizer only the findings (rule, location, fix), never the critic's free-text reasoning.
5. On the final attempt the critic runs again on the final artifact (verifier pass). The loop only passes if that run is PASS.

**Domain pack.** If `.plumbline/project.yaml` has `domain_pack:`, pass that path (or no pack when it says `none`).
Without a project.yaml, the domain pack is `none`.
Never apply another domain's rules to this repository.
