[Plumbline /pl-qa] {{YYYY-MM-DD}}

## Run
- Environment: {{URL(s) used}}
- Tested commit: {{short sha}}
- Result: {{all passed | n of m failed | QA not run: <why>}}

## Results per criterion
{{AC1 · API/UI · PASS/FAIL · the request or steps, expected, actual — one block per AC}}

## Edge cases
{{unknown id, no credentials, invalid input … with results, or None}}

## Failures
{{each: request/steps · expected · actual · response body — or None}}

## Record
- Plumbline: {{version from .github/plumbline/VERSION}}
- Commit: {{short commit the work is based on}}
- Judge: {{PASS after n/3 | FAIL after 3/3 | n/a}}
- Run by: {{name of the person who ran the command}}
- Approval: {{pending — <label> to be added by <role> SME | self — <name> (<date>)}}
