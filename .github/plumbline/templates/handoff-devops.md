<!-- plumbline:template handoff-devops v2 -->
[Plumbline /pl-devops] {{YYYY-MM-DD}}

## CI failure
- CI run: {{link or id}}
- Category: {{code | test | coverage | pipeline | config | flaky}}

## Cause
{{what failed and why, with file:line}}

## Fix
{{for each file: its path and the exact change in a fenced block, for dev to apply on the PR branch — or the diagnosis for a person to act on}}

## Results
- Local: {{command and result}}
- CI: {{result after the fix, or "not re-run"}}

— Plumbline {{version}} · {{/pl-command}} · handoff-devops v2 · commit {{short sha, or —}} · judge {{pending | PASS n/3 | FAIL 3/3 | n/a}} · {{minutes}} min · SME edited: {{yes | no}} · AI-drafted, posted after SME review
