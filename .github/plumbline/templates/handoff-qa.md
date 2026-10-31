<!-- plumbline:template handoff-qa v2 -->
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

— Plumbline {{version}} · {{/pl-command}} · handoff-qa v2 · commit {{short sha, or —}} · judge {{pending | PASS n/3 | FAIL 3/3 | n/a}} · {{minutes}} min · SME edited: {{yes | no}} · AI-drafted, posted after SME review
