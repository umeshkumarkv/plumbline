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

Every template ends with `## Record`: version, commit, judge result, who ran it, and the approval (see SECURITY.md).
