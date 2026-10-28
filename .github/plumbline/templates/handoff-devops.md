[Plumbline /pl-devops] {{YYYY-MM-DD}}

## CI failure
CI run: {{link or id}}
Category: {{code | test | coverage | pipeline | config | flaky}}

## Cause
{{what failed and why, with file:line}}

## Fix
{{the change on the branch, or the proposed fix for a person to make}}

## Results
Local: {{command and result}}
CI: {{result after the fix, or "not re-run"}}

## Record
Plumbline: {{version from .github/plumbline/VERSION}}
Commit: {{short commit the work is based on}}
Judge: {{PASS after n/3 | FAIL after 3/3 | n/a}}
Run by: {{name of the person who ran the command}}
Approval: {{pending — <label> to be added by <role> SME | self — <name> (<date>)}}
