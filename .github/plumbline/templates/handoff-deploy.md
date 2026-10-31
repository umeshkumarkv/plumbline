<!-- plumbline:template handoff-deploy v1 -->
[Plumbline /pl-devops] {{YYYY-MM-DD}}

## Deployment
- Pipeline run: {{link or id}}
- Deployed commit: {{the merge commit the pipeline deployed}}
- QA environment: {{URL — answers: yes, HTTP <status> | no}}
- Result: {{deployed to QA | pipeline failed}}

## Failure
{{when the pipeline failed: the failing step, the cause from the log, and the fix as exact text per file for dev — or None}}

— Plumbline {{version}} · {{/pl-command}} · handoff-deploy v1 · commit {{short sha, or —}} · judge {{pending | PASS n/3 | FAIL 3/3 | n/a}} · {{minutes}} min · SME edited: {{yes | no}} · AI-drafted, posted after SME review
