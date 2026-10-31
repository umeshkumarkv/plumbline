# Onboarding audit — every unit, every check, one list (`/pl-onboard`, done by the judge with its own tools)

Work through **every unit** (each folder with a CLAUDE.md besides the root) and **every check** below — no sampling.
Use search over the code, not memory. Report every failure in one list, `FAIL <unit> [<check>]: <what>`, so nothing is
found later piece by piece. A check that does not apply to a unit is skipped silently.

1. **endpoints** — every request mapping in the unit's code (e.g. `@GetMapping`/`@PostMapping`/`@RequestMapping` with
   the class prefix; Express/Nest routes) appears in the unit's CLAUDE.md or CLAUDE.reference.md with its full path
   (`{id}` and `{orderId}` count as the same).
2. **tables** — every table created in the unit's migrations (`CREATE TABLE`, schema prefix ignored) appears in the docs.
3. **topics** — every message topic the code names as a literal (`@KafkaListener(topics=…)`, `send("…")`) appears.
4. **tags** — every `[code: <file>]` names a file that exists in the repository.
5. **header defaults** — every identity header read with a silent default (e.g. `@RequestHeader(value="X-User-Id",
   defaultValue="SYSTEM")`) is named in the root's *Decisions needed*.
6. **pass-through** — a filter or guard that lets a request through when the identity/role header is missing is named
   in the root's *Decisions needed*.
7. **cors** — CORS open to any origin (`allowedOrigins("*")`, bare `@CrossOrigin`) is documented.
8. **reach** — if a deploy file (docker-compose, k8s, Helm) publishes the unit's port, its *Reachable without that
   check* field says so for that environment.
9. **recipe** — the *Test recipe* line shows a run (passed, or failed with the error) — not "not run".
10. **root** — every `Security risk:` line in a unit file is named in the root's *Decisions needed*.
