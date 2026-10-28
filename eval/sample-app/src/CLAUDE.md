# order-desk

<!-- plumbline:begin unit -->
Last updated: VERIFIED_COMMIT (2026-10-28, /pl-onboard, claude-unit v1)

## Purpose
REST API for customer orders: create, read, list, pay, ship, cancel. Package `com.example.orderdesk`.

## Build & run
- Test: `./mvnw test` (or `mvn test`). Run: `mvn spring-boot:run` (port 8085).
- Test recipe: `mvn test` · Java 21 · not run in this sample (it is review material).

## Architecture & structure
Java 21, Spring Boot 3.3 (Web MVC, JDBC, Security, Validation), Maven, H2. Layers: controller → service →
repository (`JdbcTemplate`, no JPA); records for data; one exception handler for every error. Packages: `order/`
(controller, service, repository, records), `common/` (errors), `security/` (gateway header filter, roles).

## Security
`GatewayHeaderFilter` turns `X-User-Id` / `X-User-Role` (ADMIN, CUSTOMER) into the principal; `CurrentUser` reads it.
Back-office endpoints use `@PreAuthorize("hasRole('ADMIN')")`; customer-facing ones check owner-or-ADMIN.

## Rules
- [decided team] **Money** is `BigDecimal` end to end (`DECIMAL(12,2)` in the database); never `double`/`float`;
  compare with `compareTo`, never `equals`. (`OrderLine.lineTotal`, `OrderService.create`)
- [decided team] **SQL** only through `JdbcTemplate` with `?` parameters; never build SQL from input. (`OrderRepository`)
- [decided team] **Order status** changes only through `OrderService.changeStatus`, which checks
  `OrderStatus.canMoveTo` and writes `order_status_history`; nothing else calls `OrderRepository.updateStatus`.
- [decided team] **Authorization:** back-office actions (pay, ship, refunds, anything changing money) are ADMIN only
  with `@PreAuthorize("hasRole('ADMIN')")`; customer-facing endpoints check owner-or-ADMIN.
- [decided team] **Lists** are always bounded by `orderdesk.list.max-limit`.
- [decided team] **Errors** use `ApiError {code, message}` through `GlobalExceptionHandler`; never swallow an
  exception and return 200.
- [decided team] **Logs** carry IDs and statuses only — never e-mail addresses, names or other personal data.

## Must never
- Use floating point for money; concatenate SQL; change status outside `OrderService.changeStatus`; return
  unbounded lists; log personal data; change the error body format; delete or weaken tests.

## Decisions & trade-offs
- `JdbcTemplate` instead of JPA: explicit SQL, no lazy-loading surprises (stated in this file by the team).
- Status rules live in `OrderStatus.canMoveTo` and are enforced only through `OrderService.changeStatus`, so
  `order_status_history` is always written (source: `OrderRepository.updateStatus` comment).

## Reference
API — 7 endpoints, 1 controller · Data — 4 tables · Integrations — none · Configuration — 1 key · Tech debt — none.
Open CLAUDE.reference.md only for the section your task needs.
<!-- plumbline:end unit -->
