[Plumbline /pl-arch] {{YYYY-MM-DD}}

## Acceptance criteria → design
{{AC1 → the endpoint, rule, error or UI behaviour that meets it; one line per AC}}

## Endpoint
{{method, path, auth and roles, unit and port, routing; request fields; response fields; every error (status, code, condition)}}

## Data
{{migration file (next free version) and DDL, or "no schema change"; entity fields and types}}

## Logic
{{class and method signature; numbered steps; error paths}}

## Calls and events
{{calls to other units (endpoint, timeout/fallback); events produced/consumed — or None}}

## Cache and config
{{keys, TTL, invalidation, new config or env vars — or None}}

## Identity and access
{{ownership field, identifier kinds, per-role access for every endpoint, gateway headers}}

## Tests
{{at least 3 named cases per layer touched, including error paths}}

## API-spec delta
{{paths and schemas to add or change, or "no change"}}

## Decisions
{{each design choice and why — /pl-doc copies these into CLAUDE.md "Decisions & trade-offs" — or None}}

## Open questions
{{anything the story or code does not answer, or None}}

## Record
Plumbline: {{version from .github/plumbline/VERSION}}
Commit: {{short commit the work is based on}}
Judge: {{PASS after n/3 | FAIL after 3/3 | n/a}}
Run by: {{name of the person who ran the command}}
Approval: {{pending — <label> to be added by <role> SME | self — <name> (<date>)}}
