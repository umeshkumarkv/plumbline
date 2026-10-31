<!-- plumbline:template handoff-doc v2 -->
[Plumbline /pl-doc] {{YYYY-MM-DD}}

## Change
- PR: {{link to the open PR}}
- Reviewed code: {{the PR's head commit, or —}}

## Text to apply
{{for each file (CLAUDE.md, CLAUDE.reference.md, API spec): its path, the section, and the exact new text in a fenced block — dev applies it word for word in this PR; or None}}

## Rules added
{{each new [decided <KEY>] rule, or None}}

## Proposed removals
{{rules or entries to drop or move to the reference file, each with why — for the architect, or None}}

— Plumbline {{version}} · {{/pl-command}} · handoff-doc v2 · commit {{short sha, or —}} · judge {{pending | PASS n/3 | FAIL 3/3 | n/a}} · {{minutes}} min · SME edited: {{yes | no}} · AI-drafted, posted after SME review
