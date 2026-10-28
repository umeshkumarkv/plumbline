# Plumbline templates

Every artefact Plumbline posts is written on one of these, so the same work looks the same in every project.
Rules for writers: keep every `## ` heading, in this order, with the exact text; replace every `{{…}}`; write `None`
under a heading with nothing to say; add sub-headings (`###`) or tables freely inside a section. Plain `-` bullets
only (JIRA shows `- [ ]` as literal text). Fields are bullets (`- Label: value`): plain line breaks are merged into one
paragraph by Confluence and JIRA. `check-template.sh` checks the shape before any judge or post; the judge
checks the content.

| Template | Becomes | Written by |
|---|---|---|
| `prd.md` | Confluence page (or the epic description without Confluence) — the only Confluence page | `/pl-pm` writer |
| `epic.md` | JIRA epic description: summary + link to the PRD page | `/pl-pm` |
| `story.md` | JIRA story description | `/pl-ba` writer |
| `handoff-arch.md` | `[Plumbline /pl-arch]` comment on the story: the full design | `/pl-arch` writer |
| `handoff-dev.md` … `handoff-devops.md` | `[Plumbline /pl-<role>]` comment on the story | each command, at the hand-over |
| `sprint-report.md` | sprint report comment or page | `/pl-sm` writer |
| `approval.md` | `[Plumbline approve /pl-<role>]` comment: the approver's decision | `/pl-approve` |

Every template ends with a one-line footer: `— Plumbline <version> · /pl-<command> · commit <sha> · judge <result> ·
AI-drafted, posted after SME review`. Who posted it and who approved it are not typed in: JIRA records the author.
A template's first line may be `<!-- plumbline:forbid <regex> -->`: what other roles own (APIs and points in a story,
code in a design). The check fails any draft line that matches; writers do not copy that line.

| Role | Owns | Never |
|---|---|---|
| PM | problem, behaviour, success criteria, scope, priority, size S/M/L | APIs, units, data, points, how to build |
| BA | user story, Given/When/Then criteria, examples, business dependencies | APIs, status codes, units, data, points, branches |
| Architect | unit, AC → technical check, design, technical blockers, suggested points | changing criteria or scope; production code |
| Team (at `/pl-approve … arch`) | story points | — |
| Repository settings | branch pattern, PR target | — |
