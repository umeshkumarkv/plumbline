# Approval Matrix — Plumbline on a regulated codebase

Who must approve each action an AI agent can take. Default for a bank pilot: **nothing merges or changes JIRA state without a named human.**
Every approval **should** be recorded in an audit record (`audit-record.schema.json`) with the approver's identity. **Status: the schema is defined; the eval loops do not write audit records yet.** That wiring (and a check that the approver is a human account) is the next build step. Until then, the evidence is the JIRA/GitHub history.

## Agent actions

| Action | Default approver | May be automated later? (customer opt-in, after the model passes re-qualification) | Evidence the approver sees |
|---|---|---|---|
| JIRA comment (status, findings, reports) | none (informational) | — | the comment itself |
| Add/remove JIRA label (`plumbline-*`) | Ticket owner | Yes, for `plumbline-dor-ready` / `plumbline-arch-approved` when the isolated critic PASSes | critic JSON + scorecard |
| Transition JIRA status | Ticket owner | Yes, In Progress / In Review only | loop summary |
| Create Epic | Product Owner | No | PRD + critic JSON |
| Create Story | Product Owner or BA lead | No during pilot | story + critic JSON |
| `git push` to `ai/*` branch | Developer on the ticket | Yes, internal-only changes with gates green | gate output + critic JSON |
| `gh pr create` | Developer on the ticket | Yes, same as push | PR body + gate output |
| Post PR review verdict | — (posted as a **status check**, never as an approval) | — | critic JSON |
| Merge PR | CODEOWNERS of every touched service | **Never** for regulated paths | gates + critic + human review |
| Write or overwrite any `CLAUDE.md` | Service tech lead (root: Principal Architect) | No | diff + discovery evidence |
| Root `CLAUDE.md` §5, §6, §9, §10, §11 | Principal Architect | No | diff |
| Change `gates/`, `baseline.json`, lint/ArchUnit config, rubrics | Platform/governance owner, in a separate policy PR | No | diff + eval re-run |
| Create Confluence page (security report, release notes) | Release manager | No | page preview |
| Go/No-Go decision | Go/No-Go meeting (humans) | No | release pack |

## Separation of duties

- The agent that authors an artifact never evaluates it in its own context (isolated critic).
- The human who approves a merge is not the human who prompted the generating agent for that change, on regulated paths.
- Gate and rubric changes cannot ride along in a feature PR. Enforced by `gates/checks/protected_paths.py`, run by `gates/ci/guardrails.yml` from the **base** branch (`pull_request_target`), so a PR cannot edit away its own check. It fails **any** PR, whatever its branch name, that changes workflows, CODEOWNERS, agent prompts/critic definitions (`.claude/`, `.github/prompts/`), scanner ignore files (`.semgrepignore` at any depth), lint/ArchUnit/suppression config, the jacoco/surefire/failsafe configuration or test properties in any `pom.xml`, scanner pins, or any CLAUDE.md, unless the PR carries the `plumbline-policy-change` label. Every one of those paths is listed in `CODEOWNERS.template`; with "Require review from Code Owners" on, a named human owner signs every policy change. Known limit: GitHub cannot restrict who adds a label, so the label alone is not the control; the CODEOWNERS review is. The gate rules themselves live in a separate, pinned repo.

## Regulated paths

The full template is `CODEOWNERS.template`. Regulated code paths (excerpt):
```
/services/order-service/src/main/java/**/service/OrderStateMachineService.java  @oms-architects
/services/risk-service/**                                                         @risk-owners @oms-architects
/services/client-service/**/service/*Cash*                                        @client-owners @oms-architects
/services/*/src/main/resources/db/migration/**                                    @dba-team
```
Any agent PR touching a regulated path needs a named approver from that group, with no auto-merge, ever.
