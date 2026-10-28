# Test everything in one go — Plumbline 2.8

One session, in this order: each part sets up the next. About a day. Record each row's result in the table at the end
and send it back with the hand-overs (copy the text) and any `STOPPED` lines.

## Before you start
- **Repository:** a fresh clone of a test copy of a real service (e.g. broker-dealer). Never one holding production
  secrets you have not denied (SECURITY.md).
- **JIRA + Confluence:** a *test* JIRA project, and a Confluence space with a page to hold PRDs (the `Confluence
  parent page`) — the PRD is the only Confluence page. The Atlassian connector connected in Claude Code; its write tools on **ask**.
- **Two people** (or two Atlassian accounts): **A** runs the commands; **B** approves with `/pl-approve`.
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
| 2.1 | `/pl-onboard` (answer: JIRA project, Confluence space, parent page, base branch, `Separate approver: yes`) | each unit has `CLAUDE.md` ≤ 8 KB and `CLAUDE.reference.md` ≤ 30 KB; every Rule is tagged `[code: …]` or `[decided …]`; 10 spot-checked endpoints/tables are real; the settings hold all values. Commit it on a branch. |

## Part 3 — one feature end to end (≈ 4 h)
Use one small real backlog idea. After each step, open JIRA and Confluence and look at what was posted.

| # | Who | Run | Pass when |
|---|---|---|---|
| 3.1 | A | `/pl-pm "<idea>"` | a Confluence PRD page under the parent page; the epic's description is `epic.md` (summary, link, version); `## Record` says `Run by: A`, `Approval: pending`; **no label yet** |
| 3.2 | A | `/pl-ba <EPIC>` | stops: `STOPPED: plumbline-prd-approved not on <EPIC>` |
| 3.3 | A | `/pl-approve <EPIC> pm` | stops: you ran this step; another person must approve it |
| 3.4 | B | `/pl-approve <EPIC> pm` | an `[Plumbline approve /pl-pm]` comment by B, and the label |
| 3.5 | A | `/pl-ba <EPIC>` | stories with `AC1`, `AC2`, …, the `story.md` headings, points and `Blocks` links; no label |
| 3.6 | B | `/pl-approve <STORY> ba` | approved, label added |
| 3.7 | A | `/pl-arch <STORY>` | the full design is one `[Plumbline /pl-arch]` comment on the story (no Confluence page); it maps every AC id |
| 3.8 | — | edit one word of the PRD page in Confluence, then A: `/pl-ba <EPIC>` again | stops: the PRD page changed after approval |
| 3.9 | A | `/pl-dev <STORY>` | a branch; the comment maps every AC id to a test; tests ran (or the first line says UNVERIFIED) |
| 3.10 | A | `/pl-code-review <branch>` | the review cites code it read (callers, tests), not only CLAUDE.md; findings use blocker/major/minor as the judge's severity lines say |
| 3.11 | B | `/pl-approve <STORY> review` | approved, label added |
| 3.12 | A | `/pl-qa <STORY>` with the system running | evidence per AC id; stops cleanly if the system is not reachable |
| 3.13 | B | `/pl-approve <STORY> qa` | approved, label added |
| 3.14 | A | merge the branch in your clone, then `/pl-doc <STORY or PR>` | the docs PR adds only durable rules as `[decided <STORY>]`, the design's Decisions, the "Add to CLAUDE.md" notes; core still ≤ 8 KB; `Last updated:` is the merge commit |

## Part 4 — deliberate breakage (≈ 1 h)
| # | Do | Pass when |
|---|---|---|
| 4.1 | Change a line in code that CLAUDE.md describes (e.g. an endpoint's role), commit, then `/pl-code-review` a branch touching that file | the judge flags the defect from the code and adds `CLAUDE.md out of date`; every command warns "CLAUDE.md may be stale for: …" |
| 4.2 | Hand-edit a hand-off draft to drop a heading, then let the command continue | `check-template.sh` fails it before any judge runs |
| 4.3 | Set `Separate approver: no`, run `/pl-arch` on a new story | A's yes adds the label; `Approval: self — A` |
| 4.4 | On a team where the connector cannot read issue history: label a story by hand without `/pl-approve`, run the next command | `STOPPED: cannot verify who approved <KEY> — run /pl-approve` |

## Results (copy into your reply)
| # | Pass / Fail | What happened (one line; paste the STOPPED line or hand-over first line) |
|---|---|---|
| 1.1 | | |
| … | | |

Most useful to send back if something fails: the command, its full hand-over, and what JIRA/Confluence show.
