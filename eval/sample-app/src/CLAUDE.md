# order-desk

<!-- plumbline:begin unit -->
Last updated: VERIFIED_COMMIT (2026-10-28, /pl-onboard)

## 1. Purpose
REST API for customer orders: create, read, list, pay, ship, cancel. Package `com.example.orderdesk`.

## 2. Build & run
- Test: `./mvnw test` (or `mvn test`). Run: `mvn spring-boot:run` (port 8085).
- Test recipe: `mvn test` · Java 21 · not run in this sample (it is review material).

## 3. Architecture & structure
Java 21, Spring Boot 3.3 (Web MVC, JDBC, Security, Validation), Maven, H2. Layers: controller → service →
repository (`JdbcTemplate`, no JPA); records for data; one exception handler for every error. Packages: `order/`
(controller, service, repository, records), `common/` (errors), `security/` (gateway header filter, roles).

## 4. API
- `GET /api/orders/{id}` — owner or ADMIN.
- `GET /api/orders?customerId=&limit=` — owner or ADMIN; `limit` 1..`orderdesk.list.max-limit` (100), default 20.
- `POST /api/orders` — owner or ADMIN; 201 with the order.
- `POST /api/orders/{id}/pay`, `POST /api/orders/{id}/ship` — ADMIN only (`@PreAuthorize("hasRole('ADMIN')")`).
- `POST /api/orders/{id}/cancel` — owner or ADMIN.
- Errors: always `ApiError {code, message}` from `GlobalExceptionHandler`: 404 `NOT_FOUND`, 409 `INVALID_STATE`,
  400 `VALIDATION_FAILED`, 403 `FORBIDDEN`.

## 5. Data
`customer(id, name, email unique)`, `orders(id, customer_id, status, total_amount DECIMAL(12,2), created_at)`,
`order_line(id, order_id, sku, quantity, unit_price DECIMAL(12,2))`, `order_status_history(order_id, from_status,
to_status, changed_by, changed_at)`. Schema lives in `src/main/resources/schema.sql`.

## 6. Integrations
None besides the gateway headers.

## 7. Configuration
`orderdesk.list.max-limit` (100). No secrets in this service.

## 8. Security
`GatewayHeaderFilter` turns `X-User-Id` / `X-User-Role` (ADMIN, CUSTOMER) into the principal; `CurrentUser` reads it.

## 9. Rules
- **Money** is `BigDecimal` end to end (`DECIMAL(12,2)` in the database); never `double`/`float`; compare with
  `compareTo`, never `equals`. (`OrderLine.lineTotal`, `OrderService.create`)
- **SQL** only through `JdbcTemplate` with `?` parameters; never build SQL from input. (`OrderRepository`)
- **Order status** changes only through `OrderService.changeStatus`, which checks `OrderStatus.canMoveTo` and writes
  `order_status_history`; nothing else calls `OrderRepository.updateStatus`.
- **Authorization:** back-office actions (pay, ship, refunds, anything changing money) are ADMIN only with
  `@PreAuthorize("hasRole('ADMIN')")`; customer-facing endpoints check owner-or-ADMIN.
- **Lists** are always bounded by `orderdesk.list.max-limit`.
- **Errors** use `ApiError {code, message}` through `GlobalExceptionHandler`; never swallow an exception and return 200.
- **Logs** carry IDs and statuses only — never e-mail addresses, names or other personal data.

## 10. Must never
- Use floating point for money; concatenate SQL; change status outside `OrderService.changeStatus`; return
  unbounded lists; log personal data; change the error body format; delete or weaken tests.

## 11. Tech debt
None found (sample).

## 12. Decisions & trade-offs
- `JdbcTemplate` instead of JPA: explicit SQL, no lazy-loading surprises (stated in this file by the team).
- Status rules live in `OrderStatus.canMoveTo` and are enforced only through `OrderService.changeStatus`, so
  `order_status_history` is always written (source: `OrderRepository.updateStatus` comment).

## 13. Open questions
None.
<!-- plumbline:end unit -->
