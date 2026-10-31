# Smoke test — Plumbline 2.8 in half a day

Stage 1 of the rollout: one person, one real repository, one small feature, end to end. The goal is not to judge
Plumbline's value yet — it is to find what breaks before a team uses it. [TEST-PLAN.md](TEST-PLAN.md) is the full
version for later.

## Before you start (15 min)
- **Repository:** a branch of a real service you know (e.g. broker-dealer), with Plumbline installed from `main`
  (README → Install) and `examples/claude-settings.json` merged. Atlassian connector connected, write tools on **ask**.
- **JIRA + Confluence:** a test project and a Confluence parent page for PRDs and HLDs. Label everything you create
  `plumbline-test`.
- **A small idea** that touches one service and needs 1–3 stories — something you could build by hand in a day.
- Note `claude --version`, the model, and the start time.

## The run (≈ 4 h)
Run each command, approve the writes it asks for, and fill in one row per step. Stop at the first step that cannot
be completed and send what you have.

| # | Run | Look for | Pass when |
|---|---|---|---|
| 1 | `/pl-onboard` (a second run refreshes: unchanged, passing units are kept — no writer) | It asks "Is this the system you meant?"; each unit's `CLAUDE.md` (≤ 6 KB) and `CLAUDE.reference.md`; root `CLAUDE.md` with settings | 10 endpoints/tables you pick at random are real; every Rule is tagged with a real file or class; base branch is your real default; `Workflow` matches your JIRA statuses; *Decisions needed* names any committed secret and any service reachable without the gateway; every unit — frontend included — has its own file |
| 2 | `/pl-pm "<idea>"` | Epic, PRD page with the epic key in its title, `plumbline-prd-approved` | PRD is business-only with a *Today* section; epic pins page version 1 |
| 3 | `/pl-ba <EPIC>` | Stories under the epic, `plumbline-dor-ready`, `Blocks` links | Given/When/Then `AC1`…; criteria for who may **not** do it; no APIs, units or points |
| 4 | `/pl-arch <EPIC>` | HLD page under the PRD, docs PR for CLAUDE.md, epic comment, `plumbline-hld-final` | Units come from your CLAUDE.md, not invented; the docs PR adds only decisions and `[decided <EPIC>]` rules |
| 5 | `/pl-arch <STORY>` | LLD comment, story points set, `plumbline-arch-approved` | Every AC id mapped to a technical check; conforms to the HLD |
| 6 | `/pl-dev <STORY>` | Branch, PR on `pr.md`, story comment; story In Progress → In Review | Tests ran (or the first line says UNVERIFIED); *Design gaps* None; code matches the LLD |
| 7 | `/pl-code-review <branch>` | One text as PR review and story comment | It cites code it read; anything differing from the LLD is a finding |

Then, in order: `/pl-doc <STORY>` (posts the docs text on the PR) → `/pl-dev <STORY>` again (applies it) →
`/pl-code-review` → merge → `/pl-devops <STORY>` (confirms the pipeline deployed to QA) → `/pl-qa <STORY>` (closes it).

## Two deliberate breaks (≈ 20 min)
- Edit one word of the LLD comment, then run `/pl-dev <STORY>` again → must stop: changed after approval.
- In a BA draft, add `POST /api/x` to a criterion and let the command continue → the template check must fail it.

## What to send back
For each step: pass/fail, attempts used (from the hand-over footer), any `STOPPED` line,
and anything you had to fix by hand. Plus: total time, and the one thing that annoyed you most.

| # | Pass / Fail | Attempts | STOPPED / what you fixed by hand |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| Breaks | | | |

**Ready for a team pilot when:** steps 1–7 pass, each within 3 attempts, nothing was written outside its role, and
both breaks are caught.
