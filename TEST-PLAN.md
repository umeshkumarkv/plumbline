# Test everything in one go — Plumbline 2.8

> First time? Start with the half-day [SMOKE-TEST.md](SMOKE-TEST.md); this is the full plan for after it.

One session, in this order: each part sets up the next. About a day. Record each row's result in the table at the end
and send it back with the hand-overs (copy the text) and any `STOPPED` lines.

## Before you start
- **Repository:** a fresh clone of a test copy of a real service (e.g. broker-dealer). Never one holding production
  secrets you have not denied (SECURITY.md).
- **JIRA + Confluence:** a *test* JIRA project, and a Confluence space with a page to hold PRDs and HLDs (the
  `Confluence parent page`). The Atlassian connector connected in Claude Code; its write tools on **ask**.
- **People:** one per role is ideal (PM, BA, architect, developer, QA); one person playing every role also works.
- **Install:** copy `.claude` and `.github` from Plumbline `main` (README → Install), merge
  `examples/claude-settings.json`. Note `claude --version` and the model.

## Part 1 — no JIRA needed (≈ 1 h, ≈ $15 in API usage)
| # | Run | Pass when |
|---|---|---|
| 1.1 | `bash tests/validate.sh` (in the Plumbline clone) | all checks pass |
| 1.2 | `REPEAT=3 bash eval/ab.sh v2.6.0 v2.8.1` | 2.8.1: recall 13/13 in every run, false alarms ≤ 2.6's, decoy never flagged |
| 1.3 | `bash eval/ab-command.sh v2.6.0 v2.8.1 <your repo> "/pl-ba <a requirement in plain English>"` | 2.8.1 makes clearly fewer Read/Grep/Glob calls and uses fewer tokens; reading both, the stories are as good |

## Part 2 — onboarding (≈ 30 min)
| # | Run | Pass when |
|---|---|---|
| 2.1 | `/pl-onboard` (answer: JIRA project, Confluence space, parent page, base branch) | each unit has `CLAUDE.md` ≤ 6 KB and `CLAUDE.reference.md` ≤ 30 KB; every Rule is tagged `[code: …]` or `[decided …]`; 10 spot-checked endpoints/tables are real; the settings hold all values. Commit it on a branch. |

## Part 3 — one feature end to end (≈ 4 h)
Use one small real backlog idea. After each step, open JIRA and Confluence and look at what was posted.

| # | Run | Pass when |
|---|---|---|
| 3.1 | `/pl-pm "<idea>"` | a Confluence PRD page under the parent page, business-only, with a *Today* section; the epic links it with its version; after your yes, `plumbline-prd-approved` |
| 3.2 | `/pl-ba <EPIC>` | stories in business language: *Today*, Given/When/Then `AC1`…, no APIs/units/points (plant an API path in a draft: the template check fails it); `plumbline-dor-ready` |
| 3.3 | `/pl-arch <STORY>` before the HLD | stops: `plumbline-hld-final` not on the epic |
| 3.4 | `/pl-arch <EPIC>` | an HLD page under the PRD (units, interactions, data ownership, cross-cutting, story design order); a docs PR adding only its decisions and `[decided <EPIC>]` rules to CLAUDE.md; an epic comment with the page link, version and PR; `plumbline-hld-final` |
| 3.5 | `/pl-arch <STORY>` | an LLD comment conforming to the HLD: unit, blockers, story points (field set), every AC id mapped to its technical check; `plumbline-arch-approved` |
| 3.6 | edit one word of the LLD comment, then `/pl-dev <STORY>` | stops: changed after approval — re-run `/pl-arch` |
| 3.7 | `/pl-dev <STORY>` | a branch; the comment maps every AC id to a test; *Design gaps* None; tests ran (or the first line says UNVERIFIED) |
| 3.8 | `/pl-code-review <branch>` | cites code it read (callers, tests); any difference from the LLD is a major finding |
| 3.9 | `/pl-qa <STORY>` with the system running | evidence per AC id, checked as the LLD maps it; stops cleanly if the system is not reachable |
| 3.10 | merge the branch in your clone, then `/pl-doc <STORY or PR>` | only durable rules as `[decided <STORY>]`, the LLD's Decisions, the "Add to CLAUDE.md" notes; core ≤ 6 KB |

## Part 4 — deliberate breakage (≈ 1 h)
| # | Do | Pass when |
|---|---|---|
| 4.1 | Change a line in code that CLAUDE.md describes (e.g. an endpoint's role), commit, then `/pl-code-review` a branch touching that file | the judge flags the defect from the code and adds `CLAUDE.md out of date`; every command warns "CLAUDE.md may be stale for: …" |
| 4.2 | Hand-edit a hand-off draft to drop a heading, then let the command continue | the command's Template check fails it before any judge runs |
| 4.3 | Give `/pl-dev` a story whose LLD cannot be built as written (e.g. names a method that cannot exist) | stops: `design gap — /pl-arch <KEY>`; no workaround in the code |
| 4.4 | Edit one word of the PRD page, then `/pl-ba <EPIC>` | stops: PRD page changed after approval |

## Results (copy into your reply)
| # | Pass / Fail | What happened (one line; paste the STOPPED line or hand-over first line) |
|---|---|---|
| 1.1 | | |
| … | | |

Most useful to send back if something fails: the command, its full hand-over, and what JIRA/Confluence show.
