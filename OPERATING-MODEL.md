# Plumbline operating model

Agreed 2026-10-31. Plumbline implements exactly this page; a change to how teams work changes this page first.

## Principles
1. **Markdown only.** Plumbline installs `.md` files and nothing else, so it behaves the same on macOS, Windows and
   Linux. Its agents run only the project's own build and test commands.
2. **Every person works in their own clone. Nothing travels through anyone's folder.** Hand-offs live only in JIRA,
   Confluence and the PR (or MR). Local drafts are private scratch, never read by anyone else.
3. **Only two roles use git.** Dev creates the branch and the PR; code review reads the PR and comments on it.
   No other role runs git.
4. **Any git host.** GitHub, GitLab or Bitbucket. "PR" means pull request or merge request.
5. **The person who runs a command is that role's SME.** Before anything is posted, the command shows the exact text
   and says: *"Your yes approves this as the <role> SME. JIRA will show you as the person who posted it."*
6. **The architect's design is final.** One story is built in one unit; the HLD (per epic) comes before the LLD (per
   story). Later roles follow both exactly — a role that cannot stops with `design gap — /pl-arch <KEY>`.

## Who does what

| Role | Works from | Hands off via | Git |
|---|---|---|---|
| PM | the idea; reads code read-only | Confluence PRD + JIRA epic | none |
| BA | the PRD; reads code read-only | JIRA stories (business language) | none |
| Architect | epic and stories; the code | Confluence HLD + JIRA comments (LLD; CLAUDE.md changes as an exact text block) | none |
| Dev | the LLD | branch + PR + JIRA comment; applies the architect's and doc's CLAUDE.md text word for word | **yes** |
| Doc | the open PR | PR comments with the exact CLAUDE.md / API-spec text per file + JIRA comment | none |
| Code review | the PR — code and docs together | PR review + JIRA comment | read-only |
| Merge | — | a human, behind branch protection; the architect is a required reviewer for CLAUDE.md files | human |
| Devops | the pipeline run for the merge commit | JIRA comment (QA URL + deployed commit) + `plumbline-deployed-qa`; a failed pipeline becomes a fix-PR comment for dev | none |
| QA | the deployed QA environment | JIRA evidence per acceptance criterion; **closes the story** on a pass, or moves it back to In Progress | none |
| SM | JIRA | JIRA comments, sprint report, team metrics | none |
| Onboard | the whole repository, once (then refreshes) | the tech lead commits the CLAUDE.md files in their own PR | none |

## Story flow
```
PM ─► BA ─► Architect ─► Dev ─► Doc ─► Code review ─► Merge ─► CI/CD deploys to QA ─► Devops ─► QA ─► Done
```
- If code review leads to changes in the API or the rules, doc runs again on the same PR before merge.
- If QA fails, the story goes back to In Progress; dev opens a fix PR and the flow repeats from Dev.
- The pipeline deploys; Plumbline never does. Devops confirms the deploy and reports it.

## Access each role needs
- **Everyone:** the repository (read-only is enough for all but dev) — a client's policy may say no, in which case PM
  and BA work from CLAUDE.md only; Claude Code; the Atlassian connector (JIRA + Confluence).
- **Doc, devops, SM:** a connector for the project's git host (GitHub, GitLab or Bitbucket). Without one, the person
  pastes the PR diff or pipeline log.
- **Dev:** git with push rights, and the host's way to open a PR.
- **Project setup (once):** branch protection on the base branch; the architect as required reviewer for
  `**/CLAUDE.md` (CODEOWNERS on GitHub/GitLab; code owners or default reviewers on Bitbucket); a CI/CD pipeline that
  deploys the base branch to the QA region.

## Metrics
Every hand-off comment's footer records: attempts used, minutes taken, the judge result, and whether the SME edited
the text before posting. `/pl-sm metrics` reads them from JIRA, so the whole team sees the same numbers.

## Not supported yet
- **GitHub Copilot:** on hold until tested. Its files stay in the repository but are not part of the install.
- Tested so far on one JIRA Cloud / Confluence site and one GitHub repository; other sites and hosts are expected to
  work but are untested.
