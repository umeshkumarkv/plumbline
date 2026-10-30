# Order Desk

<!-- plumbline:begin solution -->
Last updated: 0000000 (2026-10-28, /pl-onboard, claude-root v3)

## Solution
Order Desk is a small order service: customers place orders with lines; back-office staff (ADMIN) mark them paid and
shipped; customers or staff can cancel. One Spring Boot unit; H2 in memory for local runs.

## Units
| Unit | Folder | Kind | Port | Owns | CLAUDE.md |
|---|---|---|---|---|---|
| order-desk | `.` | Spring Boot 3 / Maven / Java 21 | 8085 | `/api/orders`, tables `customer`, `orders`, `order_line`, `order_status_history` | `src/CLAUDE.md` |

## How they connect
An API gateway (not in this repository) authenticates users and forwards `X-User-Id` and `X-User-Role`.

## Architecture
One Spring Boot service behind an API gateway; stateless; authorization in this service from gateway headers; one
error format (`ApiError`) for every endpoint.

## Decisions & trade-offs
None recorded beyond `src/CLAUDE.md` Decisions.

## Conventions
Money as `BigDecimal`, SQL only through `JdbcTemplate` with `?` parameters, one `ApiError` format for every error, logs with ids only — see `src/CLAUDE.md` Rules.

## Plumbline settings
- JIRA project: OD
- Confluence space: OD
- Confluence parent page: Order Desk features
- Base branch: main
- PR target: main
- Branch pattern: ai/OD-<n>-<slug>
- Workflow: To Do → In Progress → In Review → Done
- API URL: http://localhost:8085
- Frontend URL: none

## Decisions needed
- Secrets found: none
None.

## Rules for every change
- Security: authorization is checked in this service, never assumed from the gateway alone (see `src/CLAUDE.md`).
- Testing: every change comes with tests that would fail without it; never delete, skip or weaken a test.
<!-- plumbline:end solution -->
