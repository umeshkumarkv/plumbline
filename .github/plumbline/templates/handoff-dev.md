[Plumbline /pl-dev] {{YYYY-MM-DD}}

## Change
- Branch: {{branch}}
- PR: {{link, or "not opened"}}
- Tests: {{ran — N passed, M failed (pre-existing: …) | UNVERIFIED — not run: <why>}}

## Acceptance criteria → tests
{{AC1 → TestClass.testName; one line per AC}}

## Design tests → tests
{{design test → test name; one line each}}

## Deviations from the design
{{each with its reason, or None}}

## Notes for /pl-doc
{{"Add to CLAUDE.md: …" and "CLAUDE.md out of date: …" lines from the helpers, or None}}

## Record
- Plumbline: {{version from .github/plumbline/VERSION}}
- Commit: {{short commit the work is based on}}
- Judge: {{PASS after n/3 | FAIL after 3/3 | n/a}}
- Run by: {{name of the person who ran the command}}
- Approval: {{pending — <label> to be added by <role> SME | self — <name> (<date>)}}
